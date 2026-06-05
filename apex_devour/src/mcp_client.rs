//! MCP Client — Model Context Protocol JSON-RPC 2.0 client for APEX-MEM.
//!
//! Thin HTTP client to call an external APEX-MEM MCP server (JSON-RPC 2.0 over HTTP POST).
//! APEX-MEM is a separate Rust binary running at a known address.
//!
//! Integration: Hermes → mcp_client → APEX-MEM HTTP server
//! Tools: apex_ingest, apex_retrieve, apex_forget, apex_get,
//!        apex_dream, apex_apex, apex_flush, apex_graph_link,
//!        apex_graph_bfs, apex_stats

use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

const DEFAULT_MCP_ADDR: &str = "http://127.0.0.1:8080";

#[derive(Debug, Clone)]
pub struct McpClient {
    addr: String,
    http: Client,
    tool_names: Vec<String>,
}

impl Default for McpClient {
    fn default() -> Self {
        Self::new(
            std::env::var("APEX_MEM_MCP_ADDR")
                .unwrap_or_else(|_| DEFAULT_MCP_ADDR.to_string()),
        )
    }
}

impl McpClient {
    pub fn new(addr: String) -> Self {
        Self {
            addr,
            http: Client::new(),
            tool_names: vec![
                "apex_ingest".to_string(),
                "apex_retrieve".to_string(),
                "apex_forget".to_string(),
                "apex_get".to_string(),
                "apex_dream".to_string(),
                "apex_apex".to_string(),
                "apex_flush".to_string(),
                "apex_graph_link".to_string(),
                "apex_graph_bfs".to_string(),
                "apex_stats".to_string(),
            ],
        }
    }

    pub async fn health_check(&self) -> anyhow::Result<McpHealthResponse> {
        let url = format!("{}/health", self.addr);
        let resp = self.http.get(&url).send().await?;
        let body: Value = resp.json().await?;
        Ok(serde_json::from_value(body)?)
    }

    pub async fn initialize(&self) -> anyhow::Result<McpInitializeResult> {
        let response = self.rpc("initialize", json!({})).await?;
        Ok(serde_json::from_value(response)?)
    }

    pub async fn list_tools(&self) -> anyhow::Result<Vec<McpToolDef>> {
        let response = self.rpc("tools/list", json!({})).await?;
        let tools = response
            .get("tools")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();
        let mut result = Vec::new();
        for v in tools {
            result.push(serde_json::from_value(v)?);
        }
        Ok(result)
    }

    pub async fn call_tool(
        &self,
        name: &str,
        arguments: Value,
    ) -> anyhow::Result<McpToolResult> {
        let params = json!({
            "name": name,
            "arguments": arguments,
        });
        let response = self.rpc("tools/call", params).await?;
        Ok(serde_json::from_value(response)?)
    }

    // ── Convenience helpers ───────────────────────────────────────────────

    /// Ingest a memory record; returns the assigned memory id.
    pub async fn ingest(
        &self,
        content: &str,
        dimension: &str,
        title: Option<&str>,
        tags: Option<Vec<&str>>,
        importance: Option<f64>,
    ) -> anyhow::Result<String> {
        let mut args = json!({ "content": content, "dimension": dimension });
        if let Some(t) = title {
            args["title"] = json!(t);
        }
        if let Some(tgs) = tags {
            args["tags"] = json!(tgs);
        }
        if let Some(imp) = importance {
            args["importance"] = json!(imp);
        }
        let result = self.call_tool("apex_ingest", args).await?;
        // response.content[0].text is JSON string like {"id": "abc123"}
        let first_text = result
            .content
            .first()
            .and_then(|c| c.text.parse::<Value>().ok())
            .ok_or_else(|| anyhow::anyhow!("no content in apex_ingest response"))?;
        first_text
            .get("id")
            .and_then(|v| v.as_str())
            .map(String::from)
            .ok_or_else(|| anyhow::anyhow!("no id in apex_ingest response"))
    }

    /// Hybrid retrieval: BM25 + vector + graph fused via RRF.
    pub async fn retrieve(
        &self,
        query: &str,
        top_k: Option<usize>,
        dimension: Option<&str>,
        expand: Option<bool>,
        rerank: Option<bool>,
    ) -> anyhow::Result<McpRetrieveResult> {
        let mut args = json!({ "query": query });
        if let Some(k) = top_k {
            args["top_k"] = json!(k);
        }
        if let Some(d) = dimension {
            args["dimension"] = json!(d);
        }
        if let Some(e) = expand {
            args["expand"] = json!(e);
        }
        if let Some(r) = rerank {
            args["rerank"] = json!(r);
        }
        let result = self.call_tool("apex_retrieve", args).await?;
        Ok(serde_json::from_value(serde_json::to_value(&result).unwrap_or_default())?)
    }

    /// Trigger APEX self-diagnosis on the memory subsystem.
    /// Parses the JSON result from content.text.
    pub async fn apex_diagnose(&self) -> anyhow::Result<Value> {
        let result = self.call_tool("apex_apex", json!({})).await?;
        let first_text = result
            .content
            .first()
            .and_then(|c| c.text.parse::<Value>().ok())
            .ok_or_else(|| anyhow::anyhow!("no content in apex_apex response"))?;
        Ok(first_text)
    }

    /// Trigger a dreaming/consolidation sweep.
    pub async fn dream(&self) -> anyhow::Result<Value> {
        let result = self.call_tool("apex_dream", json!({})).await?;
        let first_text = result
            .content
            .first()
            .and_then(|c| c.text.parse::<Value>().ok())
            .ok_or_else(|| anyhow::anyhow!("no content in apex_dream response"))?;
        Ok(first_text)
    }

    /// Add an edge to the knowledge graph.
    pub async fn graph_link(
        &self,
        src: &str,
        dst: &str,
        kind: &str,
        weight: Option<f64>,
        evidence: Option<&str>,
    ) -> anyhow::Result<bool> {
        let mut args = json!({ "src": src, "dst": dst, "kind": kind });
        if let Some(w) = weight {
            args["weight"] = json!(w);
        }
        if let Some(e) = evidence {
            args["evidence"] = json!(e);
        }
        let result = self.call_tool("apex_graph_link", args).await?;
        // Try result.ok first
        if let Some(ok) = result.ok {
            return Ok(ok);
        }
        // Fallback: parse content text
        let first_text = result
            .content
            .first()
            .and_then(|c| c.text.parse::<Value>().ok())
            .ok_or_else(|| anyhow::anyhow!("no content in apex_graph_link response"))?;
        Ok(first_text
            .get("ok")
            .and_then(|v| v.as_bool())
            .unwrap_or(false))
    }

    /// BFS traversal from a seed node in the knowledge graph.
    pub async fn graph_bfs(&self, seed: &str, hops: Option<usize>) -> anyhow::Result<Vec<String>> {
        let mut args = json!({ "seed": seed });
        if let Some(h) = hops {
            args["hops"] = json!(h);
        }
        let result = self.call_tool("apex_graph_bfs", args).await?;
        // result.nodes if present, else parse from content.text
        if let Some(nodes) = result.nodes {
            return Ok(nodes);
        }
        let first_text = result
            .content
            .first()
            .and_then(|c| c.text.parse::<Value>().ok())
            .ok_or_else(|| anyhow::anyhow!("no content in apex_graph_bfs response"))?;
        let arr = first_text
            .get("nodes")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();
        Ok(arr
            .iter()
            .filter_map(|v| v.as_str().map(String::from))
            .collect())
    }

    // ── Low-level JSON-RPC ────────────────────────────────────────────────

    async fn rpc(&self, method: &str, params: Value) -> anyhow::Result<Value> {
        let request = json!({
            "jsonrpc": "2.0",
            "id": Value::Null,
            "method": method,
            "params": params,
        });
        let resp = self
            .http
            .post(&self.addr)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await?;
        let body: Value = resp.json().await?;
        if let Some(err) = body.get("error") {
            let code = err.get("code").and_then(|v| v.as_i64()).unwrap_or(0);
            let msg = err.get("message").and_then(|v| v.as_str()).unwrap_or("unknown");
            anyhow::bail!("MCP RPC error {}: {}", code, msg);
        }
        body.get("result")
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("no result in MCP response"))
    }
}

// ── Data types ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpHealthResponse {
    pub status: String,
    pub service: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct McpInitializeResult {
    pub protocol_version: String,
    pub server_info: McpServerInfo,
    pub capabilities: McpCapabilities,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpServerInfo {
    pub name: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpCapabilities {
    #[serde(default)]
    pub tools: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpToolDef {
    pub name: String,
    pub description: String,
    #[serde(rename = "inputSchema")]
    pub input_schema: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpToolResult {
    pub content: Vec<McpContentItem>,
    #[serde(default)]
    pub is_error: bool,
    /// Present when tools/call returns `{"ok": true/false}` directly (e.g. apex_graph_link)
    #[serde(default)]
    pub ok: Option<bool>,
    /// Present when tools/call returns `{"nodes": [...]}` directly (e.g. apex_graph_bfs)
    #[serde(default)]
    pub nodes: Option<Vec<String>>,
}

impl McpToolResult {
    /// Parse first content item text as a JSON Value.
    fn first_json(&self) -> Option<Value> {
        self.content.first().and_then(|c| c.text.parse::<Value>().ok())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpContentItem {
    #[serde(rename = "type")]
    pub content_type: String,
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpRetrieveResult {
    pub hits: Vec<McpHit>,
    pub expanded_query: Option<String>,
    pub stats: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpHit {
    pub id: String,
    pub score: f64,
    pub title: Option<String>,
    pub content: String,
    pub dimension: String,
    pub tags: Vec<String>,
    pub sources: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mcp_client_construction() {
        let client = McpClient::new("http://127.0.0.1:8080".to_string());
        assert_eq!(client.addr, "http://127.0.0.1:8080");
        assert_eq!(client.tool_names.len(), 10);
    }

    #[test]
    fn test_mcp_tool_result_first_json() {
        let result = McpToolResult {
            content: vec![McpContentItem {
                content_type: "text".to_string(),
                text: r#"{"id": "abc123"}"#.to_string(),
            }],
            is_error: false,
            ok: None,
            nodes: None,
        };
        let v = result.first_json().unwrap();
        assert_eq!(v.get("id").and_then(|v| v.as_str()), Some("abc123"));
    }
}