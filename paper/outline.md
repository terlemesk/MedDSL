# MedDSL-Lite Paper Outline

## Title
**MedDSL-Lite: A Deterministic Domain-Specific Language for Clinical Decision Support in Diabetic Retinopathy Triage**

## Abstract
We present MedDSL-Lite, a domain-specific language for encoding clinical decision rules in ophthalmology. Unlike black-box AI systems, MedDSL-Lite provides deterministic, auditable, and explainable clinical decision support. We demonstrate its effectiveness through a 3-arm evaluation comparing LLM-only, rules-only, and hybrid approaches on diabetic retinopathy triage tasks. Results show significant improvements in determinism and faithfulness while maintaining clinical accuracy.

## 1. Introduction

### 1.1 Problem Statement
- Trust gap in AI clinical decision support
- Need for auditable and explainable systems
- Challenges with black-box AI in healthcare

### 1.2 Related Work
- Classic CDSS: Arden Syntax, GLIF, FHIR CDS Hooks
- Modern AI approaches: LLMs, neural networks
- Hybrid approaches: Rules + AI

### 1.3 Contributions
- Novel DSL for clinical decision rules
- Deterministic execution with safety mechanisms
- Comprehensive evaluation framework
- Open-source implementation

## 2. Methods

### 2.1 MedDSL-Lite Design
- DSL grammar and syntax
- Case schema definition
- Boolean expression parser
- Execution model

### 2.2 Safety Mechanisms
- Parse error handling
- Cycle detection
- Safety stops
- Schema validation

### 2.3 Explanation Generation
- Trace-based explanations
- Citation retrieval system
- Template-based prose generation
- LLM-assisted rewriting

### 2.4 Evaluation Protocol
- 3-arm comparison design
- Metrics: determinism, faithfulness, safety
- Dataset: synthetic DR cases
- Statistical analysis

## 3. Results

### 3.1 Determinism Analysis
- Identical decision rates across arms
- Trace consistency validation
- Performance comparison

### 3.2 Faithfulness Evaluation
- Threshold mention rates
- Citation accuracy
- Rationale quality assessment

### 3.3 Safety Assessment
- Error handling effectiveness
- Safety stop frequency
- Robustness testing

### 3.4 Clinical Accuracy
- Decision correctness (simulated)
- Guideline adherence
- Edge case handling

## 4. Discussion

### 4.1 Advantages of Rule-Based Approach
- Determinism and reproducibility
- Auditability and transparency
- Clinical validation capability
- Safety guarantees

### 4.2 Limitations
- No image analysis
- Retrospective evaluation
- Small sample size
- Limited to DR triage

### 4.3 Future Work
- Prospective clinical validation
- Multi-specialty expansion
- Image feature integration
- Formal verification

### 4.4 Clinical Implications
- Trust and adoption
- Regulatory considerations
- Implementation challenges
- Quality assurance

## 5. Conclusion

MedDSL-Lite demonstrates that deterministic, rule-based clinical decision support can achieve comparable accuracy to LLM-based approaches while providing superior transparency and auditability. The system's safety mechanisms and explanation capabilities make it suitable for clinical deployment.

## References

### Medical Guidelines
- American Academy of Ophthalmology. Diabetic Retinopathy PPP. 2023.
- EURETINA. Diabetic Macular Edema Guidelines. 2023.

### Technical References
- Arden Syntax for Medical Logic Systems
- GLIF: Guideline Interchange Format
- FHIR CDS Hooks
- Pratt Parsing

### Evaluation Metrics
- Determinism in Clinical Decision Support
- Faithfulness in AI Explanations
- Safety in Medical AI Systems

## Appendices

### A. Complete DSL Grammar
### B. Case Schema Definition
### C. Safety Mechanism Details
### D. Evaluation Dataset
### E. Statistical Analysis Results
### F. Source Code Availability
