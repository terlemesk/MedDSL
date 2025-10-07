# MedDSL-Lite

Medical Domain Specific Language for Agentic AI Clinical Reasoning (ophthalmology prototype)

## Overview

MedDSL-Lite is a domain-specific language for encoding clinical decision rules in ophthalmology, specifically designed for diabetic retinopathy triage. It provides a safe, auditable, and explainable alternative to black-box AI systems.

## Key Features

- **Deterministic Execution**: Same input always produces identical output
- **Safety Mechanisms**: Graceful error handling with safety stops
- **Complete Traceability**: Full execution trace with citations
- **Auditable Decisions**: Rule-based decisions can be reviewed and validated
- **Extensible Rules**: Easy to modify rules without changing code

## Quick Start

### Installation

```bash
git clone https://github.com/terlemesk/MedDSL.git
cd MedDSL
pip install -r requirements.txt
```

### Basic Usage

```python
from mddsl import execute, explain, SnippetRetriever
from mddsl.interpreter import load_dsl_from_file

# Load DSL rules
dsl = load_dsl_from_file("rules/dr_triage_v1.yaml")

# Define a case
case = {
    "eye": "OD",
    "age": 62,
    "vision_reduced": True,
    "qc": {"fundus_pass": True, "macula_view": True},
    "dr_grade": "severe_npdr",
    "macula": {"edema_prob": 0.35}
}

# Execute rules
actions, trace = execute(dsl, case)

# Generate explanation
retriever = SnippetRetriever("snippets")
explanation = explain(case, actions, trace, retriever)

print("Actions:", actions)
print("Rule Trace:", explanation["rule_trace"])
print("Citations:", explanation["citations"])
```

## Project Structure

```
meddsl/
├── mddsl/                 # Core library
│   ├── __init__.py
│   ├── dsl_parser.py     # Safe boolean expression parser
│   ├── interpreter.py    # DSL interpreter with tracing
│   ├── validator.py      # Case and rule validators
│   ├── retrieval.py      # Citation snippet retriever
│   ├── explainer.py      # Explanation generator
│   ├── case_schema.json  # Case data schema
│   └── rules_schema.json # Rule structure schema
├── rules/                # Rule definitions
│   ├── dr_triage_v1.yaml
│   └── clinic_overrides_example.yaml
├── snippets/             # Citation snippets
│   └── aao_euretina.jsonl
├── data/                 # Test cases
│   └── cases_small.jsonl
├── notebooks/            # Demo and evaluation notebooks
│   ├── 01_trace_demo.ipynb
│   └── 02_eval_report.ipynb
├── tests/                # Unit tests
│   ├── test_parser.py
│   ├── test_interpreter.py
│   └── test_safety.py
├── paper/                # Research documentation
│   ├── SPEC.md
│   ├── outline.md
│   └── refs.bib
└── README.md
```

## DSL Grammar

### Basic Structure

```yaml
meta:
  profile: "diabetic_retinopathy_triage"
  version: "1.0.0"
  entry: "qc_check"

nodes:
  - id: "qc_check"
    type: "decision"
    when: "qc.fundus_pass == true and qc.macula_view == true"
    goto_true: "grade_check"
    goto_false: "qc_fail"
    cite: ["QC_retake_fundus"]

  - id: "qc_fail"
    type: "action"
    actions:
      - type: "abstain"
        reason: "insufficient image quality"
```

### Boolean Expressions

Supported operators and syntax:
- **Literals**: `true`, `false`, `null`, numbers, strings
- **Field references**: `age`, `dr_grade`, `macula.edema_prob`
- **Comparison**: `==`, `!=`, `>=`, `>`, `<=`, `<`
- **Logical**: `and`, `or`, `not`
- **Grouping**: `(expression)`

### Action Types

- **suggest_referral**: Recommend referral to specialist
- **order_test**: Order diagnostic tests
- **set_followup**: Schedule follow-up appointments
- **abstain**: Decline to make recommendation

## Evaluation

The project includes a 3-arm evaluation comparing:

1. **LLM-only**: Pure language model approach
2. **Rules-only**: Pure rule-based approach
3. **Hybrid**: Rules with LLM-assisted explanation

Key metrics:
- **Determinism**: Consistency across runs
- **Faithfulness**: Alignment with rule logic
- **Safety**: Error handling effectiveness

## Safety Mechanisms

- **Parse Errors**: Invalid expressions trigger safety stops
- **Missing Nodes**: References to non-existent nodes handled gracefully
- **Cycles**: Infinite loops detected and stopped
- **Schema Validation**: Case data validated against schema
- **Max Iterations**: Execution limited to prevent runaway processes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test files
python -m pytest tests/test_parser.py
python -m pytest tests/test_interpreter.py
python -m pytest tests/test_safety.py
```

## Documentation

- [Complete Specification](paper/SPEC.md)
- [Paper Outline](paper/outline.md)
- [Demo Notebook](notebooks/01_trace_demo.ipynb)
- [Evaluation Report](notebooks/02_eval_report.ipynb)

## Citation

If you use MedDSL-Lite in your research, please cite:

```bibtex
@article{meddsl_lite_2024,
  title={MedDSL-Lite: A Deterministic Domain-Specific Language for Clinical Decision Support},
  author={Terlemesk, K. and Contributors},
  journal={Journal of Medical Internet Research},
  year={2024},
  note={Under Review}
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- American Academy of Ophthalmology for diabetic retinopathy guidelines
- EURETINA for diabetic macular edema guidelines
- Contributors to the open-source medical AI community
