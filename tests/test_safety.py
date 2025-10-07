"""
Unit tests for safety mechanisms in MedDSL.
"""

import unittest
from mddsl.interpreter import execute, InterpreterError
from mddsl.dsl_parser import ParseError


class TestSafety(unittest.TestCase):
    """Test cases for safety mechanisms."""
    
    def setUp(self):
        """Set up test data."""
        self.test_case = {
            "age": 65,
            "vision_reduced": True,
            "dr_grade": "moderate_npdr",
            "qc": {"fundus_pass": True, "macula_view": True},
            "macula": {"edema_prob": 0.75}
        }
    
    def test_safety_stop_on_missing_entry_node(self):
        """Test safety stop when entry node is missing."""
        dsl_missing_entry = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "nonexistent_node"
            },
            "nodes": [
                {
                    "id": "existing_node",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_missing_entry, self.test_case)
        
        # Should have safety stop
        safety_stop_found = any(
            entry.get("node") == "safety_stop" and entry.get("type") == "safety_stop"
            for entry in trace
        )
        self.assertTrue(safety_stop_found)
        
        # Should have no actions
        self.assertEqual(len(actions), 0)
    
    def test_safety_stop_on_parse_error(self):
        """Test safety stop on parser error in condition."""
        dsl_parse_error = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "parse_error_node"
            },
            "nodes": [
                {
                    "id": "parse_error_node",
                    "type": "decision",
                    "when": "invalid.field.reference == true",
                    "goto_true": "next_node"
                },
                {
                    "id": "next_node",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_parse_error, self.test_case)
        
        # Should have safety stop with interpreter_error
        safety_stop_found = any(
            entry.get("node") == "safety_stop" and 
            entry.get("type") == "safety_stop" and
            "interpreter_error" in str(entry.get("outcome", ""))
            for entry in trace
        )
        self.assertTrue(safety_stop_found)
    
    def test_safety_stop_on_cycle_detection(self):
        """Test safety stop on cycle detection."""
        dsl_with_cycle = {
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
                    "goto_true": "middle",
                    "goto_false": "end"
                },
                {
                    "id": "middle",
                    "type": "decision",
                    "when": "vision_reduced == true",
                    "goto_true": "start",  # Creates cycle
                    "goto_false": "end"
                },
                {
                    "id": "end",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_with_cycle, self.test_case)
        
        # Should have safety stop for cycle
        cycle_stop_found = any(
            entry.get("node") == "safety_stop" and 
            entry.get("type") == "safety_stop" and
            "cycle_detected" in str(entry.get("outcome", ""))
            for entry in trace
        )
        self.assertTrue(cycle_stop_found)
    
    def test_safety_stop_on_max_iterations(self):
        """Test safety stop when max iterations exceeded."""
        dsl_long_chain = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "start"
            },
            "nodes": []
        }
        
        # Create a very long chain of nodes (more than max_iterations)
        for i in range(150):  # Max iterations is 100
            node = {
                "id": f"node_{i}",
                "type": "decision",
                "when": "age > 0",  # Always true
                "goto_true": f"node_{i+1}" if i < 149 else "end"
            }
            dsl_long_chain["nodes"].append(node)
        
        # Add end node
        dsl_long_chain["nodes"].append({
            "id": "end",
            "type": "action",
            "actions": [
                {"type": "set_followup", "interval": "12m"}
            ]
        })
        
        actions, trace = execute(dsl_long_chain, self.test_case)
        
        # Should have safety stop for max iterations
        max_iter_stop_found = any(
            entry.get("node") == "safety_stop" and 
            entry.get("type") == "safety_stop" and
            "max_iterations_exceeded" in str(entry.get("outcome", ""))
            for entry in trace
        )
        self.assertTrue(max_iter_stop_found)
    
    def test_safety_stop_on_missing_next_node(self):
        """Test safety stop when next node is missing."""
        dsl_missing_next = {
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
                    "goto_true": "missing_node",
                    "goto_false": "end"
                },
                {
                    "id": "end",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_missing_next, self.test_case)
        
        # Should have safety stop for missing node
        missing_node_stop_found = any(
            entry.get("node") == "safety_stop" and 
            entry.get("type") == "safety_stop" and
            "missing_node" in str(entry.get("outcome", ""))
            for entry in trace
        )
        self.assertTrue(missing_node_stop_found)
    
    def test_safety_stop_preserves_partial_trace(self):
        """Test that safety stops preserve partial execution trace."""
        dsl_with_error = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "start"
            },
            "nodes": [
                {
                    "id": "start",
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ],
                    "next": "error_node"
                },
                {
                    "id": "error_node",
                    "type": "decision",
                    "when": "invalid.field.reference == true",
                    "goto_true": "end"
                },
                {
                    "id": "end",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_with_error, self.test_case)
        
        # Should have the initial action
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "suggest_referral")
        
        # Should have trace entries including safety stop
        self.assertGreater(len(trace), 1)
        
        # Should have start node trace entry
        start_trace_found = any(
            entry.get("node") == "start" for entry in trace
        )
        self.assertTrue(start_trace_found)
        
        # Should have safety stop
        safety_stop_found = any(
            entry.get("node") == "safety_stop" for entry in trace
        )
        self.assertTrue(safety_stop_found)
    
    def test_safety_stop_error_details(self):
        """Test that safety stops include detailed error information."""
        dsl_with_error = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "error_node"
            },
            "nodes": [
                {
                    "id": "error_node",
                    "type": "decision",
                    "when": "nonexistent.field == true",
                    "goto_true": "end"
                },
                {
                    "id": "end",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_with_error, self.test_case)
        
        # Find safety stop entry
        safety_stop = None
        for entry in trace:
            if entry.get("node") == "safety_stop":
                safety_stop = entry
                break
        
        self.assertIsNotNone(safety_stop)
        self.assertEqual(safety_stop["type"], "safety_stop")
        self.assertIn("interpreter_error", str(safety_stop.get("outcome", "")))
        self.assertIn("nonexistent.field", str(safety_stop.get("outcome", "")))
    
    def test_graceful_handling_of_invalid_node_structure(self):
        """Test graceful handling of nodes with invalid structure."""
        dsl_invalid_structure = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "start"
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
        
        # This should work fine - valid structure
        actions, trace = execute(dsl_invalid_structure, self.test_case)
        self.assertEqual(len(actions), 1)
        
        # Test with missing required fields
        dsl_missing_id = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "start"
            },
            "nodes": [
                {
                    "type": "action",
                    "actions": [
                        {"type": "suggest_referral", "specialty": "retina", "urgency": "urgent"}
                    ]
                }
            ]
        }
        
        # Should raise InterpreterError during validation
        with self.assertRaises(InterpreterError):
            execute(dsl_missing_id, self.test_case)
    
    def test_safety_stop_includes_metadata(self):
        """Test that safety stops include proper metadata."""
        dsl_with_error = {
            "meta": {
                "profile": "test_profile",
                "version": "1.0.0",
                "entry": "error_node"
            },
            "nodes": [
                {
                    "id": "error_node",
                    "type": "decision",
                    "when": "invalid.field == true",
                    "goto_true": "end"
                },
                {
                    "id": "end",
                    "type": "action",
                    "actions": [
                        {"type": "set_followup", "interval": "12m"}
                    ]
                }
            ]
        }
        
        actions, trace = execute(dsl_with_error, self.test_case)
        
        # Find safety stop entry
        safety_stop = None
        for entry in trace:
            if entry.get("node") == "safety_stop":
                safety_stop = entry
                break
        
        self.assertIsNotNone(safety_stop)
        
        # Check metadata
        self.assertEqual(safety_stop["profile"], "test_profile")
        self.assertEqual(safety_stop["version"], "1.0.0")
        self.assertIn("rule_hash", safety_stop)
        self.assertIn("timestamp", safety_stop)
        self.assertIsInstance(safety_stop["rule_hash"], str)
        self.assertIsInstance(safety_stop["timestamp"], str)


if __name__ == '__main__':
    unittest.main()
