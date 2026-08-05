from optical_twin.config import SimulationConfig
from optical_twin.pipeline import run_twin


def test_economics_and_mitigations_have_money_metrics():
    run = run_twin(
        "cpo",
        "fiber_contamination",
        sim_config=SimulationConfig(racks=4, steps=90, seed=12),
    )

    assert run.economics.estimated_optics_capex_usd > 0
    assert run.economics.total_impact_usd_day >= run.economics.optical_energy_cost_usd_day
    assert run.mitigations[0].net_value_usd_day >= run.mitigations[-1].net_value_usd_day
    assert any(option.name == "clean_or_replace_optical_path" for option in run.mitigations)
