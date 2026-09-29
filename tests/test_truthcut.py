import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trailer_director.engine import (
    AUDIENCE_ORDER, audit_and_repair, create_plan, load_package,
    replan_contract_change, simulate_event, validate_plan,
)
from trailer_director.models import Segment

class TruthCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = load_package(ROOT / "data/package.json")

    def test_all_three_plans_are_distinct_and_valid(self):
        plans = [audit_and_repair(self.pkg, create_plan(self.pkg, a)) for a in AUDIENCE_ORDER]
        self.assertEqual([p.validation_status for p in plans], ["PASS_WITH_WARNINGS"] * 3)
        self.assertEqual(len({tuple(s.video for s in p.segments) for p in plans}), 3)
        self.assertTrue(any(s.subtitle == "dialect" for s in plans[2].segments))
        self.assertTrue(all(s.transition and s.text_card and s.music and s.evidence for p in plans for s in p.segments))
        self.assertTrue(all(p.fallback_plan for p in plans))

    def test_missing_scene_is_rejected(self):
        plan = create_plan(self.pkg, "family")
        plan.segments[0].scene_id = "scene_99"
        result = validate_plan(self.pkg, plan)
        self.assertTrue(any(v.rule_id == "grounding" and v.status == "FAIL" for v in result))

    def test_spoiler_is_repaired_even_when_it_is_high_performing(self):
        plan = create_plan(self.pkg, "young_adult")
        self.assertTrue(any("cand_11" in s.segment_id for s in plan.segments))
        repaired = audit_and_repair(self.pkg, plan)
        self.assertNotIn("scene_11", [s.scene_id for s in repaired.segments])
        self.assertEqual(repaired.validation_status, "PASS_WITH_WARNINGS")
        self.assertTrue(any(x.get("event") == "repair" and x.get("rule") == "spoiler" for x in repaired.decision_log))

    def test_rights_restriction_is_rejected(self):
        pkg = copy.deepcopy(self.pkg)
        plan = create_plan(pkg, "dialect_region")
        for c in pkg.raw["contracts"]:
            if c["asset_id"] == "music_03":
                c["territories"] = ["GB"]
        result = validate_plan(pkg, plan, territory="IN")
        self.assertTrue(any(v.rule_id == "rights" and v.status == "FAIL" for v in result))

    def test_changed_contract_replans_only_dependents(self):
        plans = [audit_and_repair(self.pkg, create_plan(self.pkg, a)) for a in AUDIENCE_ORDER]
        old = {p.trailer_id: tuple(s.segment_id for s in p.segments) for p in plans}
        updated = replan_contract_change(self.pkg, plans, "music_03", "2026-01-01")
        family = next(p for p in updated if p.trailer_id == "family_v1")
        young_adult = next(p for p in updated if p.trailer_id == "young_adult_v1")
        dialect = next(p for p in updated if p.trailer_id == "dialect_region_v1")
        self.assertNotEqual(old["family_v1"], tuple(s.segment_id for s in family.segments))
        self.assertEqual(old["young_adult_v1"], tuple(s.segment_id for s in young_adult.segments))
        self.assertGreaterEqual(dialect.version, 1)
        self.assertTrue(any(x.get("event") == "delta_replan" for x in dialect.decision_log))

    def test_family_policy_blocks_threat(self):
        plan = create_plan(self.pkg, "family")
        plan.segments[0] = Segment("bad", "scene_09", "10:16.000", "10:25.000", "threat", "dialogue_threat", "standard", "unsupported", ["scene_09", "music_01"])
        result = validate_plan(self.pkg, plan)
        self.assertTrue(any(v.rule_id == "ratings" and v.status == "FAIL" for v in result))

    def test_clickbait_claim_is_rejected(self):
        plan = create_plan(self.pkg, "young_adult")
        plan.segments[0].claim = "They must kill each other tonight"
        result = validate_plan(self.pkg, plan)
        self.assertTrue(any(v.rule_id == "truth" and v.status == "FAIL" for v in result))

    def test_audience_bias_is_quarantined(self):
        result = simulate_event(self.pkg, "audience_bias")
        self.assertTrue(all(any(x.get("event") == "audience_bias_detected" for x in p["decision_log"]) for p in result["plans"]))

    def test_music_expiry_discovers_renamed_music_asset(self):
        pkg = copy.deepcopy(self.pkg)
        for contract in pkg.raw["contracts"]:
            if contract["asset_id"] == "music_03":
                contract["asset_id"] = "score_custom"
        for candidate in pkg.raw["episode_manifest"]["candidates"]:
            if candidate["music"] == "music_03":
                candidate["music"] = "score_custom"
        result = simulate_event(pkg, "music_expiry")
        self.assertEqual(len(result["plans"]), 3)

    def test_empty_plan_is_rejected(self):
        plan = create_plan(self.pkg, "family")
        plan.segments = []
        audited = audit_and_repair(self.pkg, plan)
        self.assertEqual(audited.validation_status, "REJECTED")
        self.assertTrue(any("No candidate clips" in x for x in audited.warnings))

    def test_normal_validation_quarantines_prompt_injection(self):
        plan = audit_and_repair(self.pkg, create_plan(self.pkg, "family"))
        self.assertTrue(any("untrusted evidence" in x for x in plan.warnings))

    def test_dialect_relationship_drift_requires_human_review(self):
        plan = create_plan(self.pkg, "dialect_region")
        result = validate_plan(self.pkg, plan)
        self.assertTrue(any(v.rule_id == "dialect" and v.status == "WARN" and v.human_approval_required for v in result))

    def test_prompt_injection_is_logged_not_executed(self):
        result = simulate_event(self.pkg, "prompt_injection")
        self.assertTrue(all(any(x.get("event") == "prompt_injection_neutralized" for x in p["decision_log"]) for p in result["plans"]))
        self.assertTrue(all(p["validation_status"] in {"PASS_WITH_WARNINGS", "PASS"} for p in result["plans"]))

    def test_model_outage_has_replay_fallback(self):
        result = simulate_event(self.pkg, "model_outage")
        self.assertTrue(all(any(x.get("fallback") == "replay" for x in p["decision_log"]) for p in result["plans"]))

    def test_budget_failure_is_visible(self):
        pkg = copy.deepcopy(self.pkg)
        pkg.raw["cost_sheet"]["budget_total"] = 0.01
        plan = create_plan(pkg, "family")
        result = validate_plan(pkg, plan)
        self.assertTrue(any(v.rule_id == "budget" and v.status == "FAIL" for v in result))

    def test_event_simulations_cover_change_paths(self):
        for event in ("music_expiry", "subtitle_mismatch", "model_outage", "prompt_injection", "policy_change", "audience_bias"):
            result = simulate_event(self.pkg, event)
            self.assertEqual(result["event"], event)
            self.assertEqual(len(result["plans"]), 3)

if __name__ == "__main__":
    unittest.main()
