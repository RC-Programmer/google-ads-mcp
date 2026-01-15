import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 8080;
const MCP_URL = process.env.MCP_URL;
const API_TOKEN = process.env.API_TOKEN;

if (!MCP_URL) throw new Error("Missing MCP_URL");
if (!API_TOKEN) throw new Error("Missing API_TOKEN");

function requireAuth(req, res, next) {
  const auth = req.headers.authorization || "";
  if (auth !== `Bearer ${API_TOKEN}`) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

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
    const { customer_id, resource, fields, limit, where, order_by } = req.body || {};

    if (!customer_id || !resource || !Array.isArray(fields) || fields.length === 0) {
      return res.status(400).json({
        error: "Required: customer_id (string), resource (string), fields (string[])"
      });
    }

    const args = { customer_id, resource, fields };
    if (typeof limit === "number") args.limit = limit;
    if (typeof where === "string") args.where = where;
    if (typeof order_by === "string") args.order_by = order_by;

    const result = await callMcpTool("search", args);
    res.json({ result });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () => console.log(`Actions wrapper listening on ${PORT}`));
