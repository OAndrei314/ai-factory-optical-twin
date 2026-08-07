from __future__ import annotations

import argparse

from .config import ARCHITECTURES, FAULTS, SimulationConfig
from .pipeline import run_twin
from .report import write_artifacts, write_comparison_artifacts, write_matrix_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-factory-optical-twin")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="simulate an optical AI-factory scenario")
    run.add_argument("--architecture", choices=sorted(ARCHITECTURES), default="cpo")
    run.add_argument("--fault", choices=sorted(FAULTS), default="fiber_contamination")
    run.add_argument("--out", required=True, help="output directory for telemetry and reports")
    run.add_argument("--racks", type=int, default=8)
    run.add_argument("--gpus-per-rack", type=int, default=8)
    run.add_argument("--steps", type=int, default=180)
    run.add_argument("--seed", type=int, default=7)
    compare = sub.add_parser("compare", help="compare architectures under one fault")
    compare.add_argument("--fault", choices=sorted(FAULTS), default="fiber_contamination")
    compare.add_argument("--out", required=True, help="output directory for comparison reports")
    compare.add_argument("--racks", type=int, default=8)
    compare.add_argument("--gpus-per-rack", type=int, default=8)
    compare.add_argument("--steps", type=int, default=180)
    compare.add_argument("--seed", type=int, default=7)
    matrix = sub.add_parser("matrix", help="run every architecture/fault pair as an exposure matrix")
    matrix.add_argument("--out", required=True, help="output directory for matrix reports")
    matrix.add_argument("--racks", type=int, default=8)
    matrix.add_argument("--gpus-per-rack", type=int, default=8)
    matrix.add_argument("--steps", type=int, default=180)
    matrix.add_argument("--seed", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        sim_config = SimulationConfig(
            racks=args.racks,
            gpus_per_rack=args.gpus_per_rack,
            steps=args.steps,
            seed=args.seed,
        )
        run = run_twin(args.architecture, args.fault, sim_config=sim_config)
        paths = write_artifacts(args.out, run.result, run.diagnosis, run.economics, run.mitigations)
        print(f"architecture: {run.result.fabric.architecture.name}")
        print(f"fault: {run.result.fault}")
        print(f"diagnosis: {run.diagnosis.primary} ({run.diagnosis.confidence:.1%})")
        print(f"throughput index: {run.result.average_throughput_index:.3f}")
        print(f"modeled impact: ${run.economics.total_impact_usd_day:,.2f}/day")
        print(f"dashboard: {paths['dashboard']}")
        return 0
    if args.command == "compare":
        sim_config = SimulationConfig(
            racks=args.racks,
            gpus_per_rack=args.gpus_per_rack,
            steps=args.steps,
            seed=args.seed,
        )
        runs = tuple(
            run_twin(architecture, args.fault, sim_config=sim_config)
            for architecture in sorted(ARCHITECTURES)
        )
        paths = write_comparison_artifacts(args.out, runs)
        for run in runs:
            print(
                f"{run.result.fabric.architecture.name}: "
                f"throughput={run.result.average_throughput_index:.3f}, "
                f"impact=${run.economics.total_impact_usd_day:,.2f}/day"
            )
        print(f"comparison: {paths['html']}")
        return 0
    if args.command == "matrix":
        sim_config = SimulationConfig(
            racks=args.racks,
            gpus_per_rack=args.gpus_per_rack,
            steps=args.steps,
            seed=args.seed,
        )
        runs = tuple(
            run_twin(architecture, fault, sim_config=sim_config)
            for architecture in sorted(ARCHITECTURES)
            for fault in sorted(FAULTS)
        )
        paths = write_matrix_artifacts(args.out, runs)
        top = max(runs, key=lambda run: run.economics.total_impact_usd_day)
        print(
            "top exposure: "
            f"{top.result.fabric.architecture.name}/{top.result.fault} "
            f"${top.economics.total_impact_usd_day:,.2f}/day"
        )
        print(f"matrix: {paths['html']}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
