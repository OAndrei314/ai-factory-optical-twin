from __future__ import annotations

from dataclasses import dataclass

from .config import EconomicsConfig
from .diagnostics import Diagnosis
from .economics import EconomicSummary
from .simulator import SimulationResult


@dataclass(frozen=True)
class MitigationOption:
    name: str
    expected_throughput_index: float
    avoided_loss_usd_day: float
    action_cost_usd: float
    net_value_usd_day: float
    rationale: str


def rank_mitigations(
    result: SimulationResult,
    diagnosis: Diagnosis,
    economics: EconomicSummary,
    config: EconomicsConfig,
) -> tuple[MitigationOption, ...]:
    current = result.average_throughput_index
    degraded_ratio = result.max_degraded_links / max(len(result.fabric.links), 1)
    options: list[MitigationOption] = []

    options.append(
        _option(
            name="observe_only",
            current=current,
            recovered=current,
            action_cost=0.0,
            economics=economics,
            rationale="No operational change. Useful only when the diagnosis is nominal.",
        )
    )

    reroute_gain = min(0.10, degraded_ratio * 0.45)
    options.append(
        _option(
            name="reroute_away_from_degraded_links",
            current=current,
            recovered=min(1.0, current + reroute_gain),
            action_cost=config.maintenance_hour_usd * 0.5,
            economics=economics,
            rationale="Move traffic away from weak links. Fast response, but it can increase hot-spot utilization.",
        )
    )

    if diagnosis.primary == "thermal_coupling":
        recovered = min(1.0, current + 0.08)
        cost = config.maintenance_hour_usd + 0.03 * result.fabric.config.gpu_count * 24 * config.gpu_hour_usd
        rationale = "Throttle and rebalance hot racks to lower BER risk while preserving most training capacity."
    else:
        recovered = max(0.0, current - 0.02)
        cost = config.maintenance_hour_usd
        rationale = "Thermal throttle is conservative when the root cause is not thermal."
    options.append(
        _option(
            name="thermal_rebalance",
            current=current,
            recovered=recovered,
            action_cost=cost,
            economics=economics,
            rationale=rationale,
        )
    )

    if diagnosis.primary == "fiber_or_connector_contamination":
        recovered = min(1.0, current + 0.16)
        cost = config.maintenance_hour_usd * 0.75 + 120.0
        rationale = "Clean and inspect the affected optical path before replacing hardware."
    elif diagnosis.primary == "laser_aging_or_bias_headroom_loss":
        recovered = min(1.0, current + 0.16)
        cost = config.maintenance_hour_usd * 2.0 + 900.0
        rationale = "Schedule module swap for the affected rack/link set if bias headroom is exhausted."
    else:
        recovered = min(1.0, current + 0.05)
        cost = config.maintenance_hour_usd * 2.0 + 900.0
        rationale = "Hardware touch labor is expensive unless the diagnosis points to an optical path."
    options.append(
        _option(
            name="clean_or_replace_optical_path",
            current=current,
            recovered=recovered,
            action_cost=cost,
            economics=economics,
            rationale=rationale,
        )
    )

    if diagnosis.primary == "supply_or_signal_integrity_burst":
        recovered = min(1.0, current + 0.12)
        cost = config.maintenance_hour_usd * 1.5
        rationale = "Inspect power telemetry and retime affected lanes after bursty BER events."
    else:
        recovered = current
        cost = config.maintenance_hour_usd * 1.5
        rationale = "Power integrity work is not first-line unless BER is bursty across links."
    options.append(
        _option(
            name="power_integrity_check",
            current=current,
            recovered=recovered,
            action_cost=cost,
            economics=economics,
            rationale=rationale,
        )
    )

    return tuple(sorted(options, key=lambda option: option.net_value_usd_day, reverse=True))


def _option(
    name: str,
    current: float,
    recovered: float,
    action_cost: float,
    economics: EconomicSummary,
    rationale: str,
) -> MitigationOption:
    current_loss = economics.lost_compute_usd_day + economics.downtime_risk_usd_day
    remaining_loss_fraction = max(0.0, 1.0 - recovered)
    current_loss_fraction = max(0.001, 1.0 - current)
    recovered_loss = current_loss * min(1.0, remaining_loss_fraction / current_loss_fraction)
    avoided = max(0.0, current_loss - recovered_loss)
    net = avoided - action_cost / 7.0
    return MitigationOption(
        name=name,
        expected_throughput_index=round(recovered, 3),
        avoided_loss_usd_day=round(avoided, 2),
        action_cost_usd=round(action_cost, 2),
        net_value_usd_day=round(net, 2),
        rationale=rationale,
    )
