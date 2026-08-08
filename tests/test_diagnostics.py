from optical_twin.config import SimulationConfig
from optical_twin.pipeline import run_twin


def test_diagnosis_finds_fiber_contamination():
    run = run_twin(
        "cpo",
        "fiber_contamination",
        sim_config=SimulationConfig(racks=4, steps=90, seed=4),
    )

    assert run.diagnosis.primary == "fiber_or_connector_contamination"
    assert run.diagnosis.confidence >= 0.6
    assert run.diagnosis.affected_links


def test_nominal_stays_nominal():
    run = run_twin("pluggable", "none", sim_config=SimulationConfig(racks=4, steps=70, seed=4))

    assert run.diagnosis.primary == "nominal"
    assert run.result.max_degraded_links == 0
