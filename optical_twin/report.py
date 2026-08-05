from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from .diagnostics import Diagnosis
from .economics import EconomicSummary
from .mitigation import MitigationOption
from .pipeline import TwinRun
from .simulator import FleetStep, SimulationResult


def write_artifacts(
    out_dir: str | Path,
    result: SimulationResult,
    diagnosis: Diagnosis,
    economics: EconomicSummary,
    mitigations: tuple[MitigationOption, ...],
) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    telemetry_path = out / "telemetry.csv"
    summary_path = out / "summary.json"
    markdown_path = out / "report.md"
    dashboard_path = out / "dashboard.html"
    _write_telemetry(telemetry_path, result)
    summary_path.write_text(
        json.dumps(_summary_dict(result, diagnosis, economics, mitigations), indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(result, diagnosis, economics, mitigations), encoding="utf-8")
    dashboard_path.write_text(render_html(result, diagnosis, economics, mitigations), encoding="utf-8")
    return {
        "telemetry": telemetry_path,
        "summary": summary_path,
        "markdown": markdown_path,
        "dashboard": dashboard_path,
    }


def write_comparison_artifacts(out_dir: str | Path, runs: tuple[TwinRun, ...]) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "comparison.json"
    markdown_path = out / "comparison.md"
    html_path = out / "comparison.html"
    summary_path.write_text(
        json.dumps(
            [
                _summary_dict(run.result, run.diagnosis, run.economics, run.mitigations)
                for run in runs
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(render_comparison_markdown(runs), encoding="utf-8")
    html_path.write_text(render_comparison_html(runs), encoding="utf-8")
    return {"summary": summary_path, "markdown": markdown_path, "html": html_path}


def render_comparison_markdown(runs: tuple[TwinRun, ...]) -> str:
    lines = [
        "# Architecture Comparison",
        "",
        "| architecture | fault | throughput | optical kW | energy/day | capex | modeled impact/day | top mitigation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in runs:
        lines.append(
            f"| {run.result.fabric.architecture.name} | {run.result.fault} | "
            f"{run.result.average_throughput_index:.3f} | "
            f"{run.result.fabric.optical_power_kw:.3f} | "
            f"${run.economics.optical_energy_cost_usd_day:,.2f} | "
            f"${run.economics.estimated_optics_capex_usd:,.0f} | "
            f"${run.economics.total_impact_usd_day:,.2f} | "
            f"{run.mitigations[0].name} |"
        )
    lines.extend(
        [
            "",
            "The comparison is deliberately synthetic. It is meant to expose the",
            "trade-off surface: optical power, capacity headroom, thermal coupling,",
            "failure diagnosis, and operational response value.",
            "",
        ]
    )
    return "\n".join(lines)


def render_comparison_html(runs: tuple[TwinRun, ...]) -> str:
    bars = _comparison_bars(runs)
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(run.result.fabric.architecture.name)}</td>"
        f"<td>{run.result.average_throughput_index:.3f}</td>"
        f"<td>{run.result.fabric.optical_power_kw:.3f} kW</td>"
        f"<td>${run.economics.estimated_optics_capex_usd:,.0f}</td>"
        f"<td>${run.economics.total_impact_usd_day:,.0f}/day</td>"
        f"<td>{html.escape(run.diagnosis.primary)}</td>"
        f"<td>{html.escape(run.mitigations[0].name)}</td>"
        "</tr>"
        for run in runs
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Optical Architecture Comparison</title>
  <style>
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #172026; background: #f5f7f2; }}
    header {{ padding: 34px clamp(18px, 4vw, 52px); background: #fff; border-bottom: 1px solid #d8e1e7; }}
    main {{ padding: 24px clamp(18px, 4vw, 52px) 42px; display: grid; gap: 16px; }}
    section {{ background: #fff; border: 1px solid #d8e1e7; border-radius: 8px; padding: 18px; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(28px, 4vw, 46px); letter-spacing: 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #d8e1e7; text-align: left; }}
    th {{ color: #5d6b74; }}
    svg {{ width: 100%; height: auto; display: block; }}
  </style>
</head>
<body>
  <header>
    <h1>Optical Architecture Comparison</h1>
    <p>Same workload and fault, different optical architecture assumptions.</p>
  </header>
  <main>
    <section>{bars}</section>
    <section>
      <table>
        <tr><th>Architecture</th><th>Throughput</th><th>Optical power</th><th>Capex</th><th>Impact</th><th>Diagnosis</th><th>Top mitigation</th></tr>
        {rows}
      </table>
    </section>
  </main>
</body>
</html>
"""


def render_markdown(
    result: SimulationResult,
    diagnosis: Diagnosis,
    economics: EconomicSummary,
    mitigations: tuple[MitigationOption, ...],
) -> str:
    best = mitigations[0]
    lines = [
        "# AI Factory Optical Twin Report",
        "",
        "## Scenario",
        "",
        f"- Architecture: `{result.fabric.architecture.name}`",
        f"- Fault: `{result.fault}`",
        f"- GPUs: {result.fabric.config.gpu_count}",
        f"- Optical endpoints: {result.fabric.optical_endpoint_count}",
        f"- Average throughput index: {result.average_throughput_index:.3f}",
        f"- Worst step time: {result.worst_step_time_ms:.1f} ms",
        "",
        "## Diagnosis",
        "",
        f"- Primary: `{diagnosis.primary}`",
        f"- Confidence: {diagnosis.confidence:.1%}",
        f"- Affected racks: {', '.join(map(str, diagnosis.affected_racks)) or 'none'}",
        f"- Affected links: {', '.join(diagnosis.affected_links) or 'none'}",
        "",
        "Evidence:",
    ]
    lines.extend(f"- {item}" for item in diagnosis.evidence)
    lines.extend(
        [
            "",
            "## Economics",
            "",
            f"- Optical energy: {economics.optical_energy_kwh_day:.2f} kWh/day",
            f"- Optical energy cost: ${economics.optical_energy_cost_usd_day:,.2f}/day",
            f"- Estimated optics capex: ${economics.estimated_optics_capex_usd:,.0f}",
            f"- Lost GPU-hours: {economics.lost_gpu_hours_day:,.2f}/day",
            f"- Lost compute cost: ${economics.lost_compute_usd_day:,.2f}/day",
            f"- Downtime risk: ${economics.downtime_risk_usd_day:,.2f}/day",
            f"- Total modeled impact: ${economics.total_impact_usd_day:,.2f}/day",
            "",
            "## Mitigation Ranking",
            "",
            "| action | throughput index | avoided loss/day | action cost | net value/day |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for option in mitigations:
        lines.append(
            f"| {option.name} | {option.expected_throughput_index:.3f} | "
            f"${option.avoided_loss_usd_day:,.2f} | ${option.action_cost_usd:,.2f} | "
            f"${option.net_value_usd_day:,.2f} |"
        )
    lines.extend(
        [
            "",
            f"Recommended first move: **{best.name}**.",
            "",
            best.rationale,
            "",
        ]
    )
    return "\n".join(lines)


def render_html(
    result: SimulationResult,
    diagnosis: Diagnosis,
    economics: EconomicSummary,
    mitigations: tuple[MitigationOption, ...],
) -> str:
    sparkline = _sparkline(result.fleet, width=720, height=130)
    topology = _topology_svg(result, diagnosis, width=720, height=260)
    mitigation_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(option.name)}</td>"
        f"<td>{option.expected_throughput_index:.3f}</td>"
        f"<td>${option.avoided_loss_usd_day:,.0f}</td>"
        f"<td>${option.action_cost_usd:,.0f}</td>"
        f"<td>${option.net_value_usd_day:,.0f}</td>"
        "</tr>"
        for option in mitigations
    )
    evidence = "".join(f"<li>{html.escape(item)}</li>" for item in diagnosis.evidence)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Factory Optical Twin</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5d6b74;
      --line: #d8e1e7;
      --panel: #ffffff;
      --bg: #f5f7f2;
      --green: #16825d;
      --amber: #b56a00;
      --red: #b42318;
      --blue: #2764b4;
      --teal: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      padding: 34px clamp(18px, 4vw, 52px) 22px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    h1 {{ margin: 0 0 8px; font-size: clamp(28px, 4vw, 48px); letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    p {{ line-height: 1.55; }}
    main {{ padding: 24px clamp(18px, 4vw, 52px) 42px; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 1px 2px rgba(23, 32, 38, 0.05);
    }}
    .wide {{ grid-column: span 2; }}
    .full {{ grid-column: 1 / -1; }}
    .metric {{ color: var(--muted); font-size: 13px; text-transform: uppercase; }}
    .value {{ font-size: 28px; font-weight: 740; margin-top: 6px; }}
    .good {{ color: var(--green); }}
    .warn {{ color: var(--amber); }}
    .bad {{ color: var(--red); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ color: var(--muted); font-weight: 650; }}
    svg {{ width: 100%; height: auto; display: block; }}
    ul {{ margin: 0; padding-left: 18px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} .wide {{ grid-column: auto; }} }}
  </style>
</head>
<body>
  <header>
    <h1>AI Factory Optical Twin</h1>
    <p>Architecture <strong>{html.escape(result.fabric.architecture.name)}</strong>,
    fault <strong>{html.escape(result.fault)}</strong>, {result.fabric.config.gpu_count} GPUs,
    {result.fabric.optical_endpoint_count} optical endpoints.</p>
  </header>
  <main class="grid">
    <section class="panel"><div class="metric">Throughput Index</div><div class="value {_status_class(result.average_throughput_index)}">{result.average_throughput_index:.3f}</div></section>
    <section class="panel"><div class="metric">Worst Step</div><div class="value">{result.worst_step_time_ms:.0f} ms</div></section>
    <section class="panel"><div class="metric">Root Cause</div><div class="value">{html.escape(diagnosis.primary)}</div></section>
    <section class="panel"><div class="metric">Modeled Impact</div><div class="value bad">${economics.total_impact_usd_day:,.0f}/day</div></section>
    <section class="panel wide"><h2>Training Throughput Timeline</h2>{sparkline}</section>
    <section class="panel wide"><h2>Optical Fabric Health</h2>{topology}</section>
    <section class="panel wide"><h2>Diagnosis Evidence</h2><ul>{evidence}</ul></section>
    <section class="panel wide"><h2>Economics</h2>
      <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Optical energy</td><td>{economics.optical_energy_kwh_day:.2f} kWh/day</td></tr>
        <tr><td>Optical energy cost</td><td>${economics.optical_energy_cost_usd_day:,.2f}/day</td></tr>
        <tr><td>Estimated optics capex</td><td>${economics.estimated_optics_capex_usd:,.0f}</td></tr>
        <tr><td>Lost GPU-hours</td><td>{economics.lost_gpu_hours_day:,.2f}/day</td></tr>
        <tr><td>Lost compute cost</td><td>${economics.lost_compute_usd_day:,.2f}/day</td></tr>
      </table>
    </section>
    <section class="panel full"><h2>Mitigation Ranking</h2>
      <table>
        <tr><th>Action</th><th>Expected throughput</th><th>Avoided loss/day</th><th>Action cost</th><th>Net/day</th></tr>
        {mitigation_rows}
      </table>
    </section>
  </main>
</body>
</html>
"""


def _write_telemetry(path: Path, result: SimulationResult) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "step",
                "link_id",
                "rack",
                "spine",
                "rx_power_dbm",
                "laser_bias_ma",
                "temperature_c",
                "ber",
                "utilization",
                "fec_uncorrected",
                "link_up",
            ]
        )
        for sample in result.telemetry:
            writer.writerow(
                [
                    sample.step,
                    sample.link_id,
                    sample.rack,
                    sample.spine,
                    sample.rx_power_dbm,
                    sample.laser_bias_ma,
                    sample.temperature_c,
                    f"{sample.ber:.4e}",
                    sample.utilization,
                    sample.fec_uncorrected,
                    sample.link_up,
                ]
            )


def _summary_dict(
    result: SimulationResult,
    diagnosis: Diagnosis,
    economics: EconomicSummary,
    mitigations: tuple[MitigationOption, ...],
) -> dict[str, object]:
    return {
        "architecture": result.fabric.architecture.name,
        "fault": result.fault,
        "gpu_count": result.fabric.config.gpu_count,
        "throughput_index": round(result.average_throughput_index, 4),
        "diagnosis": diagnosis.__dict__,
        "economics": economics.__dict__,
        "mitigations": [option.__dict__ for option in mitigations],
    }


def _sparkline(fleet: tuple[FleetStep, ...], width: int, height: int) -> str:
    values = [step.throughput_index for step in fleet]
    lo = min(values)
    hi = max(values)
    span = hi - lo or 1.0
    points = []
    for i, value in enumerate(values):
        x = i * width / max(1, len(values) - 1)
        y = height - ((value - lo) / span) * (height - 18) - 9
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="throughput timeline">'
        f'<polyline fill="none" stroke="#2764b4" stroke-width="3" points="{" ".join(points)}"/>'
        f'<line x1="0" y1="{height-10}" x2="{width}" y2="{height-10}" stroke="#d8e1e7"/>'
        f'<text x="4" y="16" font-size="13" fill="#5d6b74">max {hi:.3f}</text>'
        f'<text x="4" y="{height-16}" font-size="13" fill="#5d6b74">min {lo:.3f}</text>'
        "</svg>"
    )


def _topology_svg(result: SimulationResult, diagnosis: Diagnosis, width: int, height: int) -> str:
    affected = set(diagnosis.affected_links)
    rack_x = 90
    spine_x = width - 90
    rack_gap = height / (result.fabric.config.racks + 1)
    spine_gap = height / (result.fabric.config.spines + 1)
    lines = []
    for link in result.fabric.links:
        y1 = (link.rack + 1) * rack_gap
        y2 = (link.spine + 1) * spine_gap
        color = "#b42318" if link.id in affected else "#16825d"
        opacity = "0.95" if link.id in affected else "0.20"
        lines.append(
            f'<line x1="{rack_x}" y1="{y1:.1f}" x2="{spine_x}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="2" opacity="{opacity}"/>'
        )
    nodes = []
    for rack in range(result.fabric.config.racks):
        y = (rack + 1) * rack_gap
        color = "#b42318" if rack in diagnosis.affected_racks else "#2764b4"
        nodes.append(f'<circle cx="{rack_x}" cy="{y:.1f}" r="10" fill="{color}"/>')
        nodes.append(f'<text x="{rack_x - 50}" y="{y + 4:.1f}" font-size="12" fill="#172026">rack {rack}</text>')
    for spine in range(result.fabric.config.spines):
        y = (spine + 1) * spine_gap
        nodes.append(f'<rect x="{spine_x - 10}" y="{y - 10:.1f}" width="20" height="20" rx="4" fill="#0f766e"/>')
        nodes.append(f'<text x="{spine_x + 18}" y="{y + 4:.1f}" font-size="12" fill="#172026">spine {spine}</text>')
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="fabric health">{"".join(lines + nodes)}</svg>'


def _status_class(value: float) -> str:
    if value >= 0.94:
        return "good"
    if value >= 0.84:
        return "warn"
    return "bad"


def _comparison_bars(runs: tuple[TwinRun, ...]) -> str:
    width = 780
    row_h = 58
    height = 30 + row_h * len(runs)
    max_impact = max(run.economics.total_impact_usd_day for run in runs) or 1.0
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="architecture comparison">']
    parts.append('<text x="0" y="18" font-size="14" fill="#5d6b74">Throughput index and modeled impact per day</text>')
    for i, run in enumerate(runs):
        y = 42 + i * row_h
        throughput_w = run.result.average_throughput_index * 260
        impact_w = (run.economics.total_impact_usd_day / max_impact) * 260
        parts.append(f'<text x="0" y="{y + 15}" font-size="14" fill="#172026">{html.escape(run.result.fabric.architecture.name)}</text>')
        parts.append(f'<rect x="150" y="{y}" width="{throughput_w:.1f}" height="16" rx="4" fill="#16825d"/>')
        parts.append(f'<text x="420" y="{y + 13}" font-size="13" fill="#172026">{run.result.average_throughput_index:.3f}</text>')
        parts.append(f'<rect x="500" y="{y}" width="{impact_w:.1f}" height="16" rx="4" fill="#b42318"/>')
        parts.append(f'<text x="500" y="{y + 36}" font-size="13" fill="#5d6b74">${run.economics.total_impact_usd_day:,.0f}/day</text>')
    parts.append("</svg>")
    return "".join(parts)
