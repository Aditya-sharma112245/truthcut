# TruthCut — Autonomous Trailer Director

TruthCut is a replayable prototype that creates three audience-specific trailer edit decision lists from one episode while protecting story truth, spoilers, rights, safety, accessibility, and cultural respect.

The core design is intentionally **Director–Auditor**:

- The **Creative Director** creates a promise and a three-act candidate plan.
- The **Independent Auditor** validates the candidate against typed evidence and hard constraints.
- A bounded repair loop replaces invalid segments.
- A dependency graph supports selective replanning when a contract or subtitle changes.

## Quickstart

```bash
cd truthcut
python -m pip install -e .
PYTHONPATH=src python -m trailer_director.cli run data/package.json --mode replay --out sample_run
PYTHONPATH=src python -m unittest discover -s tests -v
```

After installation, the commands also work without `PYTHONPATH`:

```bash
python -m trailer_director.cli run data/package.json --mode replay --out sample_run
python -m unittest discover -s tests -v
```

The replay path needs no API keys and produces:

```text
sample_run/family_trailer.json
sample_run/young_adult_trailer.json
sample_run/dialect_region_trailer.json
sample_run/validation_report.json
```

## Exercise surprise events

```bash
PYTHONPATH=src python -m trailer_director.cli simulate data/package.json --event music_expiry --out sample_run
PYTHONPATH=src python -m trailer_director.cli simulate data/package.json --event subtitle_mismatch --out sample_run
PYTHONPATH=src python -m trailer_director.cli simulate data/package.json --event model_outage --out sample_run
PYTHONPATH=src python -m trailer_director.cli simulate data/package.json --event prompt_injection --out sample_run
PYTHONPATH=src python -m trailer_director.cli simulate data/package.json --event policy_change --out sample_run
PYTHONPATH=src python -m trailer_director.cli simulate data/package.json --event audience_bias --out sample_run
```

## What makes this different

1. A high-performing spoiler is intentionally proposed for young adults and then rejected.
2. Every segment uses a verified scene interval and dependency list.
3. Rights are checked by territory and expiry, not mentioned only in a final prompt.
4. Dialect personalization uses supplied language evidence and raises semantic review when a relationship can change.
5. Historical performance is treated as a hypothesis, never as a hard objective.
6. Untrusted scene notes cannot override contracts or policies.
7. A contract change triggers targeted replanning rather than a full random rebuild.

## Output status meanings

- `PASS`: all checks pass.
- `PASS_WITH_WARNINGS`: safe to continue, but human/editorial approval remains.
- `REJECTED`: no safe repair was found within the bounded repair budget.
- `HUMAN_REVIEW_REQUIRED`: the system detected a semantic or cultural issue that should not be automated.

## Deliberate scope

This submission focuses on the required machine-readable EDL and verification path. Final video rendering and a large UI are intentionally out of scope. A production implementation would connect the EDL to Premiere, Resolve, or an internal media pipeline after human approval.

See `COMPLIANCE_AUDIT.md` for a requirement-by-requirement audit against the candidate brief.
