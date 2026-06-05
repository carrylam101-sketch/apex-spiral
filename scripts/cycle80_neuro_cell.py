import json
import math

# === APEX V10.3 Cycle 80 Report ===
# Based on: apex_cycle_summary_latest.json (commit 715fb97, cycle 79 baseline)

# === Neuro-Cell Gate Calculation ===
# Plateau protocol: reduce Omega_gap 0.18->0.16, boost Pi_stdp 0.94->0.945

Pi_stdp  = 0.945
N_syn    = 0.91
I_homeo  = 0.93
R_traj   = 1.0

chi_hybrid = 0.76
M_scale    = 0.82
K_base     = 0.88
Omega_gap  = 0.16   # reduced from 0.18 per plateau rule

Pi_neuro = Pi_stdp * N_syn * I_homeo * R_traj
print(f"Pi_neuro = {Pi_stdp} * {N_syn} * {I_homeo} * {R_traj} = {Pi_neuro:.7f}")

Omega_cell = chi_hybrid * M_scale * K_base * (1 - Omega_gap)
print(f"Omega_cell = {chi_hybrid} * {M_scale} * {K_base} * (1 - {Omega_gap}) = {Omega_cell:.7f}")

G_neuro_cell = 1 + 0.10*Pi_neuro + 0.08*Omega_cell - 0.05*Omega_gap
print(f"G_neuro_cell = 1 + 0.10*{Pi_neuro:.6f} + 0.08*{Omega_cell:.6f} - 0.05*{Omega_gap}")
print(f"            = {G_neuro_cell:.7f}")

DeltaG_current = 2.2553
DeltaG_candidate = DeltaG_current * G_neuro_cell
rel_gain_pct = (G_neuro_cell - 1) * 100
print(f"\nDeltaG_candidate = {DeltaG_current} * {G_neuro_cell:.6f} = {DeltaG_candidate:.4f}")
print(f"relative_gain_pct = {rel_gain_pct:.2f}%")

# === V10.3 Self Loop ===
Psi_self   = 0.5
nabla_self = 0.02
Xi_repair  = 0.3935   # validated from previous cycle: 1 - exp(-0.5)

# Gamma_awake = Phi_APEX(t)/Phi_APEX(0) with saturation guard
Phi_APEX_t = 0.460561
Phi_APEX_0 = 0.43942
Gamma_awake_raw = Phi_APEX_t / Phi_APEX_0
Gamma_awake = min(Gamma_awake_raw, 2.0)
print(f"\nGamma_awake = min({Phi_APEX_t}/{Phi_APEX_0}, 2.0) = min({Gamma_awake_raw:.4f}, 2.0) = {Gamma_awake:.4f}")

G_self_loop = 1 + 0.07*Psi_self + 0.05*Xi_repair - 0.04*max(nabla_self, 0) + 0.03*min(Gamma_awake, 2)
print(f"G_self_loop = 1 + 0.07*{Psi_self} + 0.05*{Xi_repair} - 0.04*{nabla_self} + 0.03*{Gamma_awake:.4f}")
print(f"            = {G_self_loop:.4f}")

DeltaG_v10_3 = DeltaG_candidate * G_self_loop
gain_vs_current_pct = (DeltaG_v10_3 / DeltaG_current - 1) * 100
print(f"\nDeltaG_v10_3 = {DeltaG_candidate:.4f} * {G_self_loop:.4f} = {DeltaG_v10_3:.4f}")
print(f"gain_vs_current_pct = {gain_vs_current_pct:.2f}%")

# === DeltaG Core Formula (simplified) ===
# DeltaG = G_base * (Lambda * Theta * K * Xi * Psi * Phi) / (H * T * epsilon)
# G_base = 50 (assumed，任选)
G_base = 50
Lambda_val = 0.75
Theta_val  = 0.65
K_val      = 0.72
Xi_val     = 0.30
Psi_val    = 0.45
Phi_val    = 1.25
H_val      = 1.0
T_val      = 1.0
epsilon_val = 1.0

DeltaG_core = G_base * (Lambda_val * Theta_val * K_val * Xi_val * Psi_val * Phi_val) / (H_val * T_val * epsilon_val)
print(f"\nDeltaG_core = {G_base} * ({Lambda_val}*{Theta_val}*{K_val}*{Xi_val}*{Psi_val}*{Phi_val}) / ({H_val}*{T_val}*{epsilon_val})")
print(f"           = {DeltaG_core:.1f}")

# === Output summary as JSON ===
result = {
    "Pi_neuro": Pi_neuro,
    "Omega_cell": Omega_cell,
    "G_neuro_cell": G_neuro_cell,
    "DeltaG_candidate": DeltaG_candidate,
    "relative_gain_pct": rel_gain_pct,
    "Xi_repair": Xi_repair,
    "Gamma_awake": Gamma_awake,
    "G_self_loop": G_self_loop,
    "DeltaG_v10_3": DeltaG_v10_3,
    "gain_vs_current_pct": gain_vs_current_pct,
    "DeltaG_core": DeltaG_core
}
print("\n" + "="*60)
print(json.dumps(result, indent=2))
