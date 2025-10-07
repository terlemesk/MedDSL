"""
DSL interpreter with tracing and safety mechanisms.
"""

import hashlib
import json
import yaml
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from .dsl_parser import eval_expr, ParseError


class InterpreterError(Exception):
    """Raised when interpretation fails."""
    pass


class TraceEntry:
    """Represents a single trace entry."""
    
    def __init__(self, node_id: str, node_type: str, outcome: Optional[str] = None, 
                 actions: Optional[List[Dict]] = None, cite: Optional[List[str]] = None,
                 profile: str = "", version: str = "", rule_hash: str = "", timestamp: str = ""):
        self.node_id = node_id
        self.node_type = node_type
        self.outcome = outcome
        self.actions = actions or []
        self.cite = cite or []
        self.profile = profile
        self.version = version
        self.rule_hash = rule_hash
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node": self.node_id,
            "type": self.node_type,
            "outcome": self.outcome,
            "actions": self.actions,
            "cite": self.cite,
            "profile": self.profile,
            "version": self.version,
            "rule_hash": self.rule_hash,
            "timestamp": self.timestamp
        }


def canonicalize_and_hash(dsl_dict: Dict[str, Any]) -> str:
    """Canonicalize DSL dictionary and compute SHA-256 hash."""
    # Create a deep copy and sort keys recursively
    canonical = canonicalize_dict(dsl_dict)
    
    # Convert to JSON string with sorted keys
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
    
    # Compute hash
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def canonicalize_dict(obj: Any) -> Any:
    """Recursively canonicalize a dictionary by sorting keys."""
    if isinstance(obj, dict):
        return {k: canonicalize_dict(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [canonicalize_dict(item) for item in obj]
    else:
        return obj


class DSLInterpreter:
    """Interpreter for MedDSL rules."""
    
    def __init__(self):
        self.rule_hash = ""
        self.profile = ""
        self.version = ""
    
    def validate_node_structure(self, node: Dict[str, Any]) -> None:
        """Validate that a node has the required structure."""
        if "id" not in node:
            raise InterpreterError("Node missing required 'id' field")
        
        if "type" not in node:
            raise InterpreterError(f"Node {node['id']} missing required 'type' field")
        
        node_type = node["type"]
        if node_type not in ["decision", "action"]:
            raise InterpreterError(f"Node {node['id']} has invalid type: {node_type}")
        
        if node_type == "decision":
            if "when" not in node:
                raise InterpreterError(f"Decision node {node['id']} missing 'when' condition")
            if "actions" in node:
                raise InterpreterError(f"Decision node {node['id']} should not have 'actions' field")
        elif node_type == "action":
            if "actions" not in node:
                raise InterpreterError(f"Action node {node['id']} missing 'actions' field")
            if "when" in node:
                raise InterpreterError(f"Action node {node['id']} should not have 'when' field")
    
    def get_node_by_id(self, nodes: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
        """Find a node by its ID."""
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None
    
    def evaluate_condition(self, condition: str, case: Dict[str, Any]) -> bool:
        """Evaluate a boolean condition."""
        try:
            return eval_expr(condition, case)
        except ParseError as e:
            raise InterpreterError(f"Failed to evaluate condition '{condition}': {e}")
        except Exception as e:
            raise InterpreterError(f"Unexpected error evaluating condition '{condition}': {e}")
    
    def execute_node(self, node: Dict[str, Any], case: Dict[str, Any]) -> Tuple[List[Dict], Optional[str]]:
        """Execute a single node and return actions and next node ID."""
        node_id = node["id"]
        node_type = node["type"]
        actions = []
        next_node = None
        
        if node_type == "decision":
            condition = node["when"]
            outcome = self.evaluate_condition(condition, case)
            
            # Add trace entry for decision
            trace_entry = TraceEntry(
                node_id=node_id,
                node_type=node_type,
                outcome="true" if outcome else "false",
                cite=node.get("cite", []),
                profile=self.profile,
                version=self.version,
                rule_hash=self.rule_hash,
                timestamp=datetime.now().isoformat()
            )
            
            # Determine next node based on outcome
            if outcome and "goto_true" in node:
                next_node = node["goto_true"]
            elif not outcome and "goto_false" in node:
                next_node = node["goto_false"]
            elif "next" in node:
                next_node = node["next"]
            
            return actions, next_node, trace_entry
        
        elif node_type == "action":
            actions = node.get("actions", [])
            
            # Add trace entry for action
            trace_entry = TraceEntry(
                node_id=node_id,
                node_type=node_type,
                actions=actions,
                cite=node.get("cite", []),
                profile=self.profile,
                version=self.version,
                rule_hash=self.rule_hash,
                timestamp=datetime.now().isoformat()
            )
            
            # Determine next node
            if "next" in node:
                next_node = node["next"]
            
            return actions, next_node, trace_entry
        
        return actions, next_node, None


def execute(dsl: Dict[str, Any], case: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    """
    Execute DSL rules on a case and return actions and trace.
    
    Args:
        dsl: DSL dictionary with meta and nodes
        case: Case data dictionary
        
    Returns:
        Tuple of (actions_list, trace_list)
    """
    interpreter = DSLInterpreter()
    
    # Extract metadata
    meta = dsl.get("meta", {})
    interpreter.profile = meta.get("profile", "")
    interpreter.version = meta.get("version", "")
    interpreter.rule_hash = canonicalize_and_hash(dsl)
    
    # Get nodes
    nodes = dsl.get("nodes", [])
    if not nodes:
        raise InterpreterError("No nodes found in DSL")
    
    # Validate all nodes
    node_ids = set()
    for node in nodes:
        interpreter.validate_node_structure(node)
        
        # Check for duplicate IDs
        node_id = node["id"]
        if node_id in node_ids:
            raise InterpreterError(f"Duplicate node ID: {node_id}")
        node_ids.add(node_id)
    
    # Find entry point
    entry_node_id = meta.get("entry")
    if entry_node_id:
        current_node = interpreter.get_node_by_id(nodes, entry_node_id)
        if not current_node:
            raise InterpreterError(f"Entry node '{entry_node_id}' not found")
    else:
        # Use first node as entry point
        current_node = nodes[0]
    
    # Execute nodes
    all_actions = []
    trace = []
    visited_nodes = set()
    max_iterations = 100  # Safety limit to prevent infinite loops
    
    for iteration in range(max_iterations):
        if current_node is None:
            break
        
        current_node_id = current_node["id"]
        
        # Check for cycles
        if current_node_id in visited_nodes:
            # Add safety stop trace entry
            safety_entry = TraceEntry(
                node_id="safety_stop",
                node_type="safety_stop",
                outcome="cycle_detected",
                profile=interpreter.profile,
                version=interpreter.version,
                rule_hash=interpreter.rule_hash,
                timestamp=datetime.now().isoformat()
            )
            trace.append(safety_entry.to_dict())
            break
        
        visited_nodes.add(current_node_id)
        
        try:
            actions, next_node_id, trace_entry = interpreter.execute_node(current_node, case)
            
            # Add actions to total
            all_actions.extend(actions)
            
            # Add trace entry
            if trace_entry:
                trace.append(trace_entry.to_dict())
            
            # Move to next node
            if next_node_id:
                current_node = interpreter.get_node_by_id(nodes, next_node_id)
                if not current_node:
                    # Add safety stop for missing node
                    safety_entry = TraceEntry(
                        node_id="safety_stop",
                        node_type="safety_stop",
                        outcome="missing_node",
                        profile=interpreter.profile,
                        version=interpreter.version,
                        rule_hash=interpreter.rule_hash,
                        timestamp=datetime.now().isoformat()
                    )
                    trace.append(safety_entry.to_dict())
                    break
            else:
                # No next node, execution complete
                break
                
        except InterpreterError as e:
            # Add safety stop for interpreter error
            safety_entry = TraceEntry(
                node_id="safety_stop",
                node_type="safety_stop",
                outcome="interpreter_error",
                profile=interpreter.profile,
                version=interpreter.version,
                rule_hash=interpreter.rule_hash,
                timestamp=datetime.now().isoformat()
            )
            safety_entry.outcome = f"interpreter_error: {str(e)}"
            trace.append(safety_entry.to_dict())
            break
        except Exception as e:
            # Add safety stop for unexpected error
            safety_entry = TraceEntry(
                node_id="safety_stop",
                node_type="safety_stop",
                outcome="unexpected_error",
                profile=interpreter.profile,
                version=interpreter.version,
                rule_hash=interpreter.rule_hash,
                timestamp=datetime.now().isoformat()
            )
            safety_entry.outcome = f"unexpected_error: {str(e)}"
            trace.append(safety_entry.to_dict())
            break
    
    if iteration >= max_iterations - 1:
        # Add safety stop for max iterations
        safety_entry = TraceEntry(
            node_id="safety_stop",
            node_type="safety_stop",
            outcome="max_iterations_exceeded",
            profile=interpreter.profile,
            version=interpreter.version,
            rule_hash=interpreter.rule_hash,
            timestamp=datetime.now().isoformat()
        )
        trace.append(safety_entry.to_dict())
    
    return all_actions, trace


def load_dsl_from_yaml(yaml_content: str) -> Dict[str, Any]:
    """Load DSL from YAML string."""
    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise InterpreterError(f"Invalid YAML: {e}")


def load_dsl_from_file(file_path: str) -> Dict[str, Any]:
    """Load DSL from YAML file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return load_dsl_from_yaml(content)
    except FileNotFoundError:
        raise InterpreterError(f"File not found: {file_path}")
    except Exception as e:
        raise InterpreterError(f"Error reading file {file_path}: {e}")
