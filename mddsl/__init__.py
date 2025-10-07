"""
MedDSL-Lite: Medical Domain Specific Language for Diabetic Retinopathy Triage
"""

__version__ = "0.1.0"
__author__ = "MedDSL Team"

from .dsl_parser import parse, eval_expr, ParseError
from .interpreter import execute
from .validator import validate_case, lint_rules
from .explainer import explain
from .retrieval import SnippetRetriever

__all__ = [
    "parse",
    "eval_expr", 
    "ParseError",
    "execute",
    "validate_case",
    "lint_rules",
    "explain",
    "SnippetRetriever"
]
