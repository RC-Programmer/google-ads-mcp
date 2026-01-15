import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 8080;
const MCP_URL = process.env.MCP_URL;
const API_TOKEN = process.env.API_TOKEN;

if (!MCP_URL) throw new Error("Missing MCP_URL");
if (!API_TOKEN) throw new Error("Missing API_TOKEN");

function requireAuth(req, res, next) {
  const auth = (req.headers.authorization || "").trim();
  const xApiKey = (req.headers["x-api-key"] || "").trim();
  const token = (req.headers["api-key"] || "").trim();

  const ok =
    auth === `Bearer ${API_TOKEN}` ||
    auth === API_TOKEN ||
    xApiKey === API_TOKEN ||
    token === API_TOKEN;

  if (!ok) {
    return res.status(403).json({ error: "Forbidden" });
  }
  next();
}

// Streamable HTTP MCP responses come back as text/event-stream with lines like: data: {...}
async function callMcpTool(toolName, args) {
  const body = {
    jsonrpc: "2.0",
    id: 1,
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

  // Find the first "data: {json...}" line
  const dataLine = text.split("\n").find((line) => line.startsWith("data: "));
  if (!dataLine) throw new Error(`Unexpected MCP response: ${text.slice(0, 500)}`);

  const payload = JSON.parse(dataLine.replace("data: ", ""));
  if (payload?.error) throw new Error(payload.error.message || "MCP error");

  const toolResult = payload?.result?.structuredContent?.result;
  return toolResult ?? payload?.result ?? null;
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
    const { customer_id, resource, fields, limit, where, conditions, order_by } = req.body || {};

    if (!customer_id || !resource || !Array.isArray(fields) || fields.length === 0) {
      return res.status(400).json({
        error: "Required: customer_id (string), resource (string), fields (string[])"
      });
    }

    const args = { customer_id, resource, fields };

    // MCP expects `conditions` as a LIST of strings.
    // Accept any of:
    // - conditions: ["a", "b"]
    // - conditions: "a"
    // - where: "a" (legacy alias)
    let condList = null;

    if (Array.isArray(conditions)) {
      condList = conditions
        .filter((x) => typeof x === "string")
        .map((x) => x.trim())
        .filter(Boolean);
    } else if (typeof conditions === "string" && conditions.trim()) {
      condList = [conditions.trim()];
    } else if (typeof where === "string" && where.trim()) {
      condList = [where.trim()];
    }

    if (condList && condList.length) args.conditions = condList;

    if (typeof limit === "number") args.limit = limit;

    // MCP tool uses `orderings` (plural) and expects a list
    if (Array.isArray(order_by)) {
      const orderings = order_by
        .filter((x) => typeof x === "string")
        .map((x) => x.trim())
        .filter(Boolean);
      if (orderings.length) args.orderings = orderings;
    } else if (typeof order_by === "string" && order_by.trim()) {
      args.orderings = [order_by.trim()];
    }

    const result = await callMcpTool("search", args);
    res.json({ result });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () => console.log(`Actions wrapper listening on ${PORT}`));
