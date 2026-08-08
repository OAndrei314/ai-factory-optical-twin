from optical_twin.config import SimulationConfig
from optical_twin.economics import compare_architecture_business_case
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


def test_architecture_business_case_exposes_payback_decision():
    baseline = run_twin("pluggable", "fiber_contamination", sim_config=SimulationConfig(racks=4, steps=90, seed=12))
    candidate = run_twin("cpo", "fiber_contamination", sim_config=SimulationConfig(racks=4, steps=90, seed=12))

    case = compare_architecture_business_case(baseline.economics, candidate.economics, max_payback_days=10_000)

    assert case.baseline_impact_usd_day == baseline.economics.total_impact_usd_day
    assert case.candidate_impact_usd_day == candidate.economics.total_impact_usd_day
    assert case.decision in {"upgrade_candidate", "needs_business_review", "stay_with_baseline"}
