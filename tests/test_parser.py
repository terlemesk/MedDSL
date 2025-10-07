"""
Unit tests for the DSL parser.
"""

import unittest
from mddsl.dsl_parser import parse, eval_expr, ParseError


class TestParser(unittest.TestCase):
    """Test cases for the DSL parser."""
    
    def setUp(self):
        """Set up test case data."""
        self.test_case = {
            "eye": "OD",
            "age": 62,
            "vision_reduced": True,
            "qc": {
                "fundus_pass": True,
                "macula_view": True
            },
            "dr_grade": "severe_npdr",
            "macula": {
                "edema_prob": 0.35
            }
        }
    
    def test_literals(self):
        """Test parsing of literal values."""
        self.assertTrue(eval_expr("true", {}))
        self.assertFalse(eval_expr("false", {}))
        self.assertIsNone(eval_expr("null", {}))
        self.assertEqual(eval_expr("42", {}), 42)
        self.assertEqual(eval_expr("3.14", {}), 3.14)
    
    def test_field_references(self):
        """Test parsing of field references."""
        self.assertEqual(eval_expr("age", self.test_case), 62)
        self.assertEqual(eval_expr("eye", self.test_case), "OD")
        self.assertTrue(eval_expr("vision_reduced", self.test_case))
        self.assertEqual(eval_expr("dr_grade", self.test_case), "severe_npdr")
    
    def test_dotted_field_references(self):
        """Test parsing of dotted field references."""
        self.assertTrue(eval_expr("qc.fundus_pass", self.test_case))
        self.assertTrue(eval_expr("qc.macula_view", self.test_case))
        self.assertEqual(eval_expr("macula.edema_prob", self.test_case), 0.35)
    
    def test_comparison_operators(self):
        """Test comparison operators."""
        # Equality
        self.assertTrue(eval_expr("age == 62", self.test_case))
        self.assertFalse(eval_expr("age == 30", self.test_case))
        self.assertTrue(eval_expr("dr_grade == 'severe_npdr'", self.test_case))
        
        # Inequality
        self.assertFalse(eval_expr("age != 62", self.test_case))
        self.assertTrue(eval_expr("age != 30", self.test_case))
        
        # Greater than/less than
        self.assertTrue(eval_expr("age > 60", self.test_case))
        self.assertFalse(eval_expr("age > 70", self.test_case))
        self.assertTrue(eval_expr("age < 70", self.test_case))
        self.assertFalse(eval_expr("age < 60", self.test_case))
        
        # Greater than or equal/less than or equal
        self.assertTrue(eval_expr("age >= 62", self.test_case))
        self.assertTrue(eval_expr("age >= 60", self.test_case))
        self.assertFalse(eval_expr("age >= 70", self.test_case))
        self.assertTrue(eval_expr("age <= 62", self.test_case))
        self.assertTrue(eval_expr("age <= 70", self.test_case))
        self.assertFalse(eval_expr("age <= 60", self.test_case))
    
    def test_logical_operators(self):
        """Test logical operators."""
        # AND
        self.assertTrue(eval_expr("age > 60 and vision_reduced == true", self.test_case))
        self.assertFalse(eval_expr("age > 60 and vision_reduced == false", self.test_case))
        self.assertFalse(eval_expr("age < 60 and vision_reduced == true", self.test_case))
        
        # OR
        self.assertTrue(eval_expr("age > 60 or vision_reduced == false", self.test_case))
        self.assertTrue(eval_expr("age < 60 or vision_reduced == true", self.test_case))
        self.assertFalse(eval_expr("age < 60 or vision_reduced == false", self.test_case))
        
        # NOT
        self.assertFalse(eval_expr("not vision_reduced", self.test_case))
        self.assertTrue(eval_expr("not (age < 60)", self.test_case))
    
    def test_operator_precedence(self):
        """Test operator precedence."""
        # NOT should have higher precedence than comparisons
        self.assertTrue(eval_expr("not age > 70", self.test_case))
        self.assertFalse(eval_expr("not age > 60", self.test_case))
        
        # Comparisons should have higher precedence than AND/OR
        self.assertTrue(eval_expr("age > 60 and age < 70", self.test_case))
        self.assertTrue(eval_expr("age > 50 or age < 40", self.test_case))
        
        # AND should have higher precedence than OR
        self.assertTrue(eval_expr("age > 50 or age < 40 and vision_reduced == true", self.test_case))
    
    def test_parentheses(self):
        """Test parentheses for grouping."""
        self.assertTrue(eval_expr("(age > 60) and (vision_reduced == true)", self.test_case))
        self.assertTrue(eval_expr("((age > 60) and (vision_reduced == true))", self.test_case))
        self.assertFalse(eval_expr("(age > 60) and (vision_reduced == false)", self.test_case))
    
    def test_null_comparisons(self):
        """Test null comparison semantics."""
        null_case = {
            "field1": None,
            "field2": 42,
            "field3": None
        }
        
        # Equality with null
        self.assertTrue(eval_expr("field1 == null", null_case))
        self.assertFalse(eval_expr("field2 == null", null_case))
        self.assertTrue(eval_expr("field1 == field3", null_case))
        
        # Inequality with null
        self.assertFalse(eval_expr("field1 != null", null_case))
        self.assertTrue(eval_expr("field2 != null", null_case))
        self.assertFalse(eval_expr("field1 != field3", null_case))
        
        # Other comparisons with null should be False
        self.assertFalse(eval_expr("field1 > 0", null_case))
        self.assertFalse(eval_expr("field1 < 0", null_case))
        self.assertFalse(eval_expr("field1 >= 0", null_case))
        self.assertFalse(eval_expr("field1 <= 0", null_case))
    
    def test_complex_expressions(self):
        """Test complex expressions."""
        self.assertTrue(eval_expr("qc.fundus_pass == true and qc.macula_view == true", self.test_case))
        self.assertFalse(eval_expr("dr_grade == 'pdr' or dr_grade == 'severe_npdr'", self.test_case))
        self.assertTrue(eval_expr("macula.edema_prob >= 0.30 and macula.edema_prob <= 0.40", self.test_case))
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Empty expressions should raise ParseError
        with self.assertRaises(ParseError):
            eval_expr("", {})
        
        # Invalid tokens should raise ParseError
        with self.assertRaises(ParseError):
            eval_expr("invalid_token", {})
        
        # Missing field should raise ParseError
        with self.assertRaises(ParseError):
            eval_expr("missing.field", {})
        
        # Unclosed parentheses should raise ParseError
        with self.assertRaises(ParseError):
            eval_expr("(age > 60", {})
        
        # Extra closing parentheses should raise ParseError
        with self.assertRaises(ParseError):
            eval_expr("age > 60)", {})
    
    def test_parse_function(self):
        """Test the parse function returns AST."""
        ast = parse("age > 60 and vision_reduced == true")
        self.assertIsNotNone(ast)
        
        # Test that the AST can be evaluated
        result = ast.eval(self.test_case)
        self.assertTrue(result)
    
    def test_threshold_edge_cases(self):
        """Test threshold edge cases as specified in requirements."""
        edge_case = {
            "macula": {"edema_prob": 0.69}
        }
        
        # Test 0.69 threshold (should be false for >= 0.70)
        self.assertFalse(eval_expr("macula.edema_prob >= 0.70", edge_case))
        
        edge_case = {
            "macula": {"edema_prob": 0.70}
        }
        
        # Test 0.70 threshold (should be true for >= 0.70)
        self.assertTrue(eval_expr("macula.edema_prob >= 0.70", edge_case))


if __name__ == '__main__':
    unittest.main()
