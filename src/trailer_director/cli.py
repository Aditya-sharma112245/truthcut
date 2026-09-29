from __future__ import annotations
import argparse, json
from pathlib import Path
from .engine import audit_and_repair, create_plan, load_package, simulate_event, replan_contract_change
from .models import jsonable
from .report import render_report


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(value), indent=2), encoding="utf-8")


def plan_output(plan):
    value = jsonable(plan)
    value["validation"] = {"status": plan.validation_status, "warnings": plan.warnings, "human_approvals": plan.human_approvals}
    return value


def write_markdown_report(out: Path, report: dict):
    lines = ["# TruthCut Validation Report", "", f"- Mode: `{report['mode']}`", f"- Territory: `{report['territory']}`", f"- As of: `{report['as_of']}`", "", "## Plans", ""]
    for p in report["plans"]:
        lines += [f"### {p['audience']}", f"- Status: **{p['status']}**", f"- Duration: {p['duration_seconds']} seconds", f"- Segments: {', '.join(p['segments'])}", f"- Warnings: {'; '.join(p['warnings']) or 'None'}", ""]
    (out / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args):
    pkg = load_package(args.package)
    if args.audiences:
        custom = json.loads(Path(args.audiences).read_text(encoding="utf-8"))
        pkg.raw["audiences"] = custom["audiences"] if isinstance(custom, dict) and "audiences" in custom else custom
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plans = []
    audience_ids = [a["audience_id"] for a in pkg.raw.get("audiences", [])]
    for audience in audience_ids:
        plan = audit_and_repair(pkg, create_plan(pkg, audience), args.as_of, args.territory)
        plans.append(plan)
        write_json(out / f"{audience}_trailer.json", plan_output(plan))
    report = {
        "product": "TruthCut",
        "mode": args.mode,
        "territory": args.territory,
        "as_of": args.as_of,
        "plans": [{"trailer_id":p.trailer_id,"audience":p.audience,"status":p.validation_status,"duration_seconds":p.duration_seconds,"segments":[s.segment_id for s in p.segments],"warnings":p.warnings} for p in plans]
    }
    write_json(out / "validation_report.json", report)
    write_json(out / "story_map.json", pkg.raw["story_map"])
    write_json(out / "constraint_map.json", {
        "trusted_inputs": ["episode_manifest", "contracts", "rating_policies", "audiences", "cost_sheet", "protected_facts"],
        "untrusted_evidence": ["scene_descriptions", "historic_performance", "free_text_notes", "automatic_captions"],
        "validators": ["schema", "grounding", "story_truth", "spoiler", "rights", "ratings", "dialect", "accessibility", "duration", "budget", "bias"],
    })
    write_json(out / "spoiler_map.json", {
        "protected_facts": pkg.raw["story_map"].get("protected_facts", []),
        "candidate_reveals": [{"candidate_id": c["candidate_id"], "reveals": c.get("reveals", []), "classification": "MAJOR" if c.get("reveals") else "SAFE"} for c in pkg.candidates],
    })
    write_markdown_report(out, report)
    print(json.dumps(report, indent=2))


def simulate(args):
    pkg = load_package(args.package)
    result = simulate_event(pkg, args.event)
    write_json(Path(args.out) / f"event_{args.event}.json", result)
    print(json.dumps({"event":args.event,"statuses":[{"trailer_id":p["trailer_id"],"status":p["validation_status"],"version":p["version"]} for p in result["plans"]]}, indent=2))


def report(args):
    render_report(args.run_dir, args.output)
    print(json.dumps({"report": str(args.output), "status": "created"}, indent=2))


def main():
    parser = argparse.ArgumentParser(prog="truthcut", description="Verifiable audience-aware trailer planning")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="generate and audit all three trailer plans")
    run_p.add_argument("package", type=Path)
    run_p.add_argument("--mode", choices=["replay","live"], default="replay")
    run_p.add_argument("--out", type=Path, default=Path("sample_run"))
    run_p.add_argument("--as-of", default="2026-09-29")
    run_p.add_argument("--territory", default="IN")
    run_p.add_argument("--audiences", type=Path, help="optional JSON file containing an audiences array")
    run_p.set_defaults(func=run)
    sim_p = sub.add_parser("simulate", help="exercise an evaluator surprise event")
    sim_p.add_argument("package", type=Path)
    sim_p.add_argument("--event", choices=["music_expiry","subtitle_mismatch","model_outage","prompt_injection","policy_change","audience_bias"], required=True)
    sim_p.add_argument("--out", type=Path, default=Path("sample_run"))
    sim_p.set_defaults(func=simulate)
    report_p = sub.add_parser("report", help="render a lightweight HTML EDL inspector")
    report_p.add_argument("run_dir", type=Path)
    report_p.add_argument("--output", type=Path, default=Path("sample_run/edl_inspector.html"))
    report_p.set_defaults(func=report)
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
