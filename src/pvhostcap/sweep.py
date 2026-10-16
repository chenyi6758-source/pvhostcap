"""Hosting-capacity sweeps: system-wide and per-bus (locational).

Method: deterministic bisection on PV size. Feasibility (no violation) is
monotone decreasing in PV size — more PV can only raise voltages and push
more reverse power through the same branches — so bisection on a single
scalar per case is exact up to the tolerance.
"""

import copy
from dataclasses import dataclass, field

import pandapower as pp

from pvhostcap.powerflow import (
    Violation,
    binding_violation,
    check_violations,
    run_case,
)

__all__ = [
    "HostingCapacityResult",
    "evaluate",
    "connection_check",
    "resolve_bus",
    "system_hosting_capacity",
    "locational_hosting_capacity",
]


@dataclass
class HostingCapacityResult:
    """Result of one hosting-capacity search."""

    hc_kw_per_bus: float          # bisection result (per-bus kW)
    hc_kw_total: float            # hc_kw_per_bus * n_pv_buses
    n_pv_buses: int
    binding: object = None        # Violation that binds at the HC point
    evaluations: int = 0         # load-flow evaluations used
    converged: bool = True

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        b = f", binding: {self.binding}" if self.binding else ", no binding violation"
        return (f"HC = {self.hc_kw_total:.2f} kW total "
                f"({self.hc_kw_per_bus:.2f} kW x {self.n_pv_buses} buses){b}")

    def to_dict(self) -> dict:
        """Return a JSON-serializable result for reports and downstream tools."""
        binding = self.binding
        if binding is not None and hasattr(binding, "to_dict"):
            binding = binding.to_dict()
        return {
            "hc_kw_per_bus": self.hc_kw_per_bus,
            "hc_kw_total": self.hc_kw_total,
            "n_pv_buses": self.n_pv_buses,
            "binding": binding,
            "evaluations": self.evaluations,
            "converged": self.converged,
        }


def _add_pv(net, pv_kw: dict) -> list:
    """Attach one sgen per bus in pv_kw (kW, positive = generation)."""
    sgens = []
    for bus, kw in pv_kw.items():
        if kw > 0:
            sgens.append(pp.create_sgen(net, bus=bus, p_mw=kw / 1000.0,
                                        q_mvar=0.0, name=f"PV bus {bus}"))
    return sgens


def evaluate(net_template, pv_kw: dict, mitigation=None, **limits) -> list:
    """Evaluate one PV allocation against the limits.

    ``pv_kw`` maps bus index -> PV kW. ``mitigation`` is an optional
    callable ``(net, sgen_indices) -> None`` applied after the PV is added
    and before the load flow (see :mod:`pvhostcap.mitigations`).
    Returns the list of violations (empty = feasible). A non-converged
    load flow counts as infeasible and is reported as such.
    """
    net = copy.deepcopy(net_template)
    sgens = _add_pv(net, pv_kw)
    if mitigation is not None:
        mitigation(net, sgens)
    if not run_case(net):
        return [Violation("non_converged", "load flow", 1.0, 1.0)]
    return check_violations(net, **limits)


def resolve_bus(net_template, name_or_idx) -> int:
    """Resolve a bus name (str) or pandapower bus index (int) to a bus index.

    Engineers think in names ("LV4"), not integer indices. Raises
    ValueError for unknown or ambiguous names.
    """
    if isinstance(name_or_idx, str):
        matches = net_template.bus.index[net_template.bus.name == name_or_idx].tolist()
        if not matches:
            known = sorted(net_template.bus.name.dropna().unique().tolist())
            raise ValueError(f"no bus named {name_or_idx!r}. "
                             f"Known buses: {known}")
        if len(matches) > 1:
            raise ValueError(f"ambiguous bus name {name_or_idx!r}: "
                             f"{len(matches)} buses share it")
        return int(matches[0])
    return int(name_or_idx)


def connection_check(net_template, bus, pv_kw: float, **limits) -> tuple:
    """Answer the DSO's everyday question: can this bus take ``pv_kw`` kW of new PV?

    ``bus`` may be a bus name (``"LV4"``) or a pandapower bus index.
    Returns ``(approved, violations)`` where ``approved`` is True when the
    allocation produces no violations. This is a thin wrapper over
    :func:`evaluate` for the single-bus connection-offer case.
    """
    idx = resolve_bus(net_template, bus)
    violations = evaluate(net_template, {idx: pv_kw}, **limits)
    return (not violations, violations)


def _bisect(feasible, hi_start: float = 1.0, tol: float = 0.05,
            hi_cap: float = 1e6) -> tuple:
    """Bisection on a monotone feasible(size)->bool predicate.

    Returns (size, evaluations). ``feasible(0)`` is assumed True; if it is
    not, (0.0, n) is returned.
    """
    n = 0
    if not feasible(0.0):
        return 0.0, 1
    n += 1
    hi = hi_start
    while True:
        n += 1
        if not feasible(hi):
            break
        hi *= 2.0
        if hi > hi_cap:
            return hi_cap, n
    lo = hi / 2.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        n += 1
        if feasible(mid):
            lo = mid
        else:
            hi = mid
    return lo, n


def system_hosting_capacity(
    net_template,
    load_buses: list,
    mitigation=None,
    tol_kw: float = 0.05,
    **limits,
) -> HostingCapacityResult:
    """System HC: max *uniform* per-bus PV before the first violation.

    Every bus in ``load_buses`` gets the same PV size; bisection finds the
    largest size with zero violations. Returns the HC point plus the
    binding violation evaluated just above it.

    Raises ValueError if ``load_buses`` is empty.
    """
    buses = list(load_buses)
    if not buses:
        raise ValueError("load_buses must contain at least one bus")

    def feasible(kw: float) -> bool:
        return not evaluate(net_template, {b: kw for b in buses},
                            mitigation=mitigation, **limits)

    hc_per_bus, n_eval = _bisect(feasible, tol=tol_kw)
    # binding violation just above the HC point
    above = evaluate(net_template, {b: hc_per_bus + max(tol_kw, 0.01)
                                    for b in buses},
                     mitigation=mitigation, **limits)
    return HostingCapacityResult(
        hc_kw_per_bus=hc_per_bus,
        hc_kw_total=hc_per_bus * len(buses),
        n_pv_buses=len(buses),
        binding=binding_violation(above),
        evaluations=n_eval + 1,
        converged=True,
    )


def locational_hosting_capacity(
    net_template,
    load_buses: list,
    mitigation=None,
    tol_kw: float = 0.05,
    **limits,
) -> dict:
    """Locational HC: max PV each bus can host *on its own*.

    For every bus in ``load_buses``, bisection finds the largest PV size at
    that bus alone (all other buses at zero PV) with zero violations.
    Returns ``{bus: HostingCapacityResult}``. This is the "weak-bus map" of
    the feeder — the quantity a DSO actually needs for connection offers.

    Raises ValueError if ``load_buses`` is empty.
    """
    buses = list(load_buses)
    if not buses:
        raise ValueError("load_buses must contain at least one bus")
    out = {}
    for b in buses:
        def feasible(kw: float, _b=b) -> bool:
            return not evaluate(net_template, {_b: kw},
                                mitigation=mitigation, **limits)

        hc, n_eval = _bisect(feasible, tol=tol_kw)
        above = evaluate(net_template, {b: hc + max(tol_kw, 0.01)},
                         mitigation=mitigation, **limits)
        out[b] = HostingCapacityResult(
            hc_kw_per_bus=hc,
            hc_kw_total=hc,
            n_pv_buses=1,
            binding=binding_violation(above),
            evaluations=n_eval + 1,
            converged=True,
        )
    return out
