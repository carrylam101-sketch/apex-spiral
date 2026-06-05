#!/usr/bin/env python3
"""Neuro-Cell Gate + V10.3 Self Loop calculation for cycle 79"""
import math

# Current state from runner output (round 5, latest)
delta_g_current = 2.2553
phi_apex = 0.460561

# Neuro-Cell Gate calculation
Π_stdp, N_syn, I_homeo, R_traj = 0.94, 0.91, 0.93, 1.0
Π_neuro = Π_stdp * N_syn * I_homeo * R_traj
print(f'Π_neuro = {Π_stdp} * {N_syn} * {I_homeo} * {R_traj} = {Π_neuro}')

χ_hybrid, M_scale, K_base, Ω_gap = 0.76, 0.82, 0.88, 0.18
Ω_cell = χ_hybrid * M_scale * K_base * (1 - Ω_gap)
print(f'Ω_cell = {χ_hybrid} * {M_scale} * {K_base} * (1 - {Ω_gap}) = {Ω_cell}')

G_neuro_cell = 1 + 0.10*Π_neuro + 0.08*Ω_cell - 0.05*Ω_gap
print(f'G_neuro_cell = 1 + 0.10*{Π_neuro} + 0.08*{Ω_cell} - 0.05*{Ω_gap} = {G_neuro_cell}')

ΔG_candidate = delta_g_current * G_neuro_cell
print(f'ΔG_candidate = {delta_g_current} * {G_neuro_cell} = {ΔG_candidate}')
print(f'Relative gain vs delta_g_current: {(ΔG_candidate/delta_g_current - 1)*100:.2f}%')

# V10.3 Self Loop terms
psi_self = 0.5
nabla_self = 0.02
xi_repair = 1 - math.exp(-0.5)  # = 0.3935
gamma_awake = min(phi_apex / 0.43942, 2.0)  # saturation at 2.0
G_self_loop = 1 + 0.07*psi_self + 0.05*xi_repair - 0.04*max(nabla_self, 0) + 0.03*min(gamma_awake, 2)
ΔG_v10_3 = ΔG_candidate * G_self_loop
print(f'xi_repair = {xi_repair:.4f}')
print(f'gamma_awake = {gamma_awake:.4f}')
print(f'G_self_loop = {G_self_loop:.4f}')
print(f'ΔG_v10_3 = {ΔG_candidate} * {G_self_loop:.4f} = {ΔG_v10_3:.4f}')
