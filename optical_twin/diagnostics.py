from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .simulator import SimulationResult, TelemetrySample


@dataclass(frozen=True)
class Diagnosis:
    primary: str
    confidence: float
    affected_racks: tuple[int, ...]
    affected_links: tuple[str, ...]
    evidence: tuple[str, ...]


def diagnose(result: SimulationResult) -> Diagnosis:
    by_link: dict[str, list[TelemetrySample]] = defaultdict(list)
    for sample in result.telemetry:
        by_link[sample.link_id].append(sample)

    link_scores: dict[str, float] = {}
    rack_votes: Counter[int] = Counter()
    evidence: list[str] = []
    weak_power_links = 0
    hot_links = 0
    high_bias_links = 0
    bursty_links = 0

    for link_id, samples in by_link.items():
        first = samples[: max(3, len(samples) // 5)]
        last = samples[-max(3, len(samples) // 5) :]
        rx_drop = _mean(s.rx_power_dbm for s in first) - _mean(s.rx_power_dbm for s in last)
        bias_rise = _mean(s.laser_bias_ma for s in last) - _mean(s.laser_bias_ma for s in first)
        temp_max = max(s.temperature_c for s in samples)
        ber_max = max(s.ber for s in samples)
        fec_total = sum(s.fec_uncorrected for s in samples)
        score = max(0.0, rx_drop) * 0.8 + max(0.0, bias_rise) * 0.08
        score += max(0.0, temp_max - 64.0) * 0.05
        score += 1.5 if ber_max > 1e-9 else 0.0
        score += min(2.0, fec_total / 1500.0)
        if score > 1.4:
            link_scores[link_id] = score
            rack_votes[samples[0].rack] += 1
        if rx_drop > 2.5 and ber_max > 1e-9:
            weak_power_links += 1
        if temp_max > 64.0:
            hot_links += 1
        if bias_rise > 8.0:
            high_bias_links += 1
        if ber_max > 5e-9 and rx_drop < 2.0:
            bursty_links += 1

    affected_links = tuple(
        link_id for link_id, _ in sorted(link_scores.items(), key=lambda item: item[1], reverse=True)[:8]
    )
    affected_racks = tuple(rack for rack, _ in rack_votes.most_common(3))

    if weak_power_links >= 2:
        primary = "fiber_or_connector_contamination"
        confidence = min(0.95, 0.55 + weak_power_links * 0.06)
        evidence.append(f"{weak_power_links} links show receive-power loss with BER growth")
    elif high_bias_links >= 3:
        primary = "laser_aging_or_bias_headroom_loss"
        confidence = min(0.92, 0.52 + high_bias_links * 0.05)
        evidence.append(f"{high_bias_links} links show laser-bias growth")
    elif hot_links >= max(4, len(by_link) // 5):
        primary = "thermal_coupling"
        confidence = min(0.90, 0.50 + hot_links / max(len(by_link), 1))
        evidence.append(f"{hot_links} links exceeded thermal watch limits")
    elif bursty_links >= 4:
        primary = "supply_or_signal_integrity_burst"
        confidence = min(0.86, 0.45 + bursty_links * 0.04)
        evidence.append(f"{bursty_links} links show bursty BER without strong optical-power drift")
    else:
        primary = "nominal"
        confidence = 0.72
        evidence.append("No sustained optical, thermal, or BER signature crossed diagnosis thresholds")

    if affected_racks:
        evidence.append(f"Most affected racks: {', '.join(map(str, affected_racks))}")
    if affected_links:
        evidence.append(f"Top affected links: {', '.join(affected_links[:4])}")

    return Diagnosis(
        primary=primary,
        confidence=round(confidence, 3),
        affected_racks=affected_racks,
        affected_links=affected_links,
        evidence=tuple(evidence),
    )


def _mean(values) -> float:
    items = list(values)
    return sum(items) / len(items)
