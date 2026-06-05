//! LLM Router: OpenAI-protocol compatible multi-provider with automatic fallback
//! Priority: freemodel.dev → Local Codex → MiniMax-M2.7
//! No Python glue — pure Rust implementation

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LLMProvider {
    Freemodel { api_key: String, model: String },
    Codex { endpoint: String, api_key: String, model: String },
    Minimax,
}

#[derive(Debug, Clone)]
pub struct LLMRouter {
    pub chain: Vec<LLMProvider>,
    pub timeout_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMRequest {
    pub model: String,
    pub messages: Vec<Message>,
    pub max_tokens: Option<u32>,
    pub temperature: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMResponse {
    pub provider: String,
    pub model: String,
    pub content: String,
    pub usage_tokens: u32,
    pub latency_ms: f64,
    pub status: String,
}

impl Default for LLMRouter {
    fn default() -> Self {
        Self {
            chain: vec![
                LLMProvider::Freemodel {
                    api_key: String::new(), // Set via env or config
                    model: "FRE-5.5".to_string(),
                },
                LLMProvider::Codex {
                    endpoint: "http://127.0.0.1:8317/v1".to_string(),
                    api_key: "codex-api".to_string(),
                    model: "codex".to_string(),
                },
                LLMProvider::Minimax,
            ],
            timeout_ms: 30_000,
        }
    }
}

impl LLMRouter {
    /// Route request through provider chain, return first successful response
    pub fn route(&self, req: &LLMRequest) -> Result<LLMResponse, String> {
        let mut last_err = String::new();

        for provider in &self.chain {
            match self.call_provider(provider, req) {
                Ok(resp) => return Ok(resp),
                Err(e) => {
                    last_err = format!("{:?} → {}", provider.name(), e);
                    eprintln!("[LLM Router] {} failed: {}", provider.name(), e);
                }
            }
        }

        Err(format!("All providers failed. Last: {}", last_err))
    }

    fn call_provider(&self, provider: &LLMProvider, req: &LLMRequest) -> Result<LLMResponse, String> {
        match provider {
            LLMProvider::Freemodel { api_key, model } => self.call_freemodel(api_key, model, req),
            LLMProvider::Codex { endpoint, api_key, model } => {
                self.call_openai_compatible(endpoint, api_key, model, req)
            }
            LLMProvider::Minimax => {
                // Minimax is the embedded provider — use internal knowledge
                // For actual API calls this would need the provider's endpoint
                Err("Minimax provider requires explicit endpoint configuration".to_string())
            }
        }
    }

    fn call_freemodel(&self, api_key: &str, model: &str, req: &LLMRequest) -> Result<LLMResponse, String> {
        if api_key.is_empty() {
            return Err("freemodel API key not set".to_string());
        }

        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_millis(self.timeout_ms))
            .build()
            .map_err(|e| e.to_string())?;

        let payload = serde_json::json!({
            "model": model,
            "messages": req.messages,
            "max_tokens": req.max_tokens.unwrap_or(512),
            "temperature": req.temperature.unwrap_or(0.7),
        });

        let resp = client
            .post("https://api.freemodel.dev/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .map_err(|e| e.to_string())?;

        let status = resp.status().as_u16();
        if status != 200 {
            let body = resp.text().unwrap_or_default();
            return Err(format!("HTTP {}: {}", status, body));
        }

        let parsed: serde_json::Value = resp.json().map_err(|e| e.to_string())?;
        let content = parsed["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or("")
            .to_string();
        let usage = parsed["usage"]["total_tokens"].as_u64().unwrap_or(0) as u32;

        Ok(LLMResponse {
            provider: "freemodel".to_string(),
            model: model.to_string(),
            content,
            usage_tokens: usage,
            latency_ms: 0.0, // Could be tracked with std::time::Instant
            status: "ok".to_string(),
        })
    }

    fn call_openai_compatible(
        &self,
        endpoint: &str,
        api_key: &str,
        model: &str,
        req: &LLMRequest,
    ) -> Result<LLMResponse, String> {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_millis(self.timeout_ms))
            .build()
            .map_err(|e| e.to_string())?;

        let payload = serde_json::json!({
            "model": model,
            "messages": req.messages,
            "max_tokens": req.max_tokens.unwrap_or(512),
            "temperature": req.temperature.unwrap_or(0.7),
        });

        let resp = client
            .post(format!("{}/chat/completions", endpoint.trim_end_matches('/')))
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .map_err(|e| e.to_string())?;

        let status = resp.status().as_u16();
        if status != 200 {
            let body = resp.text().unwrap_or_default();
            return Err(format!("HTTP {}: {}", status, body));
        }

        let parsed: serde_json::Value = resp.json().map_err(|e| e.to_string())?;
        let content = parsed["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or("")
            .to_string();
        let usage = parsed["usage"]["total_tokens"].as_u64().unwrap_or(0) as u32;

        Ok(LLMResponse {
            provider: "codex".to_string(),
            model: model.to_string(),
            content,
            usage_tokens: usage,
            latency_ms: 0.0,
            status: "ok".to_string(),
        })
    }

    /// Set freemodel API key from environment or config file
    pub fn with_freemodel_key(mut self, key: String) -> Self {
        if let LLMProvider::Freemodel { ref mut api_key, .. } = self.chain[0] {
            *api_key = key;
        }
        self
    }
}

impl LLMProvider {
    fn name(&self) -> &'static str {
        match self {
            LLMProvider::Freemodel { .. } => "freemodel",
            LLMProvider::Codex { .. } => "codex",
            LLMProvider::Minimax => "minimax",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_router_default_chain() {
        let router = LLMRouter::default();
        assert_eq!(router.chain.len(), 3);
    }

    #[test]
    fn test_router_with_key() {
        let router = LLMRouter::default().with_freemodel_key("test-key".to_string());
        if let LLMProvider::Freemodel { api_key, .. } = &router.chain[0] {
            assert_eq!(api_key, "test-key");
        }
    }

    #[test]
    fn test_provider_name() {
        assert_eq!(LLMProvider::Minimax.name(), "minimax");
    }

    #[test]
    fn test_request_serialization() {
        let req = LLMRequest {
            model: "FRE-5.5".to_string(),
            messages: vec![Message {
                role: "user".to_string(),
                content: "Hello".to_string(),
            }],
            max_tokens: Some(10),
            temperature: None,
        };
        let json = serde_json::to_string(&req).unwrap();
        assert!(json.contains("FRE-5.5"));
    }
}