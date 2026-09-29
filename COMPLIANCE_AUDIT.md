# TruthCut Compliance Audit

## Verdict

TruthCut now follows the brief strongly at the prototype and replay-engine level. It is **not literally 100% media-production complete** because the current submission uses a verified episode manifest and deterministic replay fixture instead of performing live frame/audio analysis, and it does not generate voice-over audio. Those are intentional scope tradeoffs, but they should be stated in the interview.

## Requirement status

| Requirement | Status | Evidence or remaining limitation |
|---|---|---|
| Three audience-specific plans | Full | `family_trailer.json`, `young_adult_trailer.json`, `dialect_region_trailer.json` are distinct and verified. |
| Story map | Full | `sample_run/story_map.json` contains characters, relationships, facts, protected reveal, and scene links. |
| Constraint map | Full | `sample_run/constraint_map.json` lists trusted inputs, untrusted evidence, validators, and statuses. |
| Audience promise before clip choice | Full | Each plan has `objective`, `audience_promise`, and `emotional_journey`. |
| Exact source timecodes | Full in replay mode | Intervals use `HH:MM:SS.mmm` and are checked against the canonical manifest; live media frame verification remains a future adapter. |
| Scene, dialogue, subtitle, text card, music, and transition choices | Full for EDL | EDL segments contain all fields. Voice-over is explicitly `null` because no generated voice-over is needed for this fixture. |
| Story truth and clickbait rejection | Full | Claims are checked against story evidence; an unsupported claim test is included. |
| Spoiler protection | Full | Protected fact graph, deterministic reveal check, repair, and high-performing spoiler test. |
| Rights and territories | Full for structured fixture | Actor and music contracts, allowed use, territory, expiry, promotional approval, and repair are checked. |
| Rating and family safety | Full for fixture | Audience policies and forbidden content flags are enforced. |
| Cultural respect and dialect handling | Mostly full | Dialect plan, structural differentiation, relationship-drift warning, and human review are implemented. A production system still needs expert/community review. |
| Accessibility | Partial | Subtitle-track presence and declared subtitle usage are checked. Full rendered caption readability, contrast, and audio-description inspection require real media/rendering. |
| Budget and fallback | Full for replay design | Estimated cost, budget failure, replay mode, and fallback plan are exposed. |
| Historical performance as hypothesis | Full | Historic data is never a hard objective; bias signals are quarantined and logged. |
| Contract change replanning | Full | Dependency-based delta replanning changes only affected plans and records versions/diffs. |
| Policy change response | Full for fixture | `simulate --event policy_change` revalidates only the affected family plan. |
| Audience-bias change response | Full for fixture | `simulate --event audience_bias` quarantines the signal and preserves evidence-based decisions. |
| Missing scene/model hallucination | Full | Grounding validator rejects unknown or out-of-bounds scene references; test included. |
| Prompt injection defense | Full | Untrusted scene text cannot override structured contracts or policies; simulation and test included. |
| Model unavailable fallback | Full | Replay fallback event and test included. |
| Decision logs and observability | Full | Plans include structured decision logs, dependencies, evidence, warnings, versions, and repair events. |
| Required repository files | Full | README, architecture, AI collaboration, limitations, source, tests, sample run, story map, spoiler map, constraint map, plans, and validation report are present. |
| Runnable CLI/API | Full | CLI supports `run`, `simulate`, and `report`, accepts optional audience definitions, and works after `python -m pip install -e .`. |
| Automated tests | Full and expanded | 16 tests cover required failures plus budget, prompt injection, dialect, clickbait, bias, fallback, dynamic IDs, renamed music expiry, empty plans, and fixture isolation. |
| Dynamic surprise events | Full for replay fixture | Music expiry discovers the used music asset dynamically; normal validation also quarantines instruction-like text in untrusted evidence. |

## Final pre-submission command

```bash
cd truthcut
PYTHONPATH=src python -m trailer_director.cli run data/package.json --mode replay --out sample_run
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m trailer_director.cli report sample_run --output sample_run/edl_inspector.html
```

## Interview disclosure

Say this clearly:

> “The submission intentionally prioritizes a reproducible, auditable EDL and independent validation over pretending that a coarse video model is a source of truth. The replay manifest proves the decision and recovery logic. In production, the manifest would be populated by shot detection, transcript alignment, OCR, audio analysis, and targeted high-resolution multimodal verification.”
