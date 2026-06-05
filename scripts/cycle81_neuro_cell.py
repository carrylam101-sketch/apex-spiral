#!/usr/bin/env python3
"""
APEX Cycle 81 Neuro-Cell Gate Computation
==========================================
Formula substitution evidence for APEX V10.3 self-evolution.

Neuro-Cell Gate (Neural Network x Whole-Cell Simulation):
  Pi_neuro = Pi_stdp x N_syn x I_homeo x R_traj
  Omega_cell = chi_hybrid x M_scale x K_base x (1 - Omega_gap)
  G_neuro_cell = 1 + 0.10*Pi_neuro + 0.08*Omega_cell - 0.05*Omega_gap
  DeltaG_candidate = DeltaG_current x G_neuro_cell

V10.3 Self Loop:
  Psi_self   = sigmoid(Phi_APEX - E[Phi_APEX])
  nabla_self = gradient(Defect) [small positive, indicating ongoing refinement]
  Xi_repair  = 1 - exp(-integral nabla_self dt)
  Gamma_awake = Phi_APEX(t)/Phi_APEX(0) with saturation guard (<=2.0)
  G_self_loop = 1 + 0.07*Psi_self + 0.05*Xi_repair - 0.04*max(nabla_self,0) + 0.03*min(Gamma_awake,2)
  DeltaG_v10_3 = DeltaG_candidate x G_self_loop

tau_trace = (1/N) x sum[(D + R + Re) / 3]
Neurotransmitter conservation: DA(30%) + END(25%) + ADR(10%) + CORT(35%) = 1.0
"""

from math import exp

# Five-Ring (21345 order, round 5 final from apex_cron_cycle_runner.py)
five_ring = {
    "Phi_anti": 1.094,
    "Psi_cross": 0.535,
    "H_X": 2.2282,
    "C_shannon": None,
    "T_full": 0.831,
    "M_mem": 0.896,
}

HERRO = {
    "H_ap":  0.965,
    "P_pile": 0.955,
    "S_info": 0.948,
    "C_corr": 0.975,
    "H_err":  0.851812,
}

Prime_Assembly = {
    "N_nick":  0.935,
    "F_flap":  0.925,
    "M_match": 0.9575,
    "A_self":  0.93,
    "P_asm":   0.77015,
}

DRT3 = {
    "T_prot": 0.9225,
    "R_rev":  0.918,
    "S_syn":  0.91,
    "D_dup":  0.911,
    "D_pro":  0.702051,
}

# Phi_APEX = H_err x P_asm x D_pro
Phi_APEX = HERRO["H_err"] * Prime_Assembly["P_asm"] * DRT3["D_pro"]
print(f"Phi_APEX = H_err({HERRO['H_err']}) x P_asm({Prime_Assembly['P_asm']}) x D_pro({DRT3['D_pro']})")
print(f"         = {Phi_APEX:.6f}")

# Neuro-Cell Gate
Pi_stdp  = 0.94
N_syn    = 0.91
I_homeo  = 0.93
R_traj   = 1.0

chi_hybrid = 0.76
M_scale   = 0.82
K_base    = 0.88
Omega_gap = 0.18

Pi_neuro    = Pi_stdp * N_syn * I_homeo * R_traj
Omega_cell  = chi_hybrid * M_scale * K_base * (1 - Omega_gap)
G_neuro_cell = 1 + 0.10*Pi_neuro + 0.08*Omega_cell - 0.05*Omega_gap
DeltaG_current   = 2.2553
DeltaG_candidate = DeltaG_current * G_neuro_cell

print(f"\n--- Neuro-Cell Gate ---")
print(f"Pi_neuro  = Pi_stdp({Pi_stdp}) x N_syn({N_syn}) x I_homeo({I_homeo}) x R_traj({R_traj}) = {Pi_neuro:.6f}")
print(f"Omega_cell = chi_hybrid({chi_hybrid}) x M_scale({M_scale}) x K_base({K_base}) x (1-Omega_gap({Omega_gap})) = {Omega_cell:.6f}")
print(f"G_neuro_cell = 1 + 0.10x{Pi_neuro:.4f} + 0.08x{Omega_cell:.4f} - 0.05x{Omega_gap} = {G_neuro_cell:.6f}")
print(f"DeltaG_candidate = {DeltaG_current} x {G_neuro_cell:.6f} = {DeltaG_candidate:.4f}")
print(f"relative_gain = {(G_neuro_cell-1)*100:.2f}%")

# V10.3 Self Loop
E_Phi      = 0.43942   # baseline from cycle 80
Psi_self   = 1 / (1 + exp(-(Phi_APEX - E_Phi)))
nabla_self = 0.02      # fixed small positive gradient
Xi_repair  = 1 - exp(-nabla_self * 5)   # 5 iterations since last reset
Gamma_awake = min(Phi_APEX / E_Phi, 2.0)

G_self_loop = (1 + 0.07*Psi_self + 0.05*Xi_repair
               - 0.04*max(nabla_self, 0) + 0.03*min(Gamma_awake, 2))
DeltaG_v10_3 = DeltaG_candidate * G_self_loop

print(f"\n--- V10.3 Self Loop ---")
print(f"Psi_self   = sigmoid(Phi_APEX - E[Phi_APEX]) = sigmoid({Phi_APEX:.4f} - {E_Phi}) = {Psi_self:.6f}")
print(f"nabla_self = {nabla_self} (small positive defect gradient)")
print(f"Xi_repair  = 1 - exp(-nabla_self x 5) = {Xi_repair:.6f}")
print(f"Gamma_awake = min(Phi_APEX/E_Phi, 2.0) = min({Phi_APEX/E_Phi:.6f}, 2.0) = {Gamma_awake:.6f}")
print(f"G_self_loop = 1 + 0.07x{Psi_self:.4f} + 0.05x{Xi_repair:.4f} - 0.04x{nabla_self} + 0.03x{Gamma_awake:.4f} = {G_self_loop:.6f}")
print(f"DeltaG_v10_3 = DeltaG_candidate x G_self_loop = {DeltaG_candidate:.4f} x {G_self_loop:.6f} = {DeltaG_v10_3:.4f}")
print(f"gain_vs_current_pct = {(DeltaG_v10_3/DeltaG_current-1)*100:.2f}%")

# tau_trace (Process Trace)
D  = (HERRO["H_ap"] + Prime_Assembly["M_match"] + DRT3["T_prot"]) / 3
R  = (HERRO["P_pile"] + Prime_Assembly["A_self"] + DRT3["R_rev"]) / 3
Re = (HERRO["S_info"] + Prime_Assembly["F_flap"] + DRT3["S_syn"]) / 3
tau_trace = (D + R + Re) / 3
print(f"\n--- tau_trace ---")
print(f"D  = ({HERRO['H_ap']} + {Prime_Assembly['M_match']} + {DRT3['T_prot']}) / 3 = {D:.6f}")
print(f"R  = ({HERRO['P_pile']} + {Prime_Assembly['A_self']} + {DRT3['R_rev']}) / 3 = {R:.6f}")
print(f"Re = ({HERRO['S_info']} + {Prime_Assembly['F_flap']} + {DRT3['S_syn']}) / 3 = {Re:.6f}")
print(f"tau_trace = ({D:.4f} + {R:.4f} + {Re:.4f}) / 3 = {tau_trace:.6f}")

# Neurotransmitter Conservation
DA   = 0.30
END  = 0.25
ADR  = 0.10
CORT = 0.35
print(f"\n--- Neurotransmitter Conservation ---")
print(f"DA({DA}) + END({END}) + ADR({ADR}) + CORT({CORT}) = {DA+END+ADR+CORT}")

# DeltaG Core Formula
G_base  = 50
Lambda  = 0.75
Theta   = 0.65
K       = 0.72
Xi      = 0.30
Psi     = 0.45
Phi     = 1.25
H, T, epsilon = 1.0, 1.0, 1.0
DeltaG_core = G_base * (Lambda * Theta * K * Xi * Psi * Phi) / (H * T * epsilon)
print(f"\n--- DeltaG Core Formula ---")
print(f"DeltaG_core = {G_base} x ({Lambda}x{Theta}x{K}x{Xi}x{Psi}x{Phi}) / ({H}x{T}x{epsilon}) = {DeltaG_core}")

# Summary dict
result = {
    "cycle": 81,
    "commit": "715fb97",
    "Phi_APEX": round(Phi_APEX, 6),
    "five_ring": five_ring,
    "HERRO": HERRO,
    "Prime_Assembly": Prime_Assembly,
    "DRT3": DRT3,
    "neuro_cell_gate": {
        "Pi_neuro_terms": {"Pi_stdp": Pi_stdp, "N_syn": N_syn, "I_homeo": I_homeo, "R_traj": R_traj},
        "Omega_cell_terms": {"chi_hybrid": chi_hybrid, "M_scale": M_scale, "K_base": K_base, "Omega_gap": Omega_gap},
        "Pi_neuro": round(Pi_neuro, 6),
        "Omega_cell": round(Omega_cell, 6),
        "G_neuro_cell": round(G_neuro_cell, 6),
        "DeltaG_candidate": round(DeltaG_candidate, 4),
        "relative_gain_pct": round((G_neuro_cell-1)*100, 2),
    },
    "v10_3_self_loop": {
        "Psi_self": round(Psi_self, 6),
        "nabla_self": nabla_self,
        "Xi_repair": round(Xi_repair, 6),
        "Gamma_awake": round(Gamma_awake, 6),
        "G_self_loop": round(G_self_loop, 6),
        "DeltaG_v10_3": round(DeltaG_v10_3, 4),
        "gain_vs_current_pct": round((DeltaG_v10_3/DeltaG_current-1)*100, 2),
    },
    "tau_trace": round(tau_trace, 6),
    "neurotransmitter_conservation": round(DA+END+ADR+CORT, 2),
    "DeltaG_core": DeltaG_core,
    "DeltaG_current": DeltaG_current,
    "DeltaG_candidate": round(DeltaG_candidate, 4),
    "DeltaG_v10_3": round(DeltaG_v10_3, 4),
}

import json
out = "/home/ubuntu/apex-spiral/reports/apex_cycle_summary_cycle81.json"
with open(out, "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(f"\nReport written to {out}")
