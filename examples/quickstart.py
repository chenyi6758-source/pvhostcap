"""One-click example: screen two feeders, map the weak buses, compare mitigations.

Run from the repo root::

    python examples/quickstart.py

Prints the hosting-capacity results and saves three figures under
``examples/output/``.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandapower as pp

import pvhostcap
from pvhostcap import (
    apply_voltvar,
    build_lv_radial,
    build_mv_radial,
    compare_strategies,
    evaluate,
    locational_hosting_capacity,
    system_hosting_capacity,
)
from pvhostcap.powerflow import run_case
from pvhostcap.report import (
    plot_locational_map,
    plot_mitigation_comparison,
    plot_voltage_profile,
    summarize_comparison,
    summarize_locational,
    summarize_system,
)

OUT = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    print(f"pvhostcap {pvhostcap.__version__}\n")

    # --- 1. LV residential feeder: system HC --------------------------------
    net, load_buses = build_lv_radial()
    res = system_hosting_capacity(net, load_buses)
    print("=== LV radial feeder (0.4 kV, 6 load buses) ===")
    print(summarize_system(res))

    # voltage profile at the HC point (for the plot)
    net_hc = copy.deepcopy(net)
    for b in load_buses:
        pp.create_sgen(net_hc, bus=b, p_mw=res.hc_kw_per_bus / 1000.0)
    assert run_case(net_hc)
    plot_voltage_profile(net_hc, load_buses,
                         title="LV feeder: bus voltages at HC point").savefig(
        os.path.join(OUT, "lv_voltage_profile.png"), dpi=120)

    # --- 2. Locational HC: the weak-bus map ---------------------------------
    loc = locational_hosting_capacity(net, load_buses)
    print()
    print(summarize_locational(net, loc))
    plot_locational_map(net, loc).savefig(
        os.path.join(OUT, "lv_locational_map.png"), dpi=120)

    # --- 3. Mitigation comparison ------------------------------------------
    comp = compare_strategies(net, load_buses)
    print()
    print(summarize_comparison(comp))
    plot_mitigation_comparison(comp).savefig(
        os.path.join(OUT, "lv_mitigation_comparison.png"), dpi=120)

    # --- 4. MV feeder: a thermally-bound contrast ---------------------------
    net_mv, mv_buses = build_mv_radial()
    res_mv = system_hosting_capacity(net_mv, mv_buses, tol_kw=5.0)
    print()
    print("=== MV feeder (10 kV, 5 load buses) ===")
    print(summarize_system(res_mv))

    print(f"\nFigures saved to {OUT}/")


if __name__ == "__main__":
    main()
