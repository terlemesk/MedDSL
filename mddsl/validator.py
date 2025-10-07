"""
Validators for case data and DSL rules.
"""

import json
import os
from typing import Any, Dict, List, Set, Tuple
import jsonschema
from jsonschema import Draft7Validator


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class CaseValidator:
    """Validates case data against schema."""
    
    def __init__(self, schema_path: str = None):
        if schema_path is None:
            # Default to schema in same directory
            current_dir = os.path.dirname(__file__)
            schema_path = os.path.join(current_dir, "case_schema.json")
        
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValidationError(f"Schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in schema file: {e}")
    
    def validate_case(self, case: Dict[str, Any]) -> List[str]:
        """
        Validate a case against the schema.
        
        Args:
            case: Case data dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Validate against schema
            validation_errors = list(self.validator.iter_errors(case))
            for error in validation_errors:
                path = '.'.join(str(p) for p in error.path) if error.path else 'root'
                errors.append(f"{path}: {error.message}")
        except Exception as e:
            errors.append(f"Schema validation failed: {e}")
        
        return errors


class DSLValidator:
    """Validates DSL rules for correctness and safety."""
    
    def __init__(self, schema_path: str = None):
        if schema_path is None:
            # Default to schema in same directory
            current_dir = os.path.dirname(__file__)
            schema_path = os.path.join(current_dir, "rules_schema.json")
        
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValidationError(f"Schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in schema file: {e}")
    
    def lint_rules(self, dsl: Dict[str, Any]) -> List[str]:
        """
        Lint DSL rules for common issues.
        
        Args:
            dsl: DSL dictionary
            
        Returns:
            List of warning/error messages
        """
        warnings = []
        
        try:
            # Validate against schema first
            schema_errors = list(self.validator.iter_errors(dsl))
            for error in schema_errors:
                path = '.'.join(str(p) for p in error.path) if error.path else 'root'
                warnings.append(f"SCHEMA_ERROR: {path}: {error.message}")
        except Exception as e:
            warnings.append(f"SCHEMA_ERROR: Schema validation failed: {e}")
        
        # Additional linting checks
        warnings.extend(self._check_duplicate_ids(dsl))
        warnings.extend(self._check_missing_nodes(dsl))
        warnings.extend(self._check_unreachable_nodes(dsl))
        warnings.extend(self._check_cycles(dsl))
        warnings.extend(self._check_action_consistency(dsl))
        warnings.extend(self._check_node_structure(dsl))
        
        return warnings
    
    def _check_duplicate_ids(self, dsl: Dict[str, Any]) -> List[str]:
        """Check for duplicate node IDs."""
        warnings = []
        nodes = dsl.get("nodes", [])
        ids = []
        
        for node in nodes:
            node_id = node.get("id")
            if node_id in ids:
                warnings.append(f"DUPLICATE_ID: Duplicate node ID '{node_id}'")
            ids.append(node_id)
        
        return warnings
    
    def _check_missing_nodes(self, dsl: Dict[str, Any]) -> List[str]:
        """Check for references to missing nodes."""
        warnings = []
        nodes = dsl.get("nodes", [])
        meta = dsl.get("meta", {})
        
        # Build set of valid node IDs
        valid_ids = {node.get("id") for node in nodes if "id" in node}
        
        # Check entry node
        entry_node = meta.get("entry")
        if entry_node and entry_node not in valid_ids:
            warnings.append(f"MISSING_NODE: Entry node '{entry_node}' not found")
        
        # Check all node references
        for node in nodes:
            node_id = node.get("id", "unknown")
            
            # Check next references
            if "next" in node:
                next_id = node["next"]
                if next_id not in valid_ids:
                    warnings.append(f"MISSING_NODE: Node '{node_id}' references missing next node '{next_id}'")
            
            # Check goto references
            if "goto_true" in node:
                goto_id = node["goto_true"]
                if goto_id not in valid_ids:
                    warnings.append(f"MISSING_NODE: Node '{node_id}' references missing goto_true node '{goto_id}'")
            
            if "goto_false" in node:
                goto_id = node["goto_false"]
                if goto_id not in valid_ids:
                    warnings.append(f"MISSING_NODE: Node '{node_id}' references missing goto_false node '{goto_id}'")
        
        return warnings
    
    def _check_unreachable_nodes(self, dsl: Dict[str, Any]) -> List[str]:
        """Check for unreachable nodes."""
        warnings = []
        nodes = dsl.get("nodes", [])
        meta = dsl.get("meta", {})
        
        if not nodes:
            return warnings
        
        # Build graph of node references
        graph = {}
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                graph[node_id] = []
                
                if "next" in node:
                    graph[node_id].append(node["next"])
                if "goto_true" in node:
                    graph[node_id].append(node["goto_true"])
                if "goto_false" in node:
                    graph[node_id].append(node["goto_false"])
        
        # Find reachable nodes starting from entry
        reachable = set()
        entry_node = meta.get("entry")
        
        if entry_node and entry_node in graph:
            self._dfs_reachable(graph, entry_node, reachable)
        elif nodes:
            # If no entry specified, start from first node
            first_node = nodes[0].get("id")
            if first_node:
                self._dfs_reachable(graph, first_node, reachable)
        
        # Check for unreachable nodes
        all_node_ids = set(node.get("id") for node in nodes if "id" in node)
        unreachable = all_node_ids - reachable
        
        for node_id in unreachable:
            warnings.append(f"UNREACHABLE_NODE: Node '{node_id}' is unreachable from entry point")
        
        return warnings
    
    def _dfs_reachable(self, graph: Dict[str, List[str]], start: str, reachable: Set[str]):
        """DFS to find reachable nodes."""
        if start in reachable:
            return
        
        reachable.add(start)
        if start in graph:
            for neighbor in graph[start]:
                self._dfs_reachable(graph, neighbor, reachable)
    
    def _check_cycles(self, dsl: Dict[str, Any]) -> List[str]:
        """Check for cycles in the node graph."""
        warnings = []
        nodes = dsl.get("nodes", [])
        
        if not nodes:
            return warnings
        
        # Build graph
        graph = {}
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                graph[node_id] = []
                
                if "next" in node:
                    graph[node_id].append(node["next"])
                if "goto_true" in node:
                    graph[node_id].append(node["goto_true"])
                if "goto_false" in node:
                    graph[node_id].append(node["goto_false"])
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        for node_id in graph:
            if node_id not in visited:
                cycle = self._dfs_cycle(graph, node_id, visited, rec_stack, [])
                if cycle:
                    warnings.append(f"CYCLE_DETECTED: Cycle found: {' -> '.join(cycle)}")
        
        return warnings
    
    def _dfs_cycle(self, graph: Dict[str, List[str]], node: str, visited: Set[str], 
                   rec_stack: Set[str], path: List[str]) -> List[str]:
        """DFS to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        if node in graph:
            for neighbor in graph[node]:
                if neighbor not in visited:
                    cycle = self._dfs_cycle(graph, neighbor, visited, rec_stack, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
        
        rec_stack.remove(node)
        path.pop()
        return []
    
    def _check_action_consistency(self, dsl: Dict[str, Any]) -> List[str]:
        """Check for consistency in action definitions."""
        warnings = []
        nodes = dsl.get("nodes", [])
        
        # Valid action types (can be expanded)
        valid_action_types = {
            "suggest_referral", "order_test", "set_followup", "abstain"
        }
        
        for node in nodes:
            node_id = node.get("id", "unknown")
            node_type = node.get("type")
            
            if node_type == "action":
                actions = node.get("actions", [])
                if not actions:
                    warnings.append(f"EMPTY_ACTIONS: Action node '{node_id}' has no actions")
                
                for i, action in enumerate(actions):
                    if not isinstance(action, dict):
                        warnings.append(f"INVALID_ACTION: Node '{node_id}' action {i} is not a dictionary")
                        continue
                    
                    action_type = action.get("type")
                    if action_type not in valid_action_types:
                        warnings.append(f"UNKNOWN_ACTION_TYPE: Node '{node_id}' has unknown action type '{action_type}'")
        
        return warnings
    
    def _check_node_structure(self, dsl: Dict[str, Any]) -> List[str]:
        """Check for structural issues in nodes."""
        warnings = []
        nodes = dsl.get("nodes", [])
        
        for node in nodes:
            node_id = node.get("id", "unknown")
            node_type = node.get("type")
            
            # Check for mixed node types
            has_when = "when" in node
            has_actions = "actions" in node
            
            if node_type == "decision" and has_actions:
                warnings.append(f"STRUCTURE_ERROR: Decision node '{node_id}' should not have 'actions' field")
            
            if node_type == "action" and has_when:
                warnings.append(f"STRUCTURE_ERROR: Action node '{node_id}' should not have 'when' field")
            
            # Check for missing required fields
            if node_type == "decision" and not has_when:
                warnings.append(f"MISSING_FIELD: Decision node '{node_id}' missing 'when' condition")
            
            if node_type == "action" and not has_actions:
                warnings.append(f"MISSING_FIELD: Action node '{node_id}' missing 'actions' field")
        
        return warnings


def validate_case(case: Dict[str, Any], case_schema_path: str = None) -> List[str]:
    """Validate a case against the schema."""
    validator = CaseValidator(case_schema_path)
    return validator.validate_case(case)


def lint_rules(dsl: Dict[str, Any]) -> List[str]:
    """Lint DSL rules for issues."""
    validator = DSLValidator()
    return validator.lint_rules(dsl)
