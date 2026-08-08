from pathlib import Path

from optical_twin.cli import main
from optical_twin.config import SimulationConfig
from optical_twin.pipeline import run_twin
from optical_twin.report import (
    render_comparison_html,
    render_comparison_markdown,
    render_html,
    render_matrix_html,
    render_matrix_markdown,
    render_markdown,
    write_artifacts,
    write_comparison_artifacts,
    write_matrix_artifacts,
)


def test_report_contains_dashboard_sections(tmp_path):
    run = run_twin("cpo", "laser_aging", sim_config=SimulationConfig(racks=4, steps=80, seed=9))

    markdown = render_markdown(run.result, run.diagnosis, run.economics, run.mitigations)
    html = render_html(run.result, run.diagnosis, run.economics, run.mitigations)

    assert "Mitigation Ranking" in markdown
    assert "AI Factory Optical Twin" in html
    assert "<svg" in html


def test_write_artifacts_and_cli(tmp_path):
    out = tmp_path / "demo"

    code = main(["run", "--architecture", "cpo", "--fault", "fiber_contamination", "--out", str(out), "--steps", "60", "--racks", "4"])

    assert code == 0
    assert (out / "telemetry.csv").exists()
    assert (out / "summary.json").exists()
    assert (out / "report.md").exists()
    assert (out / "dashboard.html").exists()

    run = run_twin("pluggable", "none", sim_config=SimulationConfig(racks=4, steps=30, seed=3))
    paths = write_artifacts(tmp_path / "nominal", run.result, run.diagnosis, run.economics, run.mitigations)
    assert Path(paths["dashboard"]).read_text(encoding="utf-8").startswith("<!doctype html>")


def test_comparison_report_and_cli(tmp_path):
    runs = (
        run_twin("cpo", "fiber_contamination", sim_config=SimulationConfig(racks=4, steps=40, seed=1)),
        run_twin("pluggable", "fiber_contamination", sim_config=SimulationConfig(racks=4, steps=40, seed=1)),
    )

    markdown = render_comparison_markdown(runs)
    html = render_comparison_html(runs)
    paths = write_comparison_artifacts(tmp_path / "compare", runs)
    code = main(["compare", "--fault", "fiber_contamination", "--out", str(tmp_path / "cli-compare"), "--steps", "40", "--racks", "4"])

    assert "Architecture Comparison" in markdown
    assert "<svg" in html
    assert paths["html"].exists()
    assert code == 0


def test_matrix_report_and_cli(tmp_path):
    runs = tuple(
        run_twin(architecture, fault, sim_config=SimulationConfig(racks=4, steps=30, seed=2))
        for architecture in ("cpo", "pluggable")
        for fault in ("none", "thermal_coupling")
    )

    markdown = render_matrix_markdown(runs)
    html = render_matrix_html(runs)
    paths = write_matrix_artifacts(tmp_path / "matrix", runs)
    code = main(["matrix", "--out", str(tmp_path / "cli-matrix"), "--steps", "24", "--racks", "4"])

    assert "Scenario Matrix" in markdown
    assert "Highest Modeled Exposures" in markdown
    assert "validation gap" in markdown
    assert "<svg" in html
    assert paths["summary"].exists()
    assert paths["markdown"].exists()
    assert paths["html"].exists()
    assert code == 0
