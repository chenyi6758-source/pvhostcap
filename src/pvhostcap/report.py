"""Text summaries, reports, and matplotlib figures for HC results."""

import html
import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

__all__ = [
    "summarize_system",
    "summarize_locational",
    "summarize_comparison",
    "render_html_report",
    "plot_voltage_profile",
    "plot_locational_map",
    "plot_mitigation_comparison",
]


def summarize_system(result) -> str:
    lines = [
        f"System hosting capacity : {result.hc_kw_total:7.2f} kW total",
        f"                        ({result.hc_kw_per_bus:.2f} kW x "
        f"{result.n_pv_buses} buses, {result.evaluations} load flows)",
    ]
    if result.binding is not None:
        lines.append(f"Binding constraint     : {result.binding}")
    else:
        lines.append("Binding constraint     : none (search hit the upper cap)")
    return "\n".join(lines)


def summarize_locational(net, loc: dict) -> str:
    rows = []
    for bus, res in loc.items():
        name = net.bus.at[bus, "name"]
        bind = res.binding.kind if res.binding else "-"
        rows.append(f"  bus {name:>8}: {res.hc_kw_per_bus:7.2f} kW   binds: {bind}")
    return "Locational hosting capacity (PV at that bus alone):\n" + "\n".join(rows)


def summarize_comparison(comp: dict, baseline: str = "none") -> str:
    """One-line-per-strategy HC table with % gain vs the baseline strategy.

    ``baseline`` names the strategy to compare against; it defaults to
    ``"none"`` and falls back to the first strategy in ``comp`` when that
    key is absent, so the table never crashes on a custom strategy set.
    """
    base_key = baseline if baseline in comp else next(iter(comp))
    base = comp[base_key].hc_kw_total
    rows = [f"Mitigation comparison (system HC, baseline: {base_key}):"]
    for name, res in comp.items():
        gain = (res.hc_kw_total / base - 1.0) * 100.0 if base > 0 else 0.0
        rows.append(f"  {name:>15}: {res.hc_kw_total:7.2f} kW   ({gain:+.1f}% vs baseline)")
    return "\n".join(rows)


def render_html_report(
    title: str,
    system_text: str,
    locational_text: str,
    mitigation_text: str,
    json_payload: dict,
) -> str:
    """Render a self-contained HTML report from existing study results."""
    payload = json.dumps(json_payload, indent=2, ensure_ascii=False)
    sections = (
        ("System hosting capacity", system_text),
        ("Locational hosting capacity", locational_text),
        ("Mitigation comparison", mitigation_text),
    )
    rendered = "\n".join(
        f"<section><h2>{html.escape(heading)}</h2>"
        f"<pre>{html.escape(text)}</pre></section>"
        for heading, text in sections
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #17202a; }}
    section {{ border: 1px solid #d8dee4; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
    pre {{ white-space: pre-wrap; background: #f6f8fa; padding: 1rem; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p>Deterministic first-pass screen; not an interconnection guarantee.</p>
  {rendered}
  <details><summary>Machine-readable JSON</summary><pre>{html.escape(payload)}</pre></details>
</body>
</html>
"""


def plot_voltage_profile(net, load_buses, title="Bus voltages at HC point"):
    """Bar chart of per-unit voltages on the PV buses of a solved case."""
    names = [net.bus.at[b, "name"] for b in load_buses]
    volts = [float(net.res_bus.vm_pu.at[b]) for b in load_buses]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.bar(names, volts, color="steelblue")
    ax.axhline(1.05, color="red", linestyle="--", label="vmax = 1.05 p.u.")
    ax.axhline(0.90, color="red", linestyle=":", label="vmin = 0.90 p.u.")
    ax.set_ylabel("Voltage (p.u.)")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_locational_map(net, loc: dict, title="Locational hosting capacity"):
    names = [net.bus.at[b, "name"] for b in loc]
    hcs = [loc[b].hc_kw_per_bus for b in loc]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.bar(names, hcs, color="darkorange")
    ax.set_ylabel("Hosting capacity (kW)")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_mitigation_comparison(comp: dict, title="Mitigation comparison"):
    names = list(comp.keys())
    hcs = [comp[n].hc_kw_total for n in names]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(names, hcs, color="seagreen")
    ax.set_ylabel("System HC (kW)")
    ax.set_title(title)
    fig.tight_layout()
    return fig
