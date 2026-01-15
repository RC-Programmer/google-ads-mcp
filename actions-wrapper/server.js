import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 8080;
const MCP_URL = process.env.MCP_URL; // e.g. https://google-ads-mcp-server.up.railway.app/mcp
const API_TOKEN = process.env.API_TOKEN; // secret token stored in Railway

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

  // Your server returns tool results under result.structuredContent.result
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

    // IMPORTANT:
    // The Google Ads MCP server expects the WHERE clause under `conditions` (not `where`).
    // We accept either input key for convenience, but we always pass `conditions` to MCP.
    const args = { customer_id, resource, fields };

    const cond = typeof conditions === "string" ? conditions : (typeof where === "string" ? where : undefined);
    if (typeof cond === "string") args.conditions = cond;

    if (typeof limit === "number") args.limit = limit;
    if (typeof order_by === "string") args.order_by = order_by;

    const result = await callMcpTool("search", args);
    res.json({ result });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () => console.log(`Actions wrapper listening on ${PORT}`));
