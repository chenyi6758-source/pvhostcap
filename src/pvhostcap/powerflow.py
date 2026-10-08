"""Load-flow execution and violation checking."""

from dataclasses import dataclass

import pandapower as pp

__all__ = ["Violation", "run_case", "check_violations"]


@dataclass
class Violation:
    """A single operating-limit violation found in a solved case."""

    kind: str            # 'overvoltage' | 'undervoltage' | 'line_overload' | 'trafo_overload'
    element: str         # e.g. 'bus LV6', 'line cable LV5-LV6'
    value: float         # measured quantity (p.u. or %)
    limit: float         # the violated limit (p.u. or %)

    @property
    def severity(self) -> float:
        """Relative exceedance: 1.10 means 10% beyond the limit."""
        return self.value / self.limit

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        unit = "p.u." if "voltage" in self.kind else "%"
        return (f"{self.kind} at {self.element}: "
                f"{self.value:.4f} {unit} (limit {self.limit:.4f})")


def run_case(net) -> bool:
    """Run a Newton-Raphson load flow. Returns True if it converged."""
    try:
        pp.runpp(net, numba=True)
    except Exception:  # LoadflowNotConverged and friends
        return False
    return bool(net.get("converged", True))


def _name(net, table: str, idx: int) -> str:
    try:
        nm = net[table].at[idx, "name"]
        if isinstance(nm, str) and nm:
            return nm
    except Exception:
        pass
    return f"{table} {idx}"


def check_violations(
    net,
    vmax: float = 1.05,
    vmin: float = 0.90,
    line_limit: float = 100.0,
    trafo_limit: float = 100.0,
    kinds=("overvoltage", "line_overload", "trafo_overload"),
) -> list:
    """Check a *solved* case against operating limits.

    ``kinds`` selects which checks to apply. The default covers exactly the
    limits that get *worse* when more PV is connected (voltage rise, reverse
    thermal loading) — the right set for hosting-capacity screening. Pass
    ``kinds=("overvoltage", "undervoltage", "line_overload",
    "trafo_overload")`` for a full operating-point audit instead.
    """
    out: list = []
    if "overvoltage" in kinds:
        bad = net.res_bus[net.res_bus.vm_pu > vmax]
        for idx, row in bad.iterrows():
            out.append(Violation("overvoltage", f"bus {_name(net, 'bus', idx)}",
                                 float(row.vm_pu), vmax))
    if "undervoltage" in kinds:
        bad = net.res_bus[net.res_bus.vm_pu < vmin]
        for idx, row in bad.iterrows():
            out.append(Violation("undervoltage", f"bus {_name(net, 'bus', idx)}",
                                 float(row.vm_pu), vmin))
    if "line_overload" in kinds and len(net.line):
        bad = net.res_line[net.res_line.loading_percent > line_limit]
        for idx, row in bad.iterrows():
            out.append(Violation("line_overload",
                                 f"line {_name(net, 'line', idx)}",
                                 float(row.loading_percent), line_limit))
    if "trafo_overload" in kinds and len(net.trafo):
        bad = net.res_trafo[net.res_trafo.loading_percent > trafo_limit]
        for idx, row in bad.iterrows():
            out.append(Violation("trafo_overload",
                                 f"trafo {_name(net, 'trafo', idx)}",
                                 float(row.loading_percent), trafo_limit))
    out.sort(key=lambda v: v.severity, reverse=True)
    return out


def binding_violation(violations: list):
    """The worst violation (highest relative exceedance), or None."""
    return violations[0] if violations else None
