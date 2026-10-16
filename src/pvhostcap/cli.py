"""Command-line entry point for built-in feeder screening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pvhostcap import build_lv_radial, build_mv_radial
from pvhostcap.mitigations import compare_strategies
from pvhostcap.report import (
    render_html_report,
    summarize_comparison,
    summarize_locational,
    summarize_system,
)
from pvhostcap.sweep import locational_hosting_capacity, system_hosting_capacity


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pvhostcap",
        description="Run deterministic PV hosting-capacity screening.",
    )
    parser.add_argument("--feeder", choices=("lv", "mv"), default="lv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pvhostcap-report"),
        help="directory for JSON and HTML reports",
    )
    parser.add_argument(
        "--tol-kw",
        type=float,
        default=None,
        help="bisection tolerance in kW; defaults to 0.05 for LV and 5.0 for MV",
    )
    parser.add_argument("--no-locational", action="store_true")
    parser.add_argument("--no-mitigations", action="store_true")
    return parser


def run(
    feeder: str,
    output_dir: Path,
    tol_kw: float | None = None,
    locational: bool = True,
    mitigations: bool = True,
) -> dict:
    """Run a built-in feeder study and write JSON/HTML reports."""
    builder = build_lv_radial if feeder == "lv" else build_mv_radial
    net, load_buses = builder()
    effective_tol = tol_kw if tol_kw is not None else (0.05 if feeder == "lv" else 5.0)

    system = system_hosting_capacity(net, load_buses, tol_kw=effective_tol)
    loc = locational_hosting_capacity(net, load_buses, tol_kw=effective_tol) if locational else {}
    comp = compare_strategies(net, load_buses, tol_kw=effective_tol) if mitigations else {}
    payload = {
        "feeder": feeder,
        "assumptions": {
            "study": "deterministic worst-hour screening",
            "pv_allocation": "uniform system / single-bus locational",
            "tol_kw": effective_tol,
        },
        "system": system.to_dict(),
        "locational": {str(bus): result.to_dict() for bus, result in loc.items()},
        "mitigations": {name: result.to_dict() for name, result in comp.items()},
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{feeder}-hosting-capacity.json"
    html_path = output_dir / f"{feeder}-hosting-capacity.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(
        render_html_report(
            title=f"pvhostcap report — {feeder.upper()} feeder",
            system_text=summarize_system(system),
            locational_text=summarize_locational(net, loc) if loc else "Skipped",
            mitigation_text=summarize_comparison(comp) if comp else "Skipped",
            json_payload=payload,
        ),
        encoding="utf-8",
    )

    print(summarize_system(system))
    if loc:
        print(f"\n{summarize_locational(net, loc)}")
    if comp:
        print(f"\n{summarize_comparison(comp)}")
    print(f"\nJSON report: {json_path}")
    print(f"HTML report: {html_path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run(
        feeder=args.feeder,
        output_dir=args.output_dir,
        tol_kw=args.tol_kw,
        locational=not args.no_locational,
        mitigations=not args.no_mitigations,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
