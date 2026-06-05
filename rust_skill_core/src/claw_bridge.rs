//! CLAW Memory Bridge: Connects Hermes Session Anchor ↔ SkillBank
//! M_claw = α·S_cache + β·D_local + γ·T_auto
//! Anchored at /tmp/hermes_session_anchor.json

use serde::{Deserialize, Serialize};
use std::fs;

/// Session anchor structure (from SOUL.md session continuity protocol)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionAnchor {
    pub session_id: String,
    pub last_updated: String,
    pub last_llm: String,
    pub active_task: ActiveTask,
    pub project_state: std::collections::HashMap<String, ProjectState>,
    pub recent_decisions: Vec<Decision>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveTask {
    pub what: String,
    pub phase: String,
    pub done_steps: Vec<String>,
    pub pending_steps: Vec<String>,
    pub key_files: Vec<String>,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectState {
    pub status: String,
    pub last_action: String,
    pub cron_jobs: std::collections::HashMap<String, String>,
    pub last_verified: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    pub when: String,
    pub what: String,
    pub why: String,
}

/// CLAW Memory integration result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClawResult {
    pub m_claw: f64,
    pub s_cache: f64,
    pub d_local: f64,
    pub t_auto: f64,
    pub matched_skills_count: usize,
    pub skill_ids: Vec<String>,
}

/// Load session anchor from path
pub fn load_anchor(path: &str) -> Option<SessionAnchor> {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
}

/// Compute M_claw from anchor
/// α = 0.45, β = 0.35, γ = 0.20
pub fn compute_m_claw(anchor: &SessionAnchor, skill_ids: &[String]) -> ClawResult {
    // S_cache: session cache freshness (1.0 if active_task is recent, else decay)
    let s_cache = if anchor.active_task.phase == "in_progress" {
        0.9
    } else if anchor.active_task.phase == "completed" {
        0.6
    } else {
        0.3
    };

    // D_local: local document context (key_files presence)
    let d_local = if anchor.active_task.key_files.is_empty() {
        0.3
    } else {
        0.7_f64.min(0.3 + 0.4 * (anchor.active_task.key_files.len() as f64 / 5.0).min(1.0))
    };

    // T_auto: task auto-progress score (how many done_steps vs pending_steps)
    let done = anchor.active_task.done_steps.len() as f64;
    let pending = anchor.active_task.pending_steps.len() as f64;
    let t_auto = if pending == 0.0 {
        0.95
    } else {
        (done / (done + pending)).max(0.1)
    };

    let alpha = 0.45;
    let beta = 0.35;
    let gamma = 0.20;

    let m_claw = alpha * s_cache + beta * d_local + gamma * t_auto;

    ClawResult {
        m_claw,
        s_cache,
        d_local,
        t_auto,
        matched_skills_count: skill_ids.len(),
        skill_ids: skill_ids.to_vec(),
    }
}

/// Merge CLAW context into skill selection
/// Returns enriched context for matcher
pub fn enrich_context(anchor: &SessionAnchor, skill_ids: &[String]) -> serde_json::Value {
    let claw = compute_m_claw(anchor, skill_ids);

    serde_json::json!({
        "session_id": anchor.session_id,
        "active_task_phase": anchor.active_task.phase,
        "active_task_what": anchor.active_task.what,
        "m_claw": claw.m_claw,
        "s_cache": claw.s_cache,
        "d_local": claw.d_local,
        "t_auto": claw.t_auto,
        "skill_ids": skill_ids,
        "done_steps": anchor.active_task.done_steps,
        "pending_steps": anchor.active_task.pending_steps,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_anchor() -> SessionAnchor {
        let mut project_state = std::collections::HashMap::new();
        project_state.insert(
            "apex-spiral".to_string(),
            ProjectState {
                status: "APEX×CLAW融合规范已激活".to_string(),
                last_action: "commit APEX_CLAW_FUSION_SPEC.md".to_string(),
                cron_jobs: std::collections::HashMap::new(),
                last_verified: "2026-05-27T13:00:00+08:00".to_string(),
            },
        );

        SessionAnchor {
            session_id: "test-session".to_string(),
            last_updated: "2026-05-27T13:00:00+08:00".to_string(),
            last_llm: "MiniMax-M2.7".to_string(),
            active_task: ActiveTask {
                what: "APEX×CLAW深度融合".to_string(),
                phase: "in_progress".to_string(),
                done_steps: vec!["读取skill_bank.rs".to_string(), "写入融合规范".to_string()],
                pending_steps: vec!["构建skill_core".to_string(), "验证health".to_string()],
                key_files: vec![
                    "/home/ubuntu/apex-spiral/APEX_CLAW_FUSION_SPEC.md".to_string(),
                    "/home/ubuntu/.hermes/skills/apex-search-skill/skill_core/src/main.rs".to_string(),
                ],
                blockers: vec![],
            },
            project_state,
            recent_decisions: vec![],
        }
    }

    #[test]
    fn test_compute_m_claw() {
        let anchor = make_anchor();
        let skills = vec!["skill_000".to_string(), "skill_001".to_string()];
        let claw = compute_m_claw(&anchor, &skills);

        // m_claw = 0.45*0.9 + 0.35*0.7 + 0.20*0.5 = 0.405+0.245+0.1 = 0.75
        assert!((claw.m_claw - 0.75).abs() < 0.001, "m_claw={}", claw.m_claw);
        assert!((claw.s_cache - 0.9).abs() < 0.001);
        assert!((claw.d_local - 0.7).abs() < 0.001);
    }

    #[test]
    fn test_enrich_context() {
        let anchor = make_anchor();
        let skills = vec!["skill_000".to_string()];
        let ctx = enrich_context(&anchor, &skills);

        assert_eq!(ctx["session_id"], "test-session");
        assert_eq!(ctx["active_task_phase"], "in_progress");
        assert!(ctx["m_claw"].as_f64().unwrap() > 0.0);
    }
}