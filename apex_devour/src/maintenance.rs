//! Self-improving coding-agent maintenance gate.
//! Native Rust gate inspired by public self-improving coding-agent loop patterns
//! (small validated tasks, persistent memory, reflection, and periodic maintenance),
//! without copying external code.
//!
//! Purpose for APEX Devour:
//! - Convert sessions into measurable improvement opportunities.
//! - Reward validated tasks, captured learnings, and implemented improvements.
//! - Penalize repeated failures, missing tests, and context-drift indicators.
//! - Decide whether the session batch should trigger a maintenance update.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenanceSession {
    pub session_id: String,
    pub task_count: u32,
    pub validated_tasks: u32,
    #[serde(default)]
    pub tests_run: bool,
    #[serde(default)]
    pub reflection_captured: bool,
    #[serde(default)]
    pub learning_events: u32,
    #[serde(default)]
    pub improvements_implemented: u32,
    #[serde(default)]
    pub repeated_failures: u32,
    #[serde(default)]
    pub context_drift: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionMaintenanceScore {
    pub session_id: String,
    pub validation_rate: f64,
    pub memory_signal: f64,
    pub improvement_signal: f64,
    pub risk_penalty: f64,
    pub maintenance_credit: f64,
    pub gate: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenanceReport {
    pub n_sessions: usize,
    pub mean_validation_rate: f64,
    pub mean_maintenance_credit: f64,
    pub reflection_capture_rate: f64,
    pub improvement_rate: f64,
    pub repeated_failure_rate: f64,
    pub trigger_maintenance: bool,
    pub keep_memory_update: bool,
    pub sessions: Vec<SessionMaintenanceScore>,
}

pub struct MaintenanceGate;

impl MaintenanceGate {
    /// Evaluate self-improvement maintenance readiness.
    /// Formula per session:
    /// validation_rate = validated_tasks / max(task_count, 1)
    /// memory_signal = 0.45*reflection + 0.35*min(learning_events/3,1) + 0.20*tests_run
    /// improvement_signal = min(improvements_implemented/2,1)
    /// risk_penalty = 0.20*min(repeated_failures/3,1) + 0.15*context_drift + 0.10*(no tests)
    /// maintenance_credit = clamp(0.50*validation_rate + 0.25*memory_signal + 0.25*improvement_signal - risk_penalty, 0, 1)
    pub fn evaluate(sessions: &[MaintenanceSession]) -> MaintenanceReport {
        if sessions.is_empty() {
            return MaintenanceReport {
                n_sessions: 0,
                mean_validation_rate: 0.0,
                mean_maintenance_credit: 0.0,
                reflection_capture_rate: 0.0,
                improvement_rate: 0.0,
                repeated_failure_rate: 0.0,
                trigger_maintenance: false,
                keep_memory_update: false,
                sessions: vec![],
            };
        }

        let mut scores = Vec::with_capacity(sessions.len());
        let mut validation_sum = 0.0;
        let mut reflection_count = 0usize;
        let mut improvement_count = 0usize;
        let mut repeated_failure_sessions = 0usize;

        for s in sessions {
            let denom = s.task_count.max(1) as f64;
            let validation_rate = (s.validated_tasks as f64 / denom).clamp(0.0, 1.0);
            validation_sum += validation_rate;
            if s.reflection_captured {
                reflection_count += 1;
            }
            if s.improvements_implemented > 0 {
                improvement_count += 1;
            }
            if s.repeated_failures > 0 {
                repeated_failure_sessions += 1;
            }

            let memory_signal = (0.45 * if s.reflection_captured { 1.0 } else { 0.0 }
                + 0.35 * (s.learning_events as f64 / 3.0).clamp(0.0, 1.0)
                + 0.20 * if s.tests_run { 1.0 } else { 0.0 })
            .clamp(0.0, 1.0);
            let improvement_signal = (s.improvements_implemented as f64 / 2.0).clamp(0.0, 1.0);
            let risk_penalty = (0.20 * (s.repeated_failures as f64 / 3.0).clamp(0.0, 1.0)
                + 0.15 * if s.context_drift { 1.0 } else { 0.0 }
                + 0.10 * if s.tests_run { 0.0 } else { 1.0 })
            .clamp(0.0, 1.0);
            let maintenance_credit =
                (0.50 * validation_rate + 0.25 * memory_signal + 0.25 * improvement_signal
                    - risk_penalty)
                    .clamp(0.0, 1.0);
            let gate = if maintenance_credit >= 0.70 {
                "promote".to_string()
            } else if maintenance_credit >= 0.45 {
                "review".to_string()
            } else {
                "hold".to_string()
            };

            scores.push(SessionMaintenanceScore {
                session_id: s.session_id.clone(),
                validation_rate,
                memory_signal,
                improvement_signal,
                risk_penalty,
                maintenance_credit,
                gate,
            });
        }

        let n = sessions.len() as f64;
        let total_credit: f64 = scores.iter().map(|s| s.maintenance_credit).sum();
        let mean_validation_rate = validation_sum / n;
        let mean_maintenance_credit = total_credit / n;
        let reflection_capture_rate = reflection_count as f64 / n;
        let improvement_rate = improvement_count as f64 / n;
        let repeated_failure_rate = repeated_failure_sessions as f64 / n;
        let trigger_maintenance = mean_maintenance_credit >= 0.55
            && reflection_capture_rate >= 0.60
            && repeated_failure_rate <= 0.40;
        let keep_memory_update = trigger_maintenance && mean_validation_rate >= 0.50;

        MaintenanceReport {
            n_sessions: sessions.len(),
            mean_validation_rate,
            mean_maintenance_credit,
            reflection_capture_rate,
            improvement_rate,
            repeated_failure_rate,
            trigger_maintenance,
            keep_memory_update,
            sessions: scores,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn promotes_validated_reflective_sessions() {
        let sessions = vec![MaintenanceSession {
            session_id: "s1".into(),
            task_count: 4,
            validated_tasks: 4,
            tests_run: true,
            reflection_captured: true,
            learning_events: 3,
            improvements_implemented: 2,
            repeated_failures: 0,
            context_drift: false,
        }];
        let r = MaintenanceGate::evaluate(&sessions);
        assert_eq!(r.n_sessions, 1);
        assert!(r.mean_maintenance_credit >= 0.95);
        assert!(r.trigger_maintenance);
        assert!(r.keep_memory_update);
        assert_eq!(r.sessions[0].gate, "promote");
    }

    #[test]
    fn holds_drifting_unvalidated_sessions() {
        let sessions = vec![MaintenanceSession {
            session_id: "s1".into(),
            task_count: 5,
            validated_tasks: 1,
            tests_run: false,
            reflection_captured: false,
            learning_events: 0,
            improvements_implemented: 0,
            repeated_failures: 3,
            context_drift: true,
        }];
        let r = MaintenanceGate::evaluate(&sessions);
        assert!(!r.trigger_maintenance);
        assert!(!r.keep_memory_update);
        assert_eq!(r.sessions[0].gate, "hold");
    }
}
