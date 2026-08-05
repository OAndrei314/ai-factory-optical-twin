from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureProfile:
    name: str
    link_capacity_tbps: float
    link_power_w: float
    base_ber: float
    thermal_coupling: float
    transceiver_cost_usd: float
    notes: str


@dataclass(frozen=True)
class SimulationConfig:
    racks: int = 8
    gpus_per_rack: int = 8
    spines: int = 4
    parallel_links: int = 2
    steps: int = 180
    seed: int = 7

    @property
    def gpu_count(self) -> int:
        return self.racks * self.gpus_per_rack


@dataclass(frozen=True)
class WorkloadConfig:
    name: str = "frontier-training-allreduce"
    base_compute_step_ms: float = 220.0
    allreduce_gb_per_gpu: float = 18.0
    target_step_ms: float = 430.0


@dataclass(frozen=True)
class EconomicsConfig:
    energy_usd_per_kwh: float = 0.12
    gpu_hour_usd: float = 8.00
    maintenance_hour_usd: float = 180.0
    downtime_penalty_usd_per_hour: float = 12000.0


ARCHITECTURES: dict[str, ArchitectureProfile] = {
    "pluggable": ArchitectureProfile(
        name="pluggable",
        link_capacity_tbps=0.8,
        link_power_w=14.0,
        base_ber=8e-13,
        thermal_coupling=0.35,
        transceiver_cost_usd=1250.0,
        notes="Illustrative pluggable optics profile.",
    ),
    "cpo": ArchitectureProfile(
        name="cpo",
        link_capacity_tbps=1.6,
        link_power_w=4.4,
        base_ber=5e-13,
        thermal_coupling=0.95,
        transceiver_cost_usd=2200.0,
        notes="Illustrative co-packaged-optics-style profile.",
    ),
}


FAULTS = {"none", "fiber_contamination", "laser_aging", "thermal_coupling", "supply_sag"}
