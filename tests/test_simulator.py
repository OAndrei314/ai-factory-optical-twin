from optical_twin.config import ARCHITECTURES, SimulationConfig, WorkloadConfig
from optical_twin.simulator import simulate_fabric
from optical_twin.topology import build_fabric


def test_simulation_is_deterministic_for_same_seed():
    config = SimulationConfig(racks=4, steps=30, seed=11)
    fabric = build_fabric(config, ARCHITECTURES["pluggable"])

    a = simulate_fabric(fabric, WorkloadConfig(), fault="fiber_contamination", seed=11)
    b = simulate_fabric(fabric, WorkloadConfig(), fault="fiber_contamination", seed=11)

    assert a.telemetry[:20] == b.telemetry[:20]
    assert a.fleet == b.fleet


def test_fault_degrades_throughput_relative_to_nominal():
    config = SimulationConfig(racks=4, steps=80, seed=5)
    fabric = build_fabric(config, ARCHITECTURES["cpo"])

    nominal = simulate_fabric(fabric, WorkloadConfig(), fault="none", seed=5)
    degraded = simulate_fabric(fabric, WorkloadConfig(), fault="fiber_contamination", seed=5)

    assert degraded.average_throughput_index < nominal.average_throughput_index
    assert degraded.max_degraded_links > 0
