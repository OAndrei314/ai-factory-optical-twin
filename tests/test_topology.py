from optical_twin.config import ARCHITECTURES, SimulationConfig
from optical_twin.topology import build_fabric


def test_fabric_counts_capacity_and_endpoints():
    fabric = build_fabric(SimulationConfig(racks=4, spines=2, parallel_links=2), ARCHITECTURES["cpo"])

    assert len(fabric.links) == 16
    assert fabric.optical_endpoint_count == 32
    assert fabric.total_capacity_tbps == 16 * 1.6
    assert fabric.optical_power_kw > 0
