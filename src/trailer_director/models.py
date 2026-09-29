from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class Validation:
    rule_id: str
    status: str
    severity: str = "info"
    message: str = ""
    evidence: list[str] = field(default_factory=list)
    repair_options: list[str] = field(default_factory=list)
    human_approval_required: bool = False

@dataclass
class Segment:
    segment_id: str
    scene_id: str
    source_in: str
    source_out: str
    video: str
    audio: str
    subtitle: str | None
    claim: str
    reason: str
    dependencies: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    validators: list[Validation] = field(default_factory=list)
    transition: str = "HARD_CUT"
    voice_over: str | None = None
    text_card: str | None = None
    music: str | None = None
    evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    dialogue: str | None = None

@dataclass
class TrailerPlan:
    trailer_id: str
    audience: str
    duration_seconds: int
    audience_promise: str
    emotional_journey: list[str]
    segments: list[Segment]
    estimated_cost: float
    validation_status: str = "PENDING"
    version: int = 1
    warnings: list[str] = field(default_factory=list)
    decision_log: list[dict[str, Any]] = field(default_factory=list)
    objective: str = ""
    fallback_plan: str = "Use deterministic replay and flag visual suitability for human review if a preferred model is unavailable."
    human_approvals: list[str] = field(default_factory=list)

@dataclass
class Package:
    raw: dict[str, Any]
    subtitles: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return float(self.raw["episode_manifest"]["duration_seconds"])

    @property
    def scenes(self) -> dict[str, dict[str, Any]]:
        return {s["scene_id"]: s for s in self.raw["episode_manifest"]["scenes"]}

    @property
    def candidates(self) -> list[dict[str, Any]]:
        return self.raw["episode_manifest"]["candidates"]

    @property
    def contracts(self) -> dict[str, dict[str, Any]]:
        return {c["asset_id"]: c for c in self.raw["contracts"]}

    @property
    def protected_facts(self) -> dict[str, dict[str, Any]]:
        return {f["fact_id"]: f for f in self.raw["story_map"]["protected_facts"]}

    @property
    def story_facts(self) -> dict[str, dict[str, Any]]:
        return {f["fact_id"]: f for f in self.raw["story_map"]["facts"]}

    @property
    def audiences(self) -> dict[str, dict[str, Any]]:
        return {a["audience_id"]: a for a in self.raw["audiences"]}

def jsonable(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    return obj
