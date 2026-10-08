"""Violation detection tests on hand-built cases."""

import sys

sys.path.insert(0, "src")

import pandapower as pp

from pvhostcap.feeders import build_lv_radial
from pvhostcap.powerflow import binding_violation, check_violations, run_case


def _two_bus(cable="NAYY 4x50 SE", length_km=0.2):
    net = pp.create_empty_network()
    b1 = pp.create_bus(net, vn_kv=0.4, name="slack")
    b2 = pp.create_bus(net, vn_kv=0.4, name="far")
    pp.create_ext_grid(net, bus=b1, vm_pu=1.0)
    pp.create_line(net, from_bus=b1, to_bus=b2, length_km=length_km,
                   std_type=cable, name="feeder")
    return net, b1, b2


def test_overvoltage_detected():
    net = pp.create_empty_network()
    b1 = pp.create_bus(net, vn_kv=0.4, name="slack")
    b2 = pp.create_bus(net, vn_kv=0.4, name="far")
    pp.create_ext_grid(net, bus=b1, vm_pu=1.0)
    # thin, long stub: 90 kW raises the far-end voltage past 1.05 p.u.
    # while the 98 kVA cable stays thermally safe
    pp.create_line(net, from_bus=b1, to_bus=b2, length_km=0.2,
                   std_type="NAYY 4x50 SE", name="thin stub")
    pp.create_sgen(net, bus=b2, p_mw=0.090)
    assert run_case(net)
    viols = check_violations(net)
    assert viols, "expected an overvoltage violation"
    assert viols[0].kind == "overvoltage"
    assert "far" in viols[0].element
    assert viols[0].severity > 1.0


def test_no_violation_clean_case():
    net, b1, b2 = _two_bus()
    pp.create_sgen(net, bus=b2, p_mw=0.005)
    assert run_case(net)
    assert check_violations(net) == []


def test_line_overload_detected():
    # thin 4x50 cable: 98 kVA thermal rating; 110 kW reverse flow overloads
    # it while the voltage stays below the relaxed 1.20 p.u. check limit
    net, b1, b2 = _two_bus(cable="NAYY 4x50 SE", length_km=0.1)
    pp.create_sgen(net, bus=b2, p_mw=0.110)
    assert run_case(net)
    kinds = {v.kind for v in check_violations(net, vmax=1.20)}
    assert "line_overload" in kinds


def test_undervoltage_opt_in():
    net, load_buses = build_lv_radial(load_kw=8.0)  # heavy load, no PV
    assert run_case(net)
    assert check_violations(net) == []  # not part of default HC kinds
    under = check_violations(net, vmin=0.99,
                             kinds=("undervoltage",))
    assert under and under[0].kind == "undervoltage"


def test_binding_violation_picks_worst():
    net, b1, b2 = _two_bus()
    pp.create_sgen(net, bus=b2, p_mw=0.090)
    assert run_case(net)
    viols = check_violations(net)
    worst = binding_violation(viols)
    assert worst is viols[0]
    assert binding_violation([]) is None
