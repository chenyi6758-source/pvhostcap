"""Mitigation strategy tests."""

import sys

sys.path.insert(0, "src")

import pandapower as pp

from pvhostcap.feeders import build_lv_radial
from pvhostcap.mitigations import (
    apply_fixed_pf_absorb,
    apply_oltc_lower,
    apply_voltvar,
    compare_strategies,
)
from pvhostcap.powerflow import run_case
from pvhostcap.sweep import evaluate, system_hosting_capacity


def _small_lv():
    return build_lv_radial(n_buses=3, seg_km=0.15, load_kw=3.0)


def test_voltvar_never_hurts_hc():
    net, load_buses = _small_lv()
    base = system_hosting_capacity(net, load_buses, tol_kw=0.2)
    vv = system_hosting_capacity(net, load_buses, mitigation=apply_voltvar,
                                 tol_kw=0.2)
    assert vv.hc_kw_total >= base.hc_kw_total


def test_fixed_pf_never_hurts_hc():
    net, load_buses = _small_lv()
    base = system_hosting_capacity(net, load_buses, tol_kw=0.2)
    pf = system_hosting_capacity(net, load_buses,
                                 mitigation=apply_fixed_pf_absorb, tol_kw=0.2)
    assert pf.hc_kw_total >= base.hc_kw_total


def test_voltvar_respects_qmax():
    net, load_buses = _small_lv()
    for b in load_buses:
        pp.create_sgen(net, bus=b, p_mw=8 / 1000.0, q_mvar=0.0)
    sgens = list(net.sgen.index)
    apply_voltvar(net, sgens)
    assert run_case(net)
    for i in sgens:
        p = net.sgen.at[i, "p_mw"]
        q = net.sgen.at[i, "q_mvar"]
        assert -0.44 * p - 1e-9 <= q <= 1e-9  # absorb only, within rating


def test_oltc_lowers_lv_voltage():
    net, load_buses = _small_lv()
    lv0 = net.bus[net.bus.name == "LV busbar"].index[0]
    assert run_case(net)
    v_before = float(net.res_bus.vm_pu.at[lv0])
    apply_oltc_lower(net, [])
    assert run_case(net)
    v_after = float(net.res_bus.vm_pu.at[lv0])
    assert v_after < v_before


def test_oltc_never_hurts_hc():
    net, load_buses = _small_lv()
    base = system_hosting_capacity(net, load_buses, tol_kw=0.2)
    oltc = system_hosting_capacity(net, load_buses, mitigation=apply_oltc_lower,
                                   tol_kw=0.2)
    assert oltc.hc_kw_total >= base.hc_kw_total


def test_compare_strategies_keys():
    net, load_buses = _small_lv()
    comp = compare_strategies(net, load_buses,
                              strategies=("none", "voltvar"), tol_kw=0.5)
    assert set(comp.keys()) == {"none", "voltvar"}
    assert comp["voltvar"].hc_kw_total >= comp["none"].hc_kw_total
