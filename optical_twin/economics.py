from __future__ import annotations

from dataclasses import dataclass

from .config import EconomicsConfig
from .simulator import SimulationResult


@dataclass(frozen=True)
class EconomicSummary:
    optical_energy_kwh_day: float
    optical_energy_cost_usd_day: float
    estimated_optics_capex_usd: float
    lost_gpu_hours_day: float
    lost_compute_usd_day: float
    downtime_risk_usd_day: float
    total_impact_usd_day: float


@dataclass(frozen=True)
class ArchitectureBusinessCase:
    baseline_impact_usd_day: float
    candidate_impact_usd_day: float
    daily_savings_usd: float
    capex_delta_usd: float
    payback_days: float
    decision: str


def summarize_economics(
    result: SimulationResult,
    config: EconomicsConfig,
    horizon_hours: float = 24.0,
) -> EconomicSummary:
    avg_throughput = result.average_throughput_index
    lost_fraction = max(0.0, 1.0 - avg_throughput)
    gpu_count = result.fabric.config.gpu_count
    optical_energy = result.fabric.optical_power_kw * horizon_hours
    optical_energy_cost = optical_energy * config.energy_usd_per_kwh
    capex = result.fabric.optical_endpoint_count * result.fabric.architecture.transceiver_cost_usd
    lost_gpu_hours = gpu_count * horizon_hours * lost_fraction
    lost_compute = lost_gpu_hours * config.gpu_hour_usd
    critical_fraction = sum(1 for step in result.fleet if step.throughput_index < 0.82) / len(result.fleet)
    downtime_risk = critical_fraction * horizon_hours * config.downtime_penalty_usd_per_hour
    total = optical_energy_cost + lost_compute + downtime_risk
    return EconomicSummary(
        optical_energy_kwh_day=round(optical_energy, 3),
        optical_energy_cost_usd_day=round(optical_energy_cost, 2),
        estimated_optics_capex_usd=round(capex, 2),
        lost_gpu_hours_day=round(lost_gpu_hours, 2),
        lost_compute_usd_day=round(lost_compute, 2),
        downtime_risk_usd_day=round(downtime_risk, 2),
        total_impact_usd_day=round(total, 2),
    )


def compare_architecture_business_case(
    baseline: EconomicSummary,
    candidate: EconomicSummary,
    max_payback_days: float = 365.0,
) -> ArchitectureBusinessCase:
    """Compare two architecture economics summaries as a capex payback case."""
    daily_savings = baseline.total_impact_usd_day - candidate.total_impact_usd_day
    capex_delta = candidate.estimated_optics_capex_usd - baseline.estimated_optics_capex_usd
    if daily_savings <= 0:
        payback_days = float("inf")
        decision = "stay_with_baseline"
    else:
        payback_days = max(0.0, capex_delta) / daily_savings
        decision = "upgrade_candidate" if payback_days <= max_payback_days else "needs_business_review"
    return ArchitectureBusinessCase(
        baseline_impact_usd_day=round(baseline.total_impact_usd_day, 2),
        candidate_impact_usd_day=round(candidate.total_impact_usd_day, 2),
        daily_savings_usd=round(daily_savings, 2),
        capex_delta_usd=round(capex_delta, 2),
        payback_days=round(payback_days, 2) if payback_days != float("inf") else payback_days,
        decision=decision,
    )
