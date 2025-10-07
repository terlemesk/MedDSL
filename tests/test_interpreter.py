"""
Unit tests for the DSL interpreter.
"""

import unittest
import json
from mddsl.interpreter import execute, InterpreterError, canonicalize_and_hash
from mddsl.dsl_parser import ParseError


class TestInterpreter(unittest.TestCase):
    """Test cases for the DSL interpreter."""
    
    def setUp(self):
        """Set up test DSL and case data."""
        self.test_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "start"
            },
            "nodes": [
                {
                    "id": "start",
                    "type": "decision",
                    "when": "age > 60",
                    "goto_true": "high_risk",
                    "goto_false": "low_risk"
                },
                {
                    "id": "high_risk",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                },
                {
                    "id": "low_risk",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        self.test_case = {
            "age": 65,
            "vision_reduced": True,
            "dr_grade": "moderate_npdr"
        }
    
    def test_basic_execution(self):
        """Test basic DSL execution."""
        actions, trace = execute(self.test_dsl, self.test_case)
        
        # Should have one action (urgent referral for age > 60)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "suggest_referral")
        self.assertEqual(actions[0]["urgency"], "urgent")
        
        # Should have trace entries
        self.assertGreater(len(trace), 0)
        
        # Check trace structure
        trace_entry = trace[0]
        self.assertIn("node", trace_entry)
        self.assertIn("type", trace_entry)
        self.assertIn("timestamp", trace_entry)
    
    def test_determinism(self):
        """Test that same input produces identical output."""
        actions1, trace1 = execute(self.test_dsl, self.test_case)
        actions2, trace2 = execute(self.test_dsl, self.test_case)
        
        # Actions should be identical
        self.assertEqual(actions1, actions2)
        
        # Traces should be identical (except timestamps)
        self.assertEqual(len(trace1), len(trace2))
        for i in range(len(trace1)):
            entry1 = trace1[i].copy()
            entry2 = trace2[i].copy()
            # Remove timestamps for comparison
            entry1.pop("timestamp", None)
            entry2.pop("timestamp", None)
            self.assertEqual(entry1, entry2)
    
    def test_qc_fail_path(self):
        """Test QC_FAIL path as specified in requirements."""
        qc_fail_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "qc_check"
            },
            "nodes": [
                {
                    "id": "qc_check",
                    "type": "decision",
                    "when": "qc.fundus_pass == true and qc.macula_view == true",
                    "goto_true": "continue",
                    "goto_false": "qc_fail"
                },
                {
                    "id": "qc_fail",
                    "type": "action",
                    "actions": [
                        {"type": "abstain", "reason": "insufficient image quality"}
                    ]
                },
                {
                    "id": "continue",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        qc_fail_case = {
            "qc": {"fundus_pass": False, "macula_view": True},
            "age": 65
        }
        
        actions, trace = execute(qc_fail_dsl, qc_fail_case)
        
        # Should have abstain action
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "abstain")
        self.assertEqual(actions[0]["reason"], "insufficient image quality")
    
    def test_abstain_on_missing_dr_grade(self):
        """Test ABSTAIN on missing dr_grade as specified in requirements."""
        missing_grade_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "grade_check"
            },
            "nodes": [
                {
                    "id": "grade_check",
                    "type": "decision",
                    "when": "dr_grade != null",
                    "goto_true": "continue",
                    "goto_false": "missing_grade"
                },
                {
                    "id": "missing_grade",
                    "type": "action",
                    "actions": [
                        {"type": "abstain", "reason": "diabetic retinopathy grade not available"}
                    ]
                },
                {
                    "id": "continue",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        missing_grade_case = {
            "dr_grade": None,
            "age": 65
        }
        
        actions, trace = execute(missing_grade_dsl, missing_grade_case)
        
        # Should have abstain action
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "abstain")
        self.assertEqual(actions[0]["reason"], "diabetic retinopathy grade not available")
    
    def test_dme_threshold_branch_flip(self):
        """Test DME threshold branch flip at 0.69 vs 0.70 as specified in requirements."""
        dme_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "dme_check"
            },
            "nodes": [
                {
                    "id": "dme_check",
                    "type": "decision",
                    "when": "macula.edema_prob >= 0.70",
                    "goto_true": "dme_referral",
                    "goto_false": "no_dme"
                },
                {
                    "id": "dme_referral",
                    "type": "action",
                    "actions": [
                        {"type": "order_test", "test_type": "OCT_macula"},
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "2-4_weeks"}
                    ]
                },
                {
                    "id": "no_dme",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        # Test 0.69 case (should go to no_dme)
        case_069 = {
            "macula": {"edema_prob": 0.69}
        }
        
        actions_069, trace_069 = execute(dme_dsl, case_069)
        self.assertEqual(len(actions_069), 1)
        self.assertEqual(actions_069[0]["type"], "set_followup")
        
        # Test 0.70 case (should go to dme_referral)
        case_070 = {
            "macula": {"edema_prob": 0.70}
        }
        
        actions_070, trace_070 = execute(dme_dsl, case_070)
        self.assertEqual(len(actions_070), 2)
        self.assertEqual(actions_070[0]["type"], "order_test")
        self.assertEqual(actions_070[1]["type"], "suggest_referral")
    
    def test_safety_stop_on_malformed_rules(self):
        """Test safety stop on malformed rule file."""
        malformed_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "invalid_node"
            },
            "nodes": [
                {
                    "id": "start",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(malformed_dsl, self.test_case)
        
        # Should have safety stop in trace
        safety_stop_found = any(
            entry.get("node") == "safety_stop" and entry.get("type") == "safety_stop"
            for entry in trace
        )
        self.assertTrue(safety_stop_found)
    
    def test_safety_stop_on_parse_error(self):
        """Test safety stop on parser error."""
        parse_error_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "parse_error_node"
            },
            "nodes": [
                {
                    "id": "parse_error_node",
                    "type": "decision",
                    "when": "invalid.field.reference",
                    "goto_true": "next"
                },
                {
                    "id": "next",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(parse_error_dsl, self.test_case)
        
        # Should have safety stop in trace
        safety_stop_found = any(
            entry.get("node") == "safety_stop" and entry.get("type") == "safety_stop"
            for entry in trace
        )
        self.assertTrue(safety_stop_found)
    
    def test_rule_hash_computation(self):
        """Test rule hash computation."""
        hash1 = canonicalize_and_hash(self.test_dsl)
        hash2 = canonicalize_and_hash(self.test_dsl)
        
        # Same DSL should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different DSL should produce different hash
        different_dsl = self.test_dsl.copy()
        different_dsl["meta"]["version"] = "2.0.0"
        hash3 = canonicalize_and_hash(different_dsl)
        self.assertNotEqual(hash1, hash3)
    
    def test_trace_includes_metadata(self):
        """Test that trace includes required metadata."""
        actions, trace = execute(self.test_dsl, self.test_case)
        
        for entry in trace:
            # Check required fields
            self.assertIn("node", entry)
            self.assertIn("type", entry)
            self.assertIn("profile", entry)
            self.assertIn("version", entry)
            self.assertIn("rule_hash", entry)
            self.assertIn("timestamp", entry)
            
            # Check metadata values
            self.assertEqual(entry["profile"], "test_profile")
            self.assertEqual(entry["version"], "1.0.0")
            self.assertIsInstance(entry["rule_hash"], str)
            self.assertIsInstance(entry["timestamp"], str)
    
    def test_citation_handling(self):
        """Test citation handling in trace."""
        cited_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "cited_node"
            },
            "nodes": [
                {
                    "id": "cited_node",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ],
                    "cite": ["AAO_DR_PPP", "AAO_DR_urgent_referral"]
                }
            ]
        }
        
        actions, trace = execute(cited_dsl, self.test_case)
        
        # Check that citations are included in trace
        cited_entry = trace[0]
        self.assertIn("cite", cited_entry)
        self.assertEqual(cited_entry["cite"], ["AAO_DR_PPP", "AAO_DR_urgent_referral"])
    
    def test_complex_workflow(self):
        """Test a complex multi-step workflow."""
        complex_dsl = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "qc_check"
            },
            "nodes": [
                {
                    "id": "qc_check",
                    "type": "decision",
                    "when": "qc.fundus_pass == true",
                    "goto_true": "grade_check",
                    "goto_false": "qc_fail"
                },
                {
                    "id": "qc_fail",
                    "type": "action",
                    "actions": [
                        {"type": "abstain", "reason": "QC failure"}
                    ]
                },
                {
                    "id": "grade_check",
                    "type": "decision",
                    "when": "dr_grade == 'pdr'",
                    "goto_true": "urgent_referral",
                    "goto_false": "moderate_check"
                },
                {
                    "id": "urgent_referral",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                },
                {
                    "id": "moderate_check",
                    "type": "decision",
                    "when": "dr_grade == 'moderate_npdr'",
                    "goto_true": "moderate_referral",
                    "goto_false": "followup"
                },
                {
                    "id": "moderate_referral",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "2-4_weeks"}
                    ]
                },
                {
                    "id": "followup",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        # Test PDR case
        pdr_case = {
            "qc": {"fundus_pass": True},
            "dr_grade": "pdr"
        }
        
        actions, trace = execute(complex_dsl, pdr_case)
        
        # Should have urgent referral
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "suggest_referral")
        self.assertEqual(actions[0]["urgency"], "urgent")
        
        # Should have multiple trace entries
        self.assertGreater(len(trace), 2)


if __name__ == '__main__':
    unittest.main()
