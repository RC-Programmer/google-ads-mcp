import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 8080;
const MCP_URL = process.env.MCP_URL; // should point to your supergateway MCP endpoint (e.g. https://.../mcp)
const API_TOKEN = process.env.API_TOKEN;

if (!MCP_URL) throw new Error("Missing MCP_URL");
if (!API_TOKEN) throw new Error("Missing API_TOKEN");

function normalizeToken(v) {
  if (!v) return "";
  // trims, removes surrounding < > that people accidentally paste
  return String(v).trim().replace(/^<|>$/g, "");
}

function requireAuth(req, res, next) {
  const authRaw = (req.headers.authorization || "").trim();
  const xApiKeyRaw = (req.headers["x-api-key"] || "").trim();
  const apiKeyRaw = (req.headers["api-key"] || "").trim();

  const auth = normalizeToken(authRaw);
  const xApiKey = normalizeToken(xApiKeyRaw);
  const apiKey = normalizeToken(apiKeyRaw);

  const expected = normalizeToken(API_TOKEN);

  const ok =
    auth === `Bearer ${expected}` ||
    auth === expected ||
    xApiKey === expected ||
    apiKey === expected;

  if (!ok) return res.status(403).json({ error: "Forbidden" });
  next();
}

let rpcId = 1;

function parseMcpResponseText(text) {
  // supergateway often replies as text/event-stream, so we extract the LAST data: line
  const dataLines = text
    .split("\n")
    .map((l) => l.trimEnd())
    .filter((l) => l.startsWith("data: "));

  if (dataLines.length > 0) {
    const last = dataLines[dataLines.length - 1].slice("data: ".length);
    return JSON.parse(last);
  }

  // sometimes it may be plain JSON
  return JSON.parse(text);
}

async function callMcpTool(toolName, args) {
  const body = {
    jsonrpc: "2.0",
    id: rpcId++,
    method: "tools/call",
    params: { name: toolName, arguments: args || {} }
  };

  const resp = await fetch(MCP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream"
    },
    body: JSON.stringify(body)
  });

  const text = await resp.text();

  let payload;
  try {
    payload = parseMcpResponseText(text);
  } catch (e) {
    throw new Error(`Unexpected MCP response (not JSON): ${text.slice(0, 500)}`);
  }

  if (payload?.error) throw new Error(payload.error.message || "MCP error");

  // Prefer structuredContent.result when available, otherwise fall back gracefully
  const r = payload?.result;

  // many MCP servers return: { result: { structuredContent: { result: [...] } } }
  if (r?.structuredContent?.result !== undefined) return r.structuredContent.result;

  // some return: { result: [...] } directly
  if (Array.isArray(r)) return r;

  // some return: { result: { result: [...] } }
  if (r?.result !== undefined) return r.result;

  return r ?? null;
}

app.get("/healthz", (_req, res) => res.send("ok"));

app.post("/api/list-accessible-customers", requireAuth, async (_req, res) => {
  try {
    const result = await callMcpTool("list_accessible_customers", {});
    res.json({ customers: result });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.post("/api/search", requireAuth, async (req, res) => {
  try {
    const {
      customer_id,
      resource,
      fields,
      limit,
      order_by,

      // support BOTH styles:
      // - where: "segments.date DURING LAST_30_DAYS"
      // - conditions: ["segments.date DURING LAST_30_DAYS", "campaign.id = 123"]
      where,
      conditions
    } = req.body || {};

    if (!customer_id || !resource || !Array.isArray(fields) || fields.length === 0) {
      return res.status(400).json({
        error: "Required: customer_id (string), resource (string), fields (string[])"
      });
    }

    const args = { customer_id, resource, fields };

    // MCP server expects `conditions` as a list (your pydantic error proved that)
    if (Array.isArray(conditions) && conditions.length > 0) {
      args.conditions = conditions;
    } else if (typeof where === "string" && where.trim()) {
      args.conditions = [where.trim()];
    }

    if (typeof limit === "number") args.limit = limit;
    if (typeof order_by === "string" && order_by.trim()) args.order_by = order_by.trim();

    const result = await callMcpTool("search", args);
    res.json({ result });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () => console.log(`Actions wrapper listening on ${PORT}`));
