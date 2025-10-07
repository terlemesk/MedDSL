"""
Explanation generator for MedDSL decisions and traces.
"""

import json
from typing import Any, Dict, List, Optional, Callable
from .retrieval import SnippetRetriever


class ExplanationGenerator:
    """Generates explanations from case data, actions, and trace."""
    
    def __init__(self, retriever: SnippetRetriever = None):
        self.retriever = retriever or SnippetRetriever()
        self.llm_rewrite_func = None  # Will be set by user if LLM rewriting is desired
    
    def set_llm_rewrite_function(self, func: Callable[[str, str], str]):
        """Set the LLM rewrite function for prose generation."""
        self.llm_rewrite_func = func
    
    def explain(self, case: Dict[str, Any], actions: List[Dict[str, Any]], 
                trace: List[Dict[str, Any]], retriever: SnippetRetriever = None) -> Dict[str, Any]:
        """
        Generate explanation from case data, actions, and trace.
        
        Args:
            case: Case data dictionary
            actions: List of actions taken
            trace: Execution trace
            retriever: Optional snippet retriever (uses instance default if None)
            
        Returns:
            Dictionary containing explanation components
        """
        if retriever is None:
            retriever = self.retriever
        
        # Generate rule trace
        rule_trace = self._generate_rule_trace(trace)
        
        # Generate actions JSON (exact actions list)
        actions_json = actions
        
        # Generate citations
        citations = self._generate_citations(trace, retriever)
        
        # Generate prose (with optional LLM rewrite)
        prose = self._generate_prose(case, actions, trace, rule_trace, citations)
        
        return {
            "rule_trace": rule_trace,
            "actions_json": actions_json,
            "citations": citations,
            "prose": prose,
            "case_summary": self._generate_case_summary(case)
        }
    
    def _generate_rule_trace(self, trace: List[Dict[str, Any]]) -> List[str]:
        """Generate bullet-point rule trace from execution trace."""
        rule_trace = []
        
        for entry in trace:
            node_id = entry.get("node", "unknown")
            entry_type = entry.get("type", "unknown")
            outcome = entry.get("outcome")
            
            if entry_type == "decision":
                # Format decision outcomes
                if outcome == "true":
                    rule_trace.append(f"• {node_id}: condition was TRUE")
                elif outcome == "false":
                    rule_trace.append(f"• {node_id}: condition was FALSE")
                else:
                    rule_trace.append(f"• {node_id}: {outcome}")
            
            elif entry_type == "action":
                # Format action outcomes
                actions = entry.get("actions", [])
                if actions:
                    action_descriptions = []
                    for action in actions:
                        action_type = action.get("type", "unknown")
                        action_desc = self._format_action(action)
                        action_descriptions.append(action_desc)
                    
                    if action_descriptions:
                        rule_trace.append(f"• {node_id}: {', '.join(action_descriptions)}")
                else:
                    rule_trace.append(f"• {node_id}: no actions")
            
            elif entry_type == "safety_stop":
                # Format safety stops
                safety_reason = outcome or "unknown reason"
                rule_trace.append(f"• SAFETY STOP: {safety_reason}")
        
        return rule_trace
    
    def _format_action(self, action: Dict[str, Any]) -> str:
        """Format a single action for display."""
        action_type = action.get("type", "unknown")
        
        if action_type == "suggest_referral":
            specialty = action.get("specialty", "unknown")
            urgency = action.get("urgency", "routine")
            return f"refer to {specialty} ({urgency})"
        
        elif action_type == "order_test":
            test_type = action.get("test_type", "unknown")
            return f"order {test_type}"
        
        elif action_type == "set_followup":
            interval = action.get("interval", "unknown")
            return f"follow-up in {interval}"
        
        elif action_type == "abstain":
            reason = action.get("reason", "insufficient data")
            return f"abstain ({reason})"
        
        else:
            # Generic formatting for unknown action types
            return f"{action_type}: {json.dumps(action, separators=(',', ':'))}"
    
    def _generate_citations(self, trace: List[Dict[str, Any]], retriever: SnippetRetriever) -> List[str]:
        """Generate citations from trace cite IDs."""
        citation_ids = set()
        
        # Collect all citation IDs from trace
        for entry in trace:
            cite_ids = entry.get("cite", [])
            citation_ids.update(cite_ids)
        
        # Retrieve citation snippets
        citations = []
        for cite_id in citation_ids:
            snippet = retriever.get_snippet(cite_id)
            if snippet and 'short_quote' in snippet:
                source = snippet.get('source', 'Unknown source')
                quote = snippet['short_quote']
                citations.append(f"{source}: {quote}")
        
        # Limit to 2-3 citations as specified
        return citations[:3]
    
    def _generate_prose(self, case: Dict[str, Any], actions: List[Dict[str, Any]], 
                       trace: List[Dict[str, Any]], rule_trace: List[str], 
                       citations: List[str]) -> str:
        """Generate prose explanation with optional LLM rewrite."""
        
        # Create template prose
        template = self._create_template_prose(case, actions, rule_trace, citations)
        
        # Apply LLM rewrite if function is available
        if self.llm_rewrite_func:
            try:
                return self.llm_rewrite_func(template, "clinician")
            except Exception as e:
                # Fall back to template if LLM rewrite fails
                print(f"Warning: LLM rewrite failed: {e}")
                return template
        
        return template
    
    def _create_template_prose(self, case: Dict[str, Any], actions: List[Dict[str, Any]], 
                              rule_trace: List[str], citations: List[str]) -> str:
        """Create template prose without LLM rewriting."""
        
        # Case summary
        eye = case.get("eye", "unknown")
        age = case.get("age", "unknown")
        dr_grade = case.get("dr_grade", "unknown")
        vision_reduced = case.get("vision_reduced", False)
        
        case_desc = f"Case: {eye} eye, age {age}, DR grade {dr_grade}"
        if vision_reduced:
            case_desc += ", vision reduced"
        
        # Action summary
        if actions:
            action_summaries = []
            for action in actions:
                action_summaries.append(self._format_action(action))
            action_text = "; ".join(action_summaries)
        else:
            action_text = "no actions recommended"
        
        # Combine into prose
        prose_parts = [
            f"Based on the clinical data ({case_desc}), the following recommendation is made: {action_text}.",
            "",
            "Rule trace:",
            *[f"  {bullet}" for bullet in rule_trace]
        ]
        
        if citations:
            prose_parts.extend([
                "",
                "Citations:",
                *[f"  {citation}" for citation in citations]
            ])
        
        return "\n".join(prose_parts)
    
    def _generate_case_summary(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the case data."""
        return {
            "eye": case.get("eye"),
            "age": case.get("age"),
            "vision_reduced": case.get("vision_reduced"),
            "dr_grade": case.get("dr_grade"),
            "edema_prob": case.get("macula", {}).get("edema_prob"),
            "qc_status": {
                "fundus_pass": case.get("qc", {}).get("fundus_pass"),
                "macula_view": case.get("qc", {}).get("macula_view")
            }
        }


def llm_rewrite_stub(text: str, style: str = "clinician") -> str:
    """Stub function for LLM rewriting."""
    # This is a placeholder - in practice, this would call an actual LLM
    # For now, just return the input text
    return text


def explain(case: Dict[str, Any], actions: List[Dict[str, Any]], 
           trace: List[Dict[str, Any]], retriever: SnippetRetriever = None) -> Dict[str, Any]:
    """
    Generate explanation from case data, actions, and trace.
    
    Args:
        case: Case data dictionary
        actions: List of actions taken
        trace: Execution trace
        retriever: Optional snippet retriever
        
    Returns:
        Dictionary containing explanation components
    """
    generator = ExplanationGenerator(retriever)
    return generator.explain(case, actions, trace, retriever)


def explain_with_llm(case: Dict[str, Any], actions: List[Dict[str, Any]], 
                    trace: List[Dict[str, Any]], llm_func: Callable[[str, str], str],
                    retriever: SnippetRetriever = None) -> Dict[str, Any]:
    """
    Generate explanation with LLM rewriting.
    
    Args:
        case: Case data dictionary
        actions: List of actions taken
        trace: Execution trace
        llm_func: Function for LLM rewriting (text, style) -> rewritten_text
        retriever: Optional snippet retriever
        
    Returns:
        Dictionary containing explanation components
    """
    generator = ExplanationGenerator(retriever)
    generator.set_llm_rewrite_function(llm_func)
    return generator.explain(case, actions, trace, retriever)
