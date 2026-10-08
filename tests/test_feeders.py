"""Feeder construction tests."""

import sys

sys.path.insert(0, "src")

import pandapower as pp

from pvhostcap.feeders import build_lv_radial, build_mv_radial
from pvhostcap.powerflow import run_case


def test_lv_feeder_builds_and_converges():
    net, load_buses = build_lv_radial()
    assert len(load_buses) == 6
    assert len(net.load) == 6
    assert abs(net.load.p_mw.sum() * 1000 - 18.0) < 1e-9  # 6 x 3 kW
    assert run_case(net)


def test_lv_feeder_custom_size():
    net, load_buses = build_lv_radial(n_buses=3, seg_km=0.2, load_kw=5.0)
    assert len(load_buses) == 3
    assert abs(net.load.p_mw.sum() * 1000 - 15.0) < 1e-9
    assert run_case(net)


def test_mv_feeder_builds_and_converges():
    net, load_buses = build_mv_radial()
    assert len(load_buses) == 5
    assert len(net.load) == 5
    assert abs(net.load.p_mw.sum() * 1000 - 2000.0) < 1e-9  # 5 x 400 kW
    assert run_case(net)
