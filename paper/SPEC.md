# MedDSL-Lite Specification

## Overview

MedDSL-Lite is a domain-specific language for encoding clinical decision rules in ophthalmology, specifically designed for diabetic retinopathy triage. It provides a safe, auditable, and explainable alternative to black-box AI systems.

## Core Design Principles

1. **Determinism**: Same input always produces identical output
2. **Safety**: Graceful handling of errors with safety stops
3. **Transparency**: Complete execution trace with citations
4. **Auditability**: Rule-based decisions can be reviewed and validated
5. **Extensibility**: Easy to modify rules without changing code

## DSL Grammar

### Meta Information
```yaml
meta:
  profile: string          # Rule set identifier
  version: string          # Version number
  entry: string           # Entry point node ID
```

### Node Types

#### Decision Node
```yaml
- id: string              # Unique node identifier
  type: "decision"
  when: string            # Boolean expression to evaluate
  goto_true: string       # Next node if condition is true
  goto_false: string      # Next node if condition is false
  cite: [string]          # Optional citation IDs
```

#### Action Node
```yaml
- id: string              # Unique node identifier
  type: "action"
  actions:                # List of actions to execute
    - type: string        # Action type
      # ... action-specific parameters
  cite: [string]          # Optional citation IDs
```

### Boolean Expressions

The `when` field supports:
- **Literals**: `true`, `false`, `null`, numbers, strings
- **Field references**: `age`, `dr_grade`, `macula.edema_prob`
- **Operators**: `==`, `!=`, `>=`, `>`, `<=`, `<`, `and`, `or`, `not`
- **Parentheses**: For grouping expressions

### Action Types

#### suggest_referral
```yaml
type: "suggest_referral"
specialty: "retina" | "optometry"
urgency: "urgent" | "2-4_weeks" | "routine"
```

#### order_test
```yaml
type: "order_test"
test_type: "OCT_macula" | "fundus_photo"
```

#### set_followup
```yaml
type: "set_followup"
interval: "3m" | "6m" | "12m"
```

#### abstain
```yaml
type: "abstain"
reason: string
```

## Case Schema

```json
{
  "eye": "OD" | "OS",
  "age": number,
  "vision_reduced": boolean,
  "qc": {
    "fundus_pass": boolean,
    "macula_view": boolean
  },
  "dr_grade": "no_dr" | "mild_npdr" | "moderate_npdr" | "severe_npdr" | "pdr" | null,
  "macula": {
    "edema_prob": number | null
  }
}
```

## Execution Model

1. **Validation**: Check case schema and rule structure
2. **Entry Point**: Start at `meta.entry` or first node
3. **Decision Evaluation**: Evaluate `when` conditions using safe parser
4. **Action Execution**: Execute actions and collect results
5. **Trace Generation**: Record complete execution path
6. **Safety Stops**: Handle errors gracefully with safety stops

## Safety Mechanisms

- **Parse Errors**: Invalid expressions trigger safety stops
- **Missing Nodes**: References to non-existent nodes trigger safety stops
- **Cycles**: Infinite loops detected and stopped
- **Max Iterations**: Execution limited to prevent runaway processes
- **Schema Validation**: Case data validated against schema

## Trace Format

Each trace entry contains:
```json
{
  "node": "node_id",
  "type": "decision" | "action" | "safety_stop",
  "outcome": "true" | "false" | "error_message",
  "actions": [action_objects],
  "cite": ["citation_id"],
  "profile": "rule_profile",
  "version": "rule_version",
  "rule_hash": "sha256_hash",
  "timestamp": "iso_timestamp"
}
```

## Rule Hash

Rules are canonicalized and hashed using SHA-256 to ensure:
- **Versioning**: Detect rule changes
- **Auditability**: Track which rules were used
- **Reproducibility**: Verify rule consistency

## Citation System

Citations link to medical literature snippets:
```json
{
  "id": "citation_id",
  "source": "AAO PPP: Diabetic Retinopathy",
  "line": "Full guideline text",
  "short_quote": "Condensed quote for display"
}
```

## Evaluation Metrics

### Determinism
- Percentage of identical decisions across runs
- Trace consistency validation

### Faithfulness
- Binary metric: rationale mentions thresholds/branches from trace
- Citation accuracy validation

### Safety
- Safety stop frequency
- Error handling effectiveness

## Implementation Notes

- **Parser**: Pratt parser for safe expression evaluation
- **Interpreter**: State machine with cycle detection
- **Validator**: Schema validation and rule linting
- **Retriever**: TF-IDF based snippet retrieval
- **Explainer**: Template-based explanation generation

## Future Extensions

- **Images**: Support for image-based features
- **Temporal Logic**: Time-based conditions
- **Uncertainty**: Probabilistic reasoning
- **Learning**: Rule refinement from data
- **Verification**: Formal verification of rule properties
