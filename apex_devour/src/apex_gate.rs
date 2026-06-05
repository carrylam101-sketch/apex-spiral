//! APEX Gate — combines devour gain into ΔG candidate
//! ΔG_candidate = ΔG_current × G_neuro × G_self × G_devour
//! Gate: G_neuro ≥ 1.0, G_self ≥ 1.0, G_devour ≥ 0.95 to proceed

use serde::{Deserialize, Serialize};

pub struct ApexGate {
    pub g_neuro: f64,
    pub g_self: f64,
    /// G_apex_ib: iteration budget gate factor (Gene 611)
    /// G_apex_ib = 1 + 0.03*(1-truncation_risk) - 0.02*truncation_risk
    /// Normal (0-70%)  → 0.0  → G_ib = 1.0300
    /// Low (70-85%)   → 0.1  → G_ib = 1.0240
    /// Medium (85-95%) → 0.3 → G_ib = 1.0150
    /// High (95-99%)  → 0.6  → G_ib = 1.0040
    /// Critical (100%)→ 1.0  → G_ib = 0.9900
    pub g_apex_ib: f64,
}

impl Default for ApexGate {
    fn default() -> Self {
        Self::new()
    }
}

impl ApexGate {
    pub fn new() -> Self {
        // Conservative baseline — these would come from last registry cycle
        Self {
            g_neuro: 1.1142,
            g_self: 1.0908,
            g_apex_ib: 1.0300, // iteration_budget: normal (45/100 iter), Gene 611
        }
    }

    pub fn with_gains(g_neuro: f64, g_self: f64) -> Self {
        Self {
            g_neuro,
            g_self,
            g_apex_ib: 1.0,
        }
    }

    /// Compute ΔG candidate: ΔG_current × G_neuro × G_self × G_devour × G_apex_ib
    pub fn compute_delta_g_candidate(&self, delta_g_current: f64, g_devour: f64) -> f64 {
        delta_g_current * self.g_neuro * self.g_self * g_devour * self.g_apex_ib
    }

    /// Returns true if the gate is open: all three G factors ≥ their thresholds.
    pub fn gate_open(&self, g_devour: f64) -> bool {
        self.g_neuro >= 1.0 && self.g_self >= 1.0 && g_devour >= 0.95 && self.g_apex_ib >= 0.99
    }

    /// Full ΔG gate check with EVM health
    pub fn gate_status(&self, g_devour: f64, evm_defect_rate: f64) -> GateStatus {
        let neuro_ok = self.g_neuro >= 1.0;
        let self_ok = self.g_self >= 1.0;
        let devour_ok = g_devour >= 0.95;
        let evm_ok = evm_defect_rate < 0.083;
        let ib_ok = self.g_apex_ib >= 0.99;

        GateStatus {
            neuro_ok,
            self_ok,
            devour_ok,
            evm_ok,
            ib_ok,
            gate_open: neuro_ok && self_ok && devour_ok && evm_ok && ib_ok,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateStatus {
    pub neuro_ok: bool,
    pub self_ok: bool,
    pub devour_ok: bool,
    pub evm_ok: bool,
    /// Iteration Budget gate: G_apex_ib ≥ 0.99 (Gene 611)
    pub ib_ok: bool,
    pub gate_open: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gate_open() {
        let gate = ApexGate::new();
        assert!(gate.gate_open(1.0));
        assert!(gate.gate_open(0.95));
        assert!(!gate.gate_open(0.90));
    }

    #[test]
    fn test_delta_g_candidate() {
        let gate = ApexGate::new();
        // From cycle_96: G_base=0.7513, G_neuro=1.1142, G_self=1.0908, G_evm=1.0589
        let delta_g_current = 0.7513;
        let g_devour = 1.01; // small positive from devour
        let candidate = gate.compute_delta_g_candidate(delta_g_current, g_devour);
        // 0.7513 * 1.1142 * 1.0908 * 1.01 ≈ 0.924
        assert!(
            candidate > 0.90 && candidate < 1.00,
            "candidate={}",
            candidate
        );
    }

    #[test]
    fn test_gate_status() {
        let gate = ApexGate::new();
        let status = gate.gate_status(1.0, 0.01);
        assert!(status.gate_open);
        assert!(status.evm_ok);
    }
}
