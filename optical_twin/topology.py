from __future__ import annotations

from dataclasses import dataclass

from .config import ArchitectureProfile, SimulationConfig


@dataclass(frozen=True)
class Link:
    id: str
    rack: int
    spine: int
    lane: int
    capacity_tbps: float
    optical_power_w: float


@dataclass(frozen=True)
class Fabric:
    config: SimulationConfig
    architecture: ArchitectureProfile
    links: tuple[Link, ...]

    @property
    def total_capacity_tbps(self) -> float:
        return sum(link.capacity_tbps for link in self.links)

    @property
    def optical_power_kw(self) -> float:
        return sum(link.optical_power_w for link in self.links) / 1000.0

    @property
    def optical_endpoint_count(self) -> int:
        return len(self.links) * 2


def build_fabric(config: SimulationConfig, architecture: ArchitectureProfile) -> Fabric:
    links: list[Link] = []
    for rack in range(config.racks):
        for spine in range(config.spines):
            for lane in range(config.parallel_links):
                links.append(
                    Link(
                        id=f"r{rack:02d}-s{spine:02d}-l{lane}",
                        rack=rack,
                        spine=spine,
                        lane=lane,
                        capacity_tbps=architecture.link_capacity_tbps,
                        optical_power_w=architecture.link_power_w,
                    )
                )
    return Fabric(config=config, architecture=architecture, links=tuple(links))
