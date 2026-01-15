import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 8080;
const MCP_URL = process.env.MCP_URL;
const API_TOKEN = process.env.API_TOKEN;

if (!MCP_URL) throw new Error("Missing MCP_URL");
if (!API_TOKEN) throw new Error("Missing API_TOKEN");

function requireAuth(req, res, next) {
  const auth = String(req.headers.authorization || "").trim();
  const xApiKey = String(req.headers["x-api-key"] || "").trim();
  const apiKey = String(req.headers["api-key"] || "").trim();

  const ok =
    auth === `Bearer ${API_TOKEN}` ||
    auth === API_TOKEN ||
    xApiKey === API_TOKEN ||
    apiKey === API_TOKEN;

  if (!ok) return res.status(403).json({ error: "Forbidden" });
  next();
}

function parseMcpSsePayload(sseText) {
  const lines = String(sseText || "").split("\n");
  const dataLines = lines.filter((l) => l.startsWith("data: "));
  if (!dataLines.length) return null;
  const last = dataLines[dataLines.length - 1].slice("data: ".length).trim();
  if (!last) return null;
  return JSON.parse(last);
}

function extractToolErrorFromResult(resultObj) {
  if (!resultObj || resultObj.isError !== true) return null;
  const firstText =
    Array.isArray(resultObj.content) &&
    resultObj.content.find((c) => c && c.type === "text" && typeof c.text === "string");
  return firstText?.text || "Tool returned isError:true";
}

function safeJson(value) {
  const seen = new WeakSet();

  const normalize = (v) => {
    if (v == null) return v;

    // primitives
    const t = typeof v;
    if (t === "string" || t === "number" || t === "boolean") return v;

    // BigInt
    if (t === "bigint") return v.toString();

    // Buffer
    if (typeof Buffer !== "undefined" && Buffer.isBuffer(v)) return v.toString("base64");

    // Dates
    if (v instanceof Date) return v.toISOString();

    // Arrays
    if (Array.isArray(v)) return v.map(normalize);

    // Google protobuf / containers often look like array-like objects
    if (typeof v === "object") {
      // prevent cycles
      if (seen.has(v)) return "[Circular]";
      seen.add(v);

      // Try common protobuf conversions
      if (typeof v.toJSON === "function") {
        try {
          return normalize(v.toJSON());
        } catch {
          // fall through
        }
      }
      if (typeof v.toObject === "function") {
        try {
          return normalize(v.toObject());
        } catch {
          // fall through
        }
      }

      // If it's iterable (like RepeatedScalarContainer), turn into array
      try {
        if (typeof v[Symbol.iterator] === "function") {
          return Array.from(v, normalize);
        }
      } catch {
        // ignore
      }

      // Plain object
      const out = {};
      for (const [k, val] of Object.entries(v)) {
        out[k] = normalize(val);
      }
      return out;
    }

    // fallback
    return String(v);
  };

  return normalize(value);
}

async function callMcpTool(toolName, args) {
  const body = {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "tools/call",
    params: { name: toolName, arguments: args || {} }
  };

  const resp = await fetch(MCP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream"
    },
    body: JSON.stringify(body)
  });

  const text = await resp.text();

  let payload;
  try {
    payload = parseMcpSsePayload(text);
  } catch {
    throw new Error(`Unexpected MCP response (invalid JSON): ${text.slice(0, 500)}`);
  }

  if (!payload) throw new Error(`Unexpected MCP response (no SSE data): ${text.slice(0, 500)}`);

  if (payload?.error) throw new Error(payload?.error?.message || "MCP error");

  const toolStyleErr = extractToolErrorFromResult(payload?.result);
  if (toolStyleErr) throw new Error(toolStyleErr);

  const toolResult = payload?.result?.structuredContent?.result;
  const raw = toolResult ?? payload?.result ?? null;

  // IMPORTANT: sanitize anything weird before we hand it back to Express/JSON
  return safeJson(raw);
}

function normalizeConditions(body) {
  if (Array.isArray(body?.conditions))
    return body.conditions.filter((x) => typeof x === "string" && x.trim());
  if (typeof body?.where === "string" && body.where.trim()) return [body.where.trim()];
  return [];
}

app.get("/healthz", (_req, res) => res.send("ok"));

app.post("/api/list-accessible-customers", requireAuth, async (_req, res) => {
  try {
    const customers = await callMcpTool("list_accessible_customers", {});
    res.json({ customers });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.post("/api/search", requireAuth, async (req, res) => {
  try {
    const body = req.body || {};
    const { customer_id, resource, fields } = body;

    if (!customer_id || !resource || !Array.isArray(fields) || fields.length === 0) {
      return res.status(400).json({
        error: "Required: customer_id (string), resource (string), fields (string[])"
      });
    }

    const conditions = normalizeConditions(body);
    const order_by = typeof body.order_by === "string" ? body.order_by.trim() : "";
    const limit = typeof body.limit === "number" ? body.limit : undefined;

    const args = { customer_id, resource, fields };
    if (conditions.length) args.conditions = conditions;
    if (order_by) args.order_by = order_by;
    if (typeof limit === "number") args.limit = limit;

    const result = await callMcpTool("search", args);
    res.json({ result });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () => console.log(`Actions wrapper listening on ${PORT}`));
