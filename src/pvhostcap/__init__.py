"""pvhostcap — deterministic PV hosting-capacity screening for distribution feeders.

Built on pandapower. Answers two practical DSO questions:

1. **System hosting capacity**: how much PV (uniformly spread over the
   feeder's load buses) can this feeder take before the first violation?
2. **Locational hosting capacity**: how much PV can *each individual bus*
   take on its own — i.e. where is the feeder weak?

Plus a side-by-side comparison of classic mitigation measures
(reactive-power control, OLTC tap change) and their effect on the numbers.
"""

from pvhostcap.feeders import build_lv_radial, build_mv_radial
from pvhostcap.powerflow import check_violations, run_case
from pvhostcap.sweep import (
    HostingCapacityResult,
    evaluate,
    locational_hosting_capacity,
    system_hosting_capacity,
)
from pvhostcap.mitigations import (
    apply_fixed_pf_absorb,
    apply_oltc_lower,
    apply_voltvar,
    compare_strategies,
)

__version__ = "0.1.0"

__all__ = [
    "build_lv_radial",
    "build_mv_radial",
    "check_violations",
    "run_case",
    "HostingCapacityResult",
    "evaluate",
    "locational_hosting_capacity",
    "system_hosting_capacity",
    "apply_fixed_pf_absorb",
    "apply_oltc_lower",
    "apply_voltvar",
    "compare_strategies",
    "__version__",
]
