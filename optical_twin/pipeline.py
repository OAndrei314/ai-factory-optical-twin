from __future__ import annotations

from dataclasses import dataclass

from .config import ARCHITECTURES, EconomicsConfig, SimulationConfig, WorkloadConfig
from .diagnostics import Diagnosis, diagnose
from .economics import EconomicSummary, summarize_economics
from .mitigation import MitigationOption, rank_mitigations
from .simulator import SimulationResult, simulate_fabric
from .topology import build_fabric


@dataclass(frozen=True)
class TwinRun:
    result: SimulationResult
    diagnosis: Diagnosis
    economics: EconomicSummary
    mitigations: tuple[MitigationOption, ...]


def run_twin(
    architecture: str,
    fault: str,
    sim_config: SimulationConfig | None = None,
    workload: WorkloadConfig | None = None,
    economics_config: EconomicsConfig | None = None,
) -> TwinRun:
    sim_config = sim_config or SimulationConfig()
    workload = workload or WorkloadConfig()
    economics_config = economics_config or EconomicsConfig()
    profile = ARCHITECTURES[architecture]
    fabric = build_fabric(sim_config, profile)
    result = simulate_fabric(fabric, workload, fault=fault, seed=sim_config.seed)
    diagnosis = diagnose(result)
    economics = summarize_economics(result, economics_config)
    mitigations = rank_mitigations(result, diagnosis, economics, economics_config)
    return TwinRun(
        result=result,
        diagnosis=diagnosis,
        economics=economics,
        mitigations=mitigations,
    )
