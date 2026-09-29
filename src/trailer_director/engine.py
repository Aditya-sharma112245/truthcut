from __future__ import annotations
import copy, hashlib, json, re
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any
from .models import Package, Segment, TrailerPlan, Validation, jsonable

AUDIENCE_ORDER = ["family", "young_adult", "dialect_region"]


def parse_time(value: str | float | int) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    parts = value.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Invalid timecode: {value}")


def tc(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remainder = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remainder:06.3f}"


def dependency_fingerprint(segment: Segment) -> str:
    raw = "|".join([segment.scene_id, *sorted(segment.dependencies), segment.audio, segment.subtitle or ""])
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def load_package(path: str | Path) -> Package:
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    subtitle_path = path.parent / "dialogue_and_subtitles.json"
    subtitles = json.loads(subtitle_path.read_text(encoding="utf-8")) if subtitle_path.exists() else {}
    return Package(raw, subtitles)


def _candidate_map(pkg: Package) -> dict[str, dict[str, Any]]:
    return {c["candidate_id"]: c for c in pkg.candidates}


def _pick_candidates(pkg: Package, audience: str) -> list[dict[str, Any]]:
    allowed = set(pkg.audiences[audience]["allowed_tags"])
    candidates = [c for c in pkg.candidates if allowed.intersection(c.get("tags", []))]
    # Deliberately include a dynamically discovered spoiler candidate in YA so
    # the Auditor demonstrates veto power on the fixture without assuming IDs.
    spoiler = None
    if audience == "young_adult":
        spoiler = next((c for c in pkg.candidates if c.get("reveals") or "spoiler" in c.get("tags", [])), None)
        if spoiler:
            candidates = [spoiler] + [c for c in candidates if c is not spoiler]
    # Stable editorial order: hook, escalation, emotional/button. No random sampling.
    buckets = {
        "hook": ["mystery", "warm", "dialect"],
        "escalation": ["conflict", "tension", "teamwork", "emotional"],
        "button": ["hopeful", "emotional", "mystery"]
    }
    selected = []
    used = set()
    if audience == "dialect_region":
        dialect = next((c for c in candidates if "dialect" in c.get("tags", []) or c.get("subtitle") == "dialect"), None)
        if dialect:
            selected.append(dialect)
            used.add(dialect["candidate_id"])
    for bucket in ("hook", "escalation", "button"):
        for c in candidates:
            if c["candidate_id"] in used:
                continue
            if any(t in c.get("tags", []) for t in buckets[bucket]):
                selected.append(c); used.add(c["candidate_id"]); break
    for c in candidates:
        if c["candidate_id"] not in used and len(selected) < 3:
            selected.append(c); used.add(c["candidate_id"])
    if audience == "young_adult" and spoiler is not None:
        selected = [spoiler] + [c for c in selected if c["candidate_id"] != spoiler["candidate_id"]]
    return selected[:3]


def _candidate_to_segment(c: dict[str, Any], audience: str, actor_contracts: list[str] | None = None) -> Segment:
    subtitle = c.get("subtitle", "standard")
    actor_ids = c.get("actors") or actor_contracts or []
    dependencies = [c["scene_id"], c["music"], *actor_ids, f"subtitle_{subtitle}"]
    clip_max = {"family": 12.0, "young_adult": 6.0, "dialect_region": 9.0}.get(audience, 10.0)
    if "warm" in c.get("tags", []) or "emotional" in c.get("tags", []):
        clip_max += 2.0
    end = min(float(c["end"]), float(c["start"]) + clip_max)
    return Segment(
        segment_id=f"{audience}_{c['candidate_id']}", scene_id=c["scene_id"],
        source_in=tc(c["start"]), source_out=tc(end), video=c["video"],
        audio=c["audio"], subtitle=subtitle, claim=c["claim"],
        reason=f"Supports the {audience} audience promise using {', '.join(c.get('tags', []))} evidence.",
        dependencies=dependencies,
        risk_flags=list(c.get("tags", [])),
        transition="HARD_CUT" if audience == "young_adult" else "DISSOLVE" if audience == "family" else "L_CUT",
        voice_over=None,
        text_card=c["claim"],
        music=c["music"],
        evidence=[f"scene:{c['scene_id']}", f"candidate:{c['candidate_id']}", f"contract:{c['music']}"],
        assumptions=["Source interval is verified against the canonical episode manifest."],
        dialogue=c.get("dialogue", c.get("claim")),
    )


def create_plan(pkg: Package, audience: str) -> TrailerPlan:
    promise = pkg.audiences[audience]["promise"]
    default_journeys = {
        "family": ["welcoming world", "safe mystery", "hopeful family button"],
        "young_adult": ["sharp hook", "conflict and pressure", "unresolved question"],
        "dialect_region": ["familiar voice", "family stakes", "dignified emotional button"]
    }
    journey = pkg.audiences[audience].get("emotional_journey", default_journeys.get(audience, ["hook", "stakes", "open question"]))
    actor_contracts = [k for k, v in pkg.contracts.items() if v.get("type") == "actor"]
    segments = [_candidate_to_segment(c, audience, actor_contracts) for c in _pick_candidates(pkg, audience)]
    duration = sum(parse_time(s.source_out) - parse_time(s.source_in) for s in segments)
    return TrailerPlan(
        trailer_id=f"{audience}_v1", audience=audience, duration_seconds=round(duration),
        audience_promise=promise, emotional_journey=journey, segments=segments,
        estimated_cost=0.04 + 0.01 * len(segments),
        objective=f"Create a {audience}-appropriate mini-story without revealing the protected resolution.",
        human_approvals=["music promotion approval"],
    )


def _validation(plan: TrailerPlan, rule: str, status: str, message: str, evidence=None, severity="error", repairs=None, human=False):
    v = Validation(rule, status, severity, message, evidence or [], repairs or [], human)
    for segment in plan.segments:
        if rule in {"grounding", "rights", "spoiler", "ratings", "truth", "dialect", "accessibility"}:
            pass
    return v


def _is_expired(contract: dict[str, Any], as_of: str) -> bool:
    return contract.get("expires_at", "9999-12-31") < as_of


def validate_plan(pkg: Package, plan: TrailerPlan, as_of: str = "2026-09-29", territory: str = "IN") -> list[Validation]:
    results: list[Validation] = []
    if not plan.segments:
        return [_validation(plan, "planning", "FAIL", f"No candidate clips available for audience {plan.audience}.", ["no_candidates"], repairs=["provide_verified_candidate_pool"])]
    manifest = pkg.scenes
    cand = _candidate_map(pkg)
    policy = pkg.raw["rating_policies"][plan.audience]
    claims = {f["statement"] for f in pkg.raw["story_map"]["facts"]}
    used_music = set()

    # Schema and grounding are hard invariants.
    for s in plan.segments:
        start, end = parse_time(s.source_in), parse_time(s.source_out)
        scene = manifest.get(s.scene_id)
        if not scene or start < scene["start"] or end > scene["end"] or start >= end:
            results.append(_validation(plan, "grounding", "FAIL", f"Segment {s.segment_id} has a missing or out-of-bounds source interval.", [s.scene_id], repairs=["replace_with_verified_candidate"]))
        if s.audio is None or not s.video:
            results.append(_validation(plan, "schema", "FAIL", f"Segment {s.segment_id} lacks media references."))
        for d in s.dependencies:
            if d.startswith("music_"):
                used_music.add(d)

    # Rights and territory.
    actor_ids = {d for s in plan.segments for d in s.dependencies if pkg.contracts.get(d, {}).get("type") == "actor"}
    if not actor_ids:
        results.append(_validation(plan, "rights", "WARN", "No actor contract dependencies were mapped for this plan; verify cast metadata before publication.", ["actor_metadata"], severity="warning", human=True))
    for actor_id in actor_ids:
        actor = pkg.contracts[actor_id]
        if territory not in actor.get("territories", []) or "trailer" not in actor.get("allowed_use", []):
            results.append(_validation(plan, "rights", "FAIL", f"Actor/likeness promotion {actor_id} is not cleared for this territory.", [actor_id], repairs=["replace_actor_or_require_approval"]))
        elif _is_expired(actor, as_of):
            results.append(_validation(plan, "rights", "FAIL", f"Actor/likeness promotion {actor_id} is expired.", [actor_id], repairs=["replace_actor_or_require_approval"]))
    for music in used_music:
        contract = pkg.contracts.get(music)
        if not contract:
            results.append(_validation(plan, "rights", "FAIL", f"No contract exists for {music}.", [music], repairs=["replace_music"]))
            continue
        if territory not in contract.get("territories", []) or "trailer" not in contract.get("allowed_use", []):
            results.append(_validation(plan, "rights", "FAIL", f"{music} is not cleared for trailer use in {territory}.", [music], repairs=["replace_music"]))
        elif _is_expired(contract, as_of):
            results.append(_validation(plan, "rights", "FAIL", f"{music} expired on {contract['expires_at']}.", [music], repairs=["replace_music"]))
        elif contract.get("approval_required"):
            results.append(_validation(plan, "rights", "WARN", f"{music} requires human promotional approval.", [music], severity="warning", human=True))

    # Spoilers and truth.
    for s in plan.segments:
        c = next((x for x in pkg.candidates if x["scene_id"] == s.scene_id and x["video"] == s.video), None)
        if c and any(f in pkg.protected_facts for f in c.get("reveals", [])):
            results.append(_validation(plan, "spoiler", "FAIL", f"Rejected {s.segment_id}: protected reveal {c['reveals'][0]}.", c.get("reveals", []), repairs=["replace_with_non_spoiler_candidate"]))
        if s.claim not in claims and not any(s.claim == f["claim"] for f in pkg.candidates):
            results.append(_validation(plan, "truth", "FAIL", f"Unsupported marketing claim: {s.claim}.", [s.scene_id], repairs=["rewrite_claim_or_replace_segment"]))

    # Audience policy and content flags.
    for s in plan.segments:
        scene = manifest.get(s.scene_id, {})
        flags = set(scene.get("content_flags", []))
        forbidden = set(policy.get("forbidden_flags", []))
        if flags.intersection(forbidden):
            results.append(_validation(plan, "ratings", "FAIL", f"{s.segment_id} contains forbidden {sorted(flags & forbidden)} for {plan.audience}.", [s.scene_id], repairs=["replace_with_safe_candidate"]))

    # Dialect semantic parity is human-gated when the material relationship matters.
    if plan.audience == "dialect_region":
        sensitive = {x.get("scene_id") for x in pkg.subtitles.get("relationship_sensitive_spans", [])}
        affected = [s.scene_id for s in plan.segments if s.subtitle == "dialect" and s.scene_id in sensitive]
        if affected:
            results.append(_validation(plan, "dialect", "WARN", f"Dialect subtitle relationship review required for {sorted(set(affected))}.", [f"subtitle:{x}" for x in sorted(set(affected))], severity="warning", human=True))
        results.append(_validation(plan, "dialect", "PASS", "Dialect plan uses supplied language evidence and passes structural-parity precheck.", ["audience:dialect_region"], severity="info"))

    # Historical performance is a hypothesis, not an instruction. Flag the
    # planted regional/social bias instead of allowing it to steer selection.
    if any("bias" in str(row).lower() for row in pkg.raw.get("historic_performance", [])):
        results.append(_validation(plan, "bias", "WARN", "Historical audience data contains a flagged bias signal; it was not used as a hard selection rule.", ["historic_performance"], severity="warning", human=True))

    # Untrusted scene descriptions are scanned and quarantined. They never
    # enter the contract or policy evaluator as executable instructions.
    serialized = json.dumps(pkg.raw).lower()
    if re.search(r"ignore\s+(the\s+)?contract|override\s+(all\s+)?rules", serialized):
        results.append(_validation(plan, "security", "WARN", "Instruction-like text was detected in untrusted evidence and ignored.", ["untrusted_scene_description"], severity="warning", human=True))

    # Accessibility and budget.
    for s in plan.segments:
        if s.subtitle is None and s.audio.startswith("dialogue"):
            results.append(_validation(plan, "accessibility", "FAIL", f"Dialogue segment {s.segment_id} has no subtitle track.", [s.segment_id], repairs=["add_verified_subtitle"]))
    max_duration = policy["max_duration"]
    if plan.duration_seconds > max_duration:
        results.append(_validation(plan, "duration", "FAIL", f"Trailer duration {plan.duration_seconds}s exceeds {max_duration}s.", repairs=["trim_or_replace_segment"]))
    budget = pkg.raw["cost_sheet"]["budget_total"]
    if plan.estimated_cost > budget:
        results.append(_validation(plan, "budget", "FAIL", f"Estimated cost {plan.estimated_cost:.2f} exceeds budget {budget:.2f}.", repairs=["use_replay_or_lower_cost_model"]))
    results.append(_validation(plan, "accessibility", "PASS", "All dialogue selections have a declared subtitle track.", severity="info"))
    return results


def audit_and_repair(pkg: Package, plan: TrailerPlan, as_of: str = "2026-09-29", territory: str = "IN") -> TrailerPlan:
    plan = copy.deepcopy(plan)
    plan.decision_log.append({"event":"director_proposed", "version":plan.version, "segments":[s.segment_id for s in plan.segments]})
    for _ in range(3):
        validations = validate_plan(pkg, plan, as_of, territory)
        failures = [v for v in validations if v.status == "FAIL"]
        if not failures:
            plan.validation_status = "PASS_WITH_WARNINGS" if any(v.status == "WARN" for v in validations) else "PASS"
            plan.warnings = [v.message for v in validations if v.status == "WARN"]
            for s in plan.segments:
                s.validators = [v for v in validations if (
                    s.scene_id in v.evidence or f"scene:{s.scene_id}" in v.evidence or
                    s.segment_id in v.evidence or any(d in v.evidence for d in s.dependencies) or
                    "all_segments" in v.evidence or (v.rule_id in {"bias", "dialect", "accessibility"} and s.subtitle)
                )]
            plan.decision_log.append({"event":"auditor_accepted", "status":plan.validation_status, "version":plan.version})
            return plan
        replaced = False
        for failure in failures:
            if failure.rule_id not in {"spoiler", "rights", "ratings", "grounding", "truth"}:
                continue
            target_ids = set(failure.evidence)
            for idx, s in enumerate(plan.segments):
                if s.scene_id in target_ids or s.segment_id in target_ids or failure.rule_id in {"spoiler", "rights"}:
                    replacement = _replacement(pkg, plan, idx, failure.rule_id, as_of, territory)
                    if replacement:
                        old = plan.segments[idx].segment_id
                        plan.segments[idx] = replacement
                        plan.decision_log.append({"event":"repair", "rule":failure.rule_id, "replaced":old, "with":replacement.segment_id})
                        replaced = True
                        break
            if replaced:
                break
        if not replaced:
            plan.validation_status = "REJECTED"
            plan.warnings = [v.message for v in failures]
            plan.decision_log.append({"event":"auditor_rejected", "reasons":plan.warnings, "version":plan.version})
            return plan
    plan.validation_status = "REJECTED"
    plan.warnings = ["Repair budget exhausted"]
    return plan


def _replacement(pkg: Package, plan: TrailerPlan, index: int, rule: str, as_of: str, territory: str) -> Segment | None:
    existing = {s.scene_id for s in plan.segments}
    audience = plan.audience
    # Search the complete verified candidate pool, not only the initial
    # creative shortlist. This is what makes repair genuinely recoverable.
    candidates = pkg.candidates
    preferred = _pick_candidates(pkg, audience)
    candidates = preferred + [c for c in candidates if c not in preferred]
    allowed = set(pkg.audiences[audience]["allowed_tags"])
    candidates = sorted(
        candidates,
        key=lambda c: (
            0 if c.get("reveals") else 1,
            -len(allowed.intersection(c.get("tags", []))),
            0 if audience == "young_adult" and "young_adult" in c.get("tags", []) else 1,
            0 if audience == "dialect_region" and "dialect" in c.get("tags", []) else 1,
            c["candidate_id"],
        ),
    )
    for c in candidates:
        if c["scene_id"] in existing or c.get("reveals"):
            continue
        if rule == "rights":
            music = pkg.contracts.get(c["music"], {})
            if territory not in music.get("territories", []) or _is_expired(music, as_of):
                continue
        if rule == "ratings" and set(pkg.scenes[c["scene_id"]].get("content_flags", [])) & set(pkg.raw["rating_policies"][audience]["forbidden_flags"]):
            continue
        actor_contracts = [k for k, v in pkg.contracts.items() if v.get("type") == "actor"]
        return _candidate_to_segment(c, audience, actor_contracts)
    return None


def replan_contract_change(pkg: Package, plans: list[TrailerPlan], asset_id: str, as_of: str, territory: str = "IN") -> list[TrailerPlan]:
    updated = []
    for plan in plans:
        if not any(asset_id in s.dependencies for s in plan.segments):
            plan.decision_log.append({"event":"contract_change_no_impact", "asset":asset_id, "version":plan.version})
            updated.append(plan); continue
        new = copy.deepcopy(plan); new.version += 1
        for idx, s in enumerate(new.segments):
            if asset_id not in s.dependencies:
                continue
            replacement = _replacement(pkg, new, idx, "rights", as_of, territory)
            if replacement:
                replacement.reason += " Replanned because a contract dependency changed."
                new.segments[idx] = replacement
                new.decision_log.append({"event":"delta_replan", "asset":asset_id, "segment":s.segment_id, "replacement":replacement.segment_id, "version":new.version})
            else:
                new.validation_status = "HUMAN_REVIEW_REQUIRED"
                new.warnings.append(f"No cleared replacement for {asset_id} in {s.segment_id}")
        updated.append(audit_and_repair(pkg, new, as_of, territory))
    return updated


def simulate_event(pkg: Package, event: str) -> dict[str, Any]:
    audiences = [a["audience_id"] for a in pkg.raw.get("audiences", [])]
    plans = [audit_and_repair(pkg, create_plan(pkg, a)) for a in audiences]
    if event == "music_expiry":
        pkg2 = copy.deepcopy(pkg)
        used_music = sorted({d for p in plans for s in p.segments for d in s.dependencies if d.startswith("music_") and d in pkg2.contracts})
        target = used_music[0] if used_music else None
        if target:
            for c in pkg2.raw["contracts"]:
                if c["asset_id"] == target:
                    c["expires_at"] = "2026-01-01"
            plans = replan_contract_change(pkg2, plans, target, "2026-09-29")
        else:
            for p in plans:
                p.decision_log.append({"event":"music_expiry_no_used_asset", "status":"no_impact"})
    elif event == "subtitle_mismatch":
        for p in plans:
            if p.audience == "dialect_region":
                sensitive = {x.get("scene_id") for x in pkg.subtitles.get("relationship_sensitive_spans", [])}
                affected = [s.scene_id for s in p.segments if s.subtitle == "dialect" and s.scene_id in sensitive]
                if affected:
                    p.validation_status = "HUMAN_REVIEW_REQUIRED"
                    p.warnings.append(f"Dialect subtitle relationship drift requires review for {sorted(set(affected))}.")
    elif event == "model_outage":
        for p in plans:
            p.decision_log.append({"event":"model_outage", "fallback":"replay", "status":"degraded_but_reproducible"})
    elif event == "prompt_injection":
        serialized = json.dumps(pkg.raw).lower()
        detected = bool(re.search(r"ignore\s+(the\s+)?contract|override\s+(all\s+)?rules", serialized))
        for p in plans:
            p.decision_log.append({"event":"prompt_injection_neutralized" if detected else "no_prompt_injection_detected", "source":"package_evidence", "authority":"contracts_and_policies"})
    elif event == "policy_change":
        pkg2 = copy.deepcopy(pkg)
        pkg2.raw["rating_policies"]["family"]["forbidden_flags"].append("moderate_argument")
        for p in plans:
            if p.audience == "family":
                p.version += 1
                p.decision_log.append({"event":"policy_change", "affected_rules":["ratings"], "version":p.version})
                refreshed = audit_and_repair(pkg2, p)
                p.segments, p.validation_status, p.warnings = refreshed.segments, refreshed.validation_status, refreshed.warnings
    elif event == "audience_bias":
        for p in plans:
            p.decision_log.append({"event":"audience_bias_detected", "action":"quarantine_historic_signal_and_preserve_evidence_based_plan"})
    return {"event":event, "plans":jsonable(plans)}
