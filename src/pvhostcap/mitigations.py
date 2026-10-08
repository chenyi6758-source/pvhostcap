"""Mitigation strategies: classic HC enhancement measures.

Each strategy is a callable ``(net, sgen_indices) -> None`` applied after
the PV sgens are added and before the load flow, so it slots directly into
:func:`pvhostcap.sweep.evaluate`. The set mirrors the enhancement
techniques reviewed in Brohi et al. (2025): reactive-power control and
on-load tap changers.

Strategies:

- ``none`` — no mitigation (baseline).
- ``fixed_pf_absorb`` — inverters run at constant 0.95 power factor,
  absorbing reactive power (a common grid-code default).
- ``voltvar`` — Q(U) droop: inverters absorb Q once the local voltage
  exceeds a deadband, up to ``qmax_ratio`` of their active power. Solved
  by fixed-point iteration over the load flow.
- ``oltc`` — the MV/LV transformer tap is moved ``steps`` positions to
  lower the LV-side voltage, buying headroom for PV voltage rise.
"""

import pandapower as pp

from pvhostcap.sweep import system_hosting_capacity

__all__ = [
    "none",
    "apply_fixed_pf_absorb",
    "apply_voltvar",
    "apply_oltc_lower",
    "compare_strategies",
]


def none(net, sgen_indices):
    """Baseline: no mitigation."""


def apply_fixed_pf_absorb(net, sgen_indices, pf: float = 0.95):
    """Constant power-factor absorption (Q < 0) on all PV inverters."""
    import math
    q_per_p = math.tan(math.acos(pf))
    for i in sgen_indices:
        p_kw = net.sgen.at[i, "p_mw"] * 1000.0
        net.sgen.at[i, "q_mvar"] = -q_per_p * p_kw / 1000.0


def apply_voltvar(net, sgen_indices, v_deadband: float = 1.03,
                  v_saturation: float = 1.08, qmax_ratio: float = 0.44,
                  max_iter: int = 25, tol: float = 1e-4):
    """Q(U) droop via fixed-point iteration over the load flow.

    Each inverter absorbs ``qmax_ratio * P`` (default 0.44, i.e. an
    inverter oversized to S = 1.1 * P) once its terminal voltage passes
    ``v_deadband``, ramping linearly to full absorption at
    ``v_saturation``. Converges when no inverter's Q changes by more than
    ``tol`` (Mvar) between iterations.
    """
    from pvhostcap.powerflow import run_case

    buses = [int(net.sgen.at[i, "bus"]) for i in sgen_indices]
    q_prev = {i: 0.0 for i in sgen_indices}
    for _ in range(max_iter):
        if not run_case(net):
            return
        max_change = 0.0
        for i, bus in zip(sgen_indices, buses):
            v = float(net.res_bus.vm_pu.at[bus])
            p_mw = float(net.sgen.at[i, "p_mw"])
            qmax_mvar = qmax_ratio * p_mw
            if v <= v_deadband:
                q = 0.0
            elif v >= v_saturation:
                q = -qmax_mvar
            else:
                q = -qmax_mvar * (v - v_deadband) / (v_saturation - v_deadband)
            max_change = max(max_change, abs(q - q_prev[i]))
            net.sgen.at[i, "q_mvar"] = q
            q_prev[i] = q
        if max_change < tol:
            return


def apply_oltc_lower(net, sgen_indices, steps: int = 2):
    """Move the first transformer's tap ``steps`` positions to lower LV voltage.

    Only applies to transformers whose tap data allows it
    (``tap_min <= tap_pos + steps <= tap_max``); otherwise a no-op.
    """
    if len(net.trafo) == 0:
        return
    tid = net.trafo.index[0]
    pos = float(net.trafo.at[tid, "tap_pos"])
    tmin = float(net.trafo.at[tid, "tap_min"])
    tmax = float(net.trafo.at[tid, "tap_max"])
    # For the built-in HV/MV and MV/LV std types, raising tap_pos on the
    # tap side lowers the secondary voltage (verified empirically).
    target = pos + steps
    if tmin <= target <= tmax:
        net.trafo.at[tid, "tap_pos"] = target


STRATEGIES = {
    "none": none,
    "fixed_pf_absorb": apply_fixed_pf_absorb,
    "voltvar": apply_voltvar,
    "oltc": apply_oltc_lower,
}


def compare_strategies(net_template, load_buses, strategies=("none", "fixed_pf_absorb",
                                                              "voltvar", "oltc"),
                       tol_kw: float = 0.05, **limits) -> dict:
    """Run the system HC search under each named mitigation strategy."""
    out = {}
    for name in strategies:
        out[name] = system_hosting_capacity(
            net_template, load_buses, mitigation=STRATEGIES[name],
            tol_kw=tol_kw, **limits)
    return out
