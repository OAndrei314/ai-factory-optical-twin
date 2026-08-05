from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .config import ArchitectureProfile, SimulationConfig, WorkloadConfig
from .topology import Fabric, Link


@dataclass(frozen=True)
class TelemetrySample:
    step: int
    link_id: str
    rack: int
    spine: int
    rx_power_dbm: float
    laser_bias_ma: float
    temperature_c: float
    ber: float
    utilization: float
    fec_uncorrected: int
    link_up: bool


@dataclass(frozen=True)
class FleetStep:
    step: int
    effective_capacity_tbps: float
    step_time_ms: float
    throughput_index: float
    degraded_links: int
    optical_power_kw: float


@dataclass(frozen=True)
class SimulationResult:
    fabric: Fabric
    workload: WorkloadConfig
    fault: str
    telemetry: tuple[TelemetrySample, ...]
    fleet: tuple[FleetStep, ...]
    nominal_step_time_ms: float

    @property
    def average_throughput_index(self) -> float:
        return sum(step.throughput_index for step in self.fleet) / len(self.fleet)

    @property
    def worst_step_time_ms(self) -> float:
        return max(step.step_time_ms for step in self.fleet)

    @property
    def max_degraded_links(self) -> int:
        return max(step.degraded_links for step in self.fleet)


def simulate_fabric(
    fabric: Fabric,
    workload: WorkloadConfig,
    fault: str,
    seed: int,
) -> SimulationResult:
    rng = random.Random(seed)
    nominal_capacity = fabric.total_capacity_tbps
    nominal_step_time = _step_time_ms(workload, nominal_capacity, fabric.config.gpu_count)
    telemetry: list[TelemetrySample] = []
    fleet: list[FleetStep] = []

    for step in range(fabric.config.steps):
        samples: list[TelemetrySample] = []
        for link in fabric.links:
            sample = _sample_link(
                link=link,
                architecture=fabric.architecture,
                step=step,
                steps=fabric.config.steps,
                fault=fault,
                rng=rng,
            )
            samples.append(sample)
            telemetry.append(sample)

        effective_capacity = _allreduce_effective_capacity(fabric, samples)
        step_time = _step_time_ms(workload, max(effective_capacity, 0.001), fabric.config.gpu_count)
        degraded_links = sum(1 for sample in samples if _quality_factor(sample) < 0.85)
        fleet.append(
            FleetStep(
                step=step,
                effective_capacity_tbps=effective_capacity,
                step_time_ms=step_time,
                throughput_index=nominal_step_time / step_time,
                degraded_links=degraded_links,
                optical_power_kw=fabric.optical_power_kw,
            )
        )

    return SimulationResult(
        fabric=fabric,
        workload=workload,
        fault=fault,
        telemetry=tuple(telemetry),
        fleet=tuple(fleet),
        nominal_step_time_ms=nominal_step_time,
    )


def _sample_link(
    link: Link,
    architecture: ArchitectureProfile,
    step: int,
    steps: int,
    fault: str,
    rng: random.Random,
) -> TelemetrySample:
    progress = step / max(steps - 1, 1)
    affected_rack = 2
    if fault == "fiber_contamination":
        affected = link.rack == affected_rack
    elif fault == "thermal_coupling":
        affected = link.rack in {affected_rack, affected_rack + 1}
    else:
        affected = link.rack == affected_rack

    rx_power = -2.4 + rng.gauss(0, 0.04)
    bias = 42.0 + rng.gauss(0, 0.18)
    temp = 48.0 + architecture.thermal_coupling * 2.5 + rng.gauss(0, 0.35)
    ber = architecture.base_ber * (1.0 + rng.random() * 0.25)
    utilization = 0.62 + 0.08 * math.sin(step / 17.0 + link.rack)

    if fault != "none" and step >= steps * 0.25:
        local_progress = (step - steps * 0.25) / max(steps * 0.75, 1)
        local_progress = max(0.0, min(1.0, local_progress))
        if fault == "fiber_contamination" and affected:
            rx_power -= 5.2 * local_progress
            ber *= 1 + 8000 * local_progress**2
            utilization += 0.08 * local_progress
        elif fault == "laser_aging" and link.rack == affected_rack:
            bias += 18.0 * local_progress
            rx_power -= 1.8 * local_progress
            temp += 4.5 * local_progress
            ber *= 1 + 700 * local_progress**2
        elif fault == "thermal_coupling" and affected:
            temp += 32.0 * local_progress * architecture.thermal_coupling
            bias += 7.0 * local_progress
            ber *= 1 + 3000 * architecture.thermal_coupling * local_progress**2
        elif fault == "supply_sag" and 0.42 <= progress <= 0.58 and link.rack in {1, 2, 3}:
            ber *= 6000
            rx_power -= 1.1
            utilization += 0.16

    link_up = rx_power > -9.5 and ber < 2e-6 and temp < 88.0
    fec_uncorrected = 0
    if ber > 1e-9:
        fec_uncorrected = int(min(9999, ber / 1e-10 + rng.random() * 7))

    return TelemetrySample(
        step=step,
        link_id=link.id,
        rack=link.rack,
        spine=link.spine,
        rx_power_dbm=round(rx_power, 3),
        laser_bias_ma=round(bias, 3),
        temperature_c=round(temp, 3),
        ber=ber,
        utilization=round(max(0.0, min(1.0, utilization)), 3),
        fec_uncorrected=fec_uncorrected,
        link_up=link_up,
    )


def _quality_factor(sample: TelemetrySample) -> float:
    if not sample.link_up:
        return 0.0
    penalty = 0.0
    if sample.ber > 1e-9:
        penalty += min(0.45, math.log10(sample.ber / 1e-9 + 1.0) * 0.18)
    if sample.rx_power_dbm < -6.0:
        penalty += min(0.35, (-6.0 - sample.rx_power_dbm) * 0.08)
    if sample.temperature_c > 72.0:
        penalty += min(0.25, (sample.temperature_c - 72.0) * 0.02)
    return max(0.05, 1.0 - penalty)


def _allreduce_effective_capacity(fabric: Fabric, samples: list[TelemetrySample]) -> float:
    """Approximate all-reduce sensitivity to the slowest rack.

    A bulk traffic sum hides the interesting failure mode: in synchronous training, a weak
    rack can hold the step open even when the rest of the fabric has spare capacity.
    """
    by_rack = {rack: 0.0 for rack in range(fabric.config.racks)}
    for link, sample in zip(fabric.links, samples):
        by_rack[link.rack] += link.capacity_tbps * _quality_factor(sample)
    return min(by_rack.values()) * fabric.config.racks


def _step_time_ms(workload: WorkloadConfig, capacity_tbps: float, gpu_count: int) -> float:
    traffic_gbit = workload.allreduce_gb_per_gpu * gpu_count * 8.0
    network_ms = traffic_gbit / capacity_tbps
    return workload.base_compute_step_ms + network_ms
