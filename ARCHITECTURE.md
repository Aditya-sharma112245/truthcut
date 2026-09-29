# Architecture

## Design principle

Generation is probabilistic. Acceptance is evidence-based.

The Director can propose a strong idea, but the Auditor can reject it. The planner never receives authority to change contracts, ratings policy, canonical scene IDs, or protected spoiler facts.

## Pipeline

```text
package.json
   ↓
trusted schemas + untrusted evidence separation
   ↓
story map / candidate pool / dependency index
   ↓
Director: audience promise + three-act EDL
   ↓
Auditor: grounding, truth, spoiler, rights, safety, dialect,
         accessibility, duration, budget
   ↓
bounded repair or rejection
   ↓
versioned JSON EDL + decision ledger + diff log
```

## Trust boundaries

Trusted inputs are the canonical episode manifest, structured contracts, rating policies, configured budget, and human-approved protected facts.

Scene descriptions, historical scores, free-text audience data, automatic captions, and instruction-like text embedded in content are evidence, not instructions. Normal validation scans for instruction-like text, emits a security warning, and quarantines it from contract and policy decisions. This protects against indirect prompt injection.

## Spoiler graph

The fixture's story map contains facts and edges from scenes to facts. Protected facts are checked for direct reveal overlap. The prototype also emits human review for contextual or semantic ambiguity because graph reachability cannot guarantee detection of every implied reveal.

## Independent validation

The Director and Auditor are separate modules. The Auditor does not accept the Director's confidence as evidence. Deterministic validation is used for identifiers, intervals, rights, expiry, territory, duration, budget, and explicit spoiler tags. Semantic checks return warnings or human-review statuses when confidence is insufficient.

## Delta replanning

Each segment stores scene, music, actor, subtitle, and claim dependencies. A changed asset invalidates only segments that reference it. The replanner selects from the complete verified candidate pool, preserves unaffected segments, reruns relevant validators, and records a versioned decision diff.

## Memory and state architecture

The prototype's memory is an explicit versioned state, not hidden conversation context. The evidence store holds the canonical package, story facts, subtitle relationship spans, contracts, and audience definitions. The dependency index maps assets and rules to plan segments. The decision ledger stores the Director proposal, Auditor results, repairs, warnings, plan version, and change event. Replay mode reconstructs the same state from files, while a production service would persist these objects in a database or event log.

## Why replay mode exists

The evaluator must be able to run the system without personal keys. Replay mode is deterministic and uses the same typed output and validators as live mode. A live multimodal adapter can be added later without changing the acceptance layer.

## Scaling bottleneck

The first large-scale bottleneck is fine-grained cross-modal verification: confirming that a short visual interval, audio, subtitle, character, and marketing claim agree. Caching, hierarchical indexing, targeted frame inspection, and human review on disagreement are the mitigation strategy.
