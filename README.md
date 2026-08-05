# ai-factory-optical-twin

A research-flavored digital twin for AI-factory optical interconnects.

It simulates a rack-scale GPU cluster, compares pluggable optics versus a
co-packaged-optics-style profile, injects optical failure modes, runs transparent
telemetry diagnosis, estimates business impact, evaluates mitigation actions, and writes
a static HTML dashboard plus markdown report.

This is not a vendor model and it does not use proprietary data. It is a compact,
inspectable lab for the question that keeps showing up in AI infrastructure:

> When model training becomes a physical-infrastructure business, how do optics,
> reliability, power, and validation time change the economics?

## Research + Money Thesis

**Research question:** how do optical-link health, thermal coupling, and mitigation policy
change end-to-end AI workload throughput in a multi-rack cluster?

**Money question:** AI infrastructure spend increasingly lands in power, networking,
packaging, and supply chain constraints, not only GPUs. Public signals include NVIDIA
positioning co-packaged optics for AI-factory networking and energy efficiency, OpenAI and
Broadcom's 10 GW accelerator/networking collaboration, and optical-transceiver/CPO demand
growth in AI clusters.

**Engineering evidence:** every run produces telemetry, root-cause diagnosis, throughput
impact, optical energy cost, estimated lost GPU-hour cost, mitigation ranking, and a
visual dashboard.

## What It Builds

```text
topology + architecture + workload
          |
          v
 synthetic telemetry stream
          |
          +--> diagnosis.py     -> root cause and affected racks/links
          +--> economics.py     -> power, capex, lost GPU-hour estimate
          +--> mitigation.py    -> rank operational responses
          +--> report.py        -> report.md + dashboard.html
```

## Quickstart

```bash
pip install -r requirements-dev.txt

python -m optical_twin.cli run \
  --architecture cpo \
  --fault fiber_contamination \
  --out reports/demo

python -m optical_twin.cli compare \
  --fault fiber_contamination \
  --out reports/compare

pytest -v
```

Open `reports/demo/dashboard.html` in a browser. It is static HTML; no server is needed.
The comparison command writes `reports/compare/comparison.html`.

## Scenarios

- `none`: nominal operation.
- `fiber_contamination`: receive-power loss and BER rise on one rack's optical paths.
- `laser_aging`: bias-current growth and power margin loss.
- `thermal_coupling`: CPO-like thermal stress affecting a rack group.
- `supply_sag`: bursty BER and temporary capacity loss.

## Architectures

The profiles are illustrative and intentionally parameterized:

- `pluggable`: lower per-port capacity, higher optical power per link.
- `cpo`: higher per-port capacity and lower optical power, but stronger thermal coupling.

Change the numbers in `optical_twin/config.py` to test different assumptions.

## Source Anchors

- NVIDIA describes Spectrum-X Photonics and co-packaged optics as an AI-factory networking
  path for power efficiency and resiliency:
  https://developer.nvidia.com/blog/scaling-ai-factories-with-co-packaged-optics-for-better-power-efficiency/
- OpenAI and Broadcom announced a 10 GW custom accelerator and networking collaboration:
  https://openai.com/index/openai-and-broadcom-announce-strategic-collaboration/
- LightCounting discusses growth in optical connectivity for AI scale-up and scale-out
  networks:
  https://www.lightcounting.com/newsletter/en/july-2025-cloud-data-center-optics-330
- A 2026 arXiv paper on 3D optoelectronics and co-packaged optics frames packaging,
  thermal management, serviceability, and robustness as scaling constraints:
  https://arxiv.org/pdf/2603.21313

## Status

MVP: deterministic topology, simulation, telemetry diagnosis, economics, mitigation
ranking, static HTML dashboard, markdown report, CLI, CI, and network-free tests.

## License

MIT - see [LICENSE](LICENSE).
