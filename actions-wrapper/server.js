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
  // MCP tools can return errors as:
  // result: { isError: true, content: [{type:"text", text:"..."}] }
  if (!resultObj || resultObj.isError !== true) return null;

  const firstText =
    Array.isArray(resultObj.content) &&
    resultObj.content.find((c) => c && c.type === "text" && typeof c.text === "string");

  return firstText?.text || "Tool returned isError:true";
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

  if (!payload) {
    throw new Error(`Unexpected MCP response (no SSE data): ${text.slice(0, 500)}`);
  }

  // JSON-RPC style error
  if (payload?.error) {
    throw new Error(payload?.error?.message || "MCP error");
  }

  // Tool-style error (isError:true inside result)
  const toolStyleErr = extractToolErrorFromResult(payload?.result);
  if (toolStyleErr) {
    throw new Error(toolStyleErr);
  }

  // Normal successful result
  const toolResult = payload?.result?.structuredContent?.result;
  return toolResult ?? payload?.result ?? null;
}

function normalizeConditions(body) {
  // Your MCP server expects `conditions` as a list of strings.
  if (Array.isArray(body?.conditions))
    return body.conditions.filter((x) => typeof x === "string" && x.trim());

  // Backwards compatibility if client sends `where`
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

    // Attempt #1
    try {
      const result = await callMcpTool("search", args);
      return res.json({ result });
    } catch (err) {
      const msg = String(err?.message || err);

      // Auto-fallback for the common ad_group_ad serialization crash ("type")
      const looksLikeTypeError =
        msg === "type" ||
        msg.endsWith(": type") ||
        msg.includes("Error executing tool search: type") ||
        msg.toLowerCase().includes(" tool search: type");

      if (resource === "ad_group_ad" && looksLikeTypeError) {
        // Retry #2 with safer fields
        const removed = [];
        const filteredFields = (fields || []).filter((f) => {
          const s = String(f);

          // These have been triggering "type" crashes in your logs
          if (s === "ad_group_ad.ad.type") {
            removed.push(s);
            return false;
          }
          if (s.includes("responsive_search_ad.headlines")) {
            removed.push(s);
            return false;
          }
          if (s.includes("responsive_search_ad.descriptions")) {
            removed.push(s);
            return false;
          }
          return true;
        });

        if (filteredFields.length) {
          const retryArgs = { ...args, fields: filteredFields };
          const result = await callMcpTool("search", retryArgs);

          return res.json({
            result,
            warnings: [
              "Your MCP server errors on some ad fields right now, so the wrapper retried without them.",
              `Removed: ${removed.join(", ") || "(none)"}`,
              "If you want RSA headlines/descriptions via API, we can add a dedicated endpoint that fetches ad text via ad_group_ad_asset_view / asset where supported."
            ]
          });
        }
      }

      return res.status(500).json({ error: msg });
    }
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.listen(PORT, () => console.log(`Actions wrapper listening on ${PORT}`));
