"""Built-in test feeders.

Two small radial feeders with deliberately *different* binding constraints:

- ``build_lv_radial`` — a 0.4 kV residential feeder. Long, thin LV cables
  make **overvoltage at the far end** the binding constraint.
- ``build_mv_radial`` — a 10 kV feeder with heavier loads. The **thermal
  limit of the head-end line** binds first.

Both are returned as ``(net, load_buses)`` where ``load_buses`` is the
ordered list of pandapower bus indices that may host PV (PV is allocated
per load bus, the usual rooftop-PV screening assumption).

The single-snapshot convention used here is the industry-standard
deterministic screening point: **minimum load / maximum PV** (a sunny
midday hour). Stochastic and time-series treatments of the same question
are reviewed in Mulenga et al. (2020) and Brohi et al. (2025).
"""

import math

import pandapower as pp

__all__ = ["build_lv_radial", "build_mv_radial"]


def build_lv_radial(
    n_buses: int = 6,
    seg_km: float = 0.15,
    load_kw: float = 3.0,
    pf: float = 0.95,
    trafo_std: str = "0.4 MVA 10/0.4 kV",
    cable_std: str = "NAYY 4x50 SE",
):
    """Build a small 0.4 kV radial residential feeder.

    Topology: 10 kV slack -> MV/LV transformer -> chain of ``n_buses``
    LV buses, each with a residential load. The far-end bus is the
    voltage-critical one.
    """
    net = pp.create_empty_network(name="lv_radial")
    b_mv = pp.create_bus(net, vn_kv=10.0, name="MV slack")
    pp.create_ext_grid(net, bus=b_mv, vm_pu=1.0, name="upstream grid")
    b_lv0 = pp.create_bus(net, vn_kv=0.4, name="LV busbar")
    pp.create_transformer(net, hv_bus=b_mv, lv_bus=b_lv0, std_type=trafo_std,
                          name="MV/LV trafo")

    q_kw = load_kw * math.tan(math.acos(pf))
    prev = b_lv0
    load_buses = []
    for i in range(1, n_buses + 1):
        b = pp.create_bus(net, vn_kv=0.4, name=f"LV{i}")
        pp.create_line(net, from_bus=prev, to_bus=b, length_km=seg_km,
                       std_type=cable_std, name=f"cable LV{i-1}-LV{i}")
        pp.create_load(net, bus=b, p_mw=load_kw / 1000.0,
                       q_mvar=q_kw / 1000.0, name=f"load LV{i}")
        load_buses.append(b)
        prev = b
    return net, load_buses


def build_mv_radial(
    n_buses: int = 5,
    seg_km: float = 1.0,
    load_kw: float = 400.0,
    pf: float = 0.95,
    trafo_std: str = "25 MVA 110/10 kV",
    cable_std: str = "NA2XS2Y 1x150 RM/25 12/20 kV",
):
    """Build a small 10 kV radial feeder with heavier lumped loads.

    Topology: 110 kV slack -> HV/MV transformer -> chain of ``n_buses``
    10 kV buses. Short, chunky cables and large loads make the **head-end
    line thermal limit** bind before far-end overvoltage.
    """
    net = pp.create_empty_network(name="mv_radial")
    b_hv = pp.create_bus(net, vn_kv=110.0, name="HV slack")
    pp.create_ext_grid(net, bus=b_hv, vm_pu=1.0, name="upstream grid")
    b_mv0 = pp.create_bus(net, vn_kv=10.0, name="MV busbar")
    pp.create_transformer(net, hv_bus=b_hv, lv_bus=b_mv0, std_type=trafo_std,
                          name="HV/MV trafo")

    q_kw = load_kw * math.tan(math.acos(pf))
    prev = b_mv0
    load_buses = []
    for i in range(1, n_buses + 1):
        b = pp.create_bus(net, vn_kv=10.0, name=f"MV{i}")
        pp.create_line(net, from_bus=prev, to_bus=b, length_km=seg_km,
                       std_type=cable_std, name=f"cable MV{i-1}-MV{i}")
        pp.create_load(net, bus=b, p_mw=load_kw / 1000.0,
                       q_mvar=q_kw / 1000.0, name=f"load MV{i}")
        load_buses.append(b)
        prev = b
    return net, load_buses
