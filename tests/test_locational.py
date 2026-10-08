"""Locational (per-bus) hosting-capacity tests."""

import sys

sys.path.insert(0, "src")

from pvhostcap.feeders import build_lv_radial
from pvhostcap.sweep import locational_hosting_capacity


def test_locational_hc_map():
    net, load_buses = build_lv_radial(n_buses=4, seg_km=0.15, load_kw=3.0)
    loc = locational_hosting_capacity(net, load_buses, tol_kw=0.2)
    assert set(loc.keys()) == set(load_buses)
    for res in loc.values():
        assert res.hc_kw_per_bus > 0
        assert res.n_pv_buses == 1


def test_far_end_bus_is_weakest():
    # Classic radial-feeder physics: the electrically farthest bus sees the
    # largest voltage rise per kW, so it hosts the least PV on its own.
    net, load_buses = build_lv_radial(n_buses=4, seg_km=0.15, load_kw=3.0)
    loc = locational_hosting_capacity(net, load_buses, tol_kw=0.2)
    weakest = min(loc, key=lambda b: loc[b].hc_kw_per_bus)
    strongest = max(loc, key=lambda b: loc[b].hc_kw_per_bus)
    assert weakest == load_buses[-1]    # LV4, far end
    assert strongest == load_buses[0]   # LV1, next to the transformer
    assert loc[weakest].binding.kind == "overvoltage"


def test_locational_hc_exceeds_uniform_share():
    # One bus alone can always host at least as much as its uniform share
    # of the system HC (fewer simultaneous injections -> less rise).
    from pvhostcap.sweep import system_hosting_capacity
    net, load_buses = build_lv_radial(n_buses=4, seg_km=0.15, load_kw=3.0)
    sys_hc = system_hosting_capacity(net, load_buses, tol_kw=0.2)
    loc = locational_hosting_capacity(net, load_buses, tol_kw=0.2)
    for res in loc.values():
        assert res.hc_kw_per_bus >= sys_hc.hc_kw_per_bus
