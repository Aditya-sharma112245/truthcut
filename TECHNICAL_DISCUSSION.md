# Technical Discussion Preparation

## How is a spoiler defined?

TruthCut defines a spoiler as a protected narrative fact or direct causal disclosure that resolves the central story question before the intended trailer moment. Protected facts live in the story map. Scenes and dialogue map to those facts. The deterministic auditor rejects direct reveals, while a separate semantic check can escalate contextual leakage to human review.

## How are creative generation and validation independent?

The Director proposes an audience promise, three-act arc, and candidate segments. The Auditor receives the candidate plus canonical manifests, contracts, policies, and protected facts. It does not treat the Director's confidence or explanation as evidence. Hard predicates can veto a creative choice.

## What happens when a music contract changes?

Every segment has dependency IDs. A contract change invalidates only segments referencing that music asset. The replanner selects a cleared replacement, reruns rights, duration, accessibility, and cost checks, increments the plan version, and records a diff. Plans without that dependency stay unchanged.

## How is dialect personalization kept respectful?

The dialect plan uses supplied language evidence and episode facts, not location-based stereotypes. The system checks for dialect-only comedy framing and requires human review where a subtitle can change a relationship. The dialect track is a source of linguistic intimacy, not a proxy for an assumed preference.

## What fails first at scale?

Fine-grained cross-modal verification is the first bottleneck: confirming that a short visual interval, audio, subtitle, character, and marketing claim all agree. Caching, hierarchical scene indexing, targeted high-resolution inspection, and review on disagreement are the mitigations.

## What did AI suggest that looked plausible but was wrong?

A plausible suggestion was to optimize historical engagement directly. That would over-select a viral spoiler and reproduce regional or social bias. TruthCut quarantines historic performance as a hypothesis feature and applies hard constraints first.

## Intentional tradeoffs

The prototype uses a deterministic replay manifest instead of pretending that a coarse video model is a source of truth. It emits EDLs instead of rendering a final master. These choices prioritize reproducibility, evidence, and evaluator trust within the 10–12 hour timebox.
