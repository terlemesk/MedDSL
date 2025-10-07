"""
Snippet retrieval system for citations and explanations.
"""

import json
import os
import re
from collections import Counter
from typing import Dict, List, Optional, Any
import math


class SnippetRetriever:
    """Retrieves and ranks snippets based on relevance."""
    
    def __init__(self, snippets_dir: str = "snippets"):
        self.snippets_dir = snippets_dir
        self.snippets = {}
        self.tf_idf_index = {}
        self.idf_scores = {}
        self._load_snippets()
        self._build_tf_idf_index()
    
    def _load_snippets(self):
        """Load all snippets from JSONL files in the snippets directory."""
        if not os.path.exists(self.snippets_dir):
            return
        
        for filename in os.listdir(self.snippets_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(self.snippets_dir, filename)
                self._load_snippets_from_file(filepath)
    
    def _load_snippets_from_file(self, filepath: str):
        """Load snippets from a single JSONL file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        snippet = json.loads(line)
                        snippet_id = snippet.get('id')
                        if snippet_id:
                            self.snippets[snippet_id] = snippet
                    except json.JSONDecodeError as e:
                        print(f"Warning: Invalid JSON in {filepath}:{line_num}: {e}")
        except FileNotFoundError:
            print(f"Warning: Snippets file not found: {filepath}")
        except Exception as e:
            print(f"Warning: Error loading snippets from {filepath}: {e}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for text."""
        if not text:
            return []
        
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _build_tf_idf_index(self):
        """Build TF-IDF index for snippet retrieval."""
        # Collect all documents (snippets)
        documents = []
        for snippet_id, snippet in self.snippets.items():
            # Combine line and short_quote for indexing
            text = ""
            if 'line' in snippet:
                text += snippet['line'] + " "
            if 'short_quote' in snippet:
                text += snippet['short_quote'] + " "
            
            documents.append({
                'id': snippet_id,
                'text': text.strip()
            })
        
        if not documents:
            return
        
        # Calculate TF (Term Frequency) for each document
        doc_terms = {}
        all_terms = set()
        
        for doc in documents:
            tokens = self._tokenize(doc['text'])
            term_counts = Counter(tokens)
            doc_terms[doc['id']] = term_counts
            all_terms.update(tokens)
        
        # Calculate IDF (Inverse Document Frequency)
        total_docs = len(documents)
        for term in all_terms:
            docs_with_term = sum(1 for term_counts in doc_terms.values() if term in term_counts)
            self.idf_scores[term] = math.log(total_docs / docs_with_term) if docs_with_term > 0 else 0
        
        # Calculate TF-IDF scores
        for doc_id, term_counts in doc_terms.items():
            tf_idf_scores = {}
            doc_length = sum(term_counts.values())
            
            for term, count in term_counts.items():
                tf = count / doc_length  # Normalized term frequency
                idf = self.idf_scores[term]
                tf_idf_scores[term] = tf * idf
            
            self.tf_idf_index[doc_id] = tf_idf_scores
    
    def retrieve(self, snippet_ids: List[str], k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve snippets by ID, with fallback to relevance-based search.
        
        Args:
            snippet_ids: List of snippet IDs to retrieve
            k: Maximum number of snippets to return
            
        Returns:
            List of snippet dictionaries
        """
        results = []
        found_ids = set()
        
        # First, try to retrieve requested IDs
        for snippet_id in snippet_ids:
            if snippet_id in self.snippets:
                results.append(self.snippets[snippet_id])
                found_ids.add(snippet_id)
        
        # If we need more results and have query keywords, do relevance search
        if len(results) < k and snippet_ids:
            # Use snippet IDs as query keywords for fallback search
            query_keywords = snippet_ids
            additional_results = self._search_by_relevance(query_keywords, k - len(results), found_ids)
            results.extend(additional_results)
        
        return results[:k]
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search snippets by relevance to query text.
        
        Args:
            query: Search query text
            k: Maximum number of results
            
        Returns:
            List of snippet dictionaries, ranked by relevance
        """
        return self._search_by_relevance([query], k, set())
    
    def _search_by_relevance(self, query_keywords: List[str], k: int, exclude_ids: set) -> List[Dict[str, Any]]:
        """Search snippets by relevance to query keywords."""
        if not query_keywords or not self.tf_idf_index:
            return []
        
        # Tokenize query
        query_tokens = []
        for keyword in query_keywords:
            query_tokens.extend(self._tokenize(keyword))
        
        if not query_tokens:
            return []
        
        # Calculate relevance scores
        relevance_scores = []
        
        for doc_id, tf_idf_scores in self.tf_idf_index.items():
            if doc_id in exclude_ids:
                continue
            
            score = 0
            for token in query_tokens:
                if token in tf_idf_scores:
                    score += tf_idf_scores[token]
            
            if score > 0:
                relevance_scores.append((doc_id, score))
        
        # Sort by relevance score (descending)
        relevance_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        results = []
        for doc_id, score in relevance_scores[:k]:
            if doc_id in self.snippets:
                results.append(self.snippets[doc_id])
        
        return results
    
    def get_snippet(self, snippet_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific snippet by ID."""
        return self.snippets.get(snippet_id)
    
    def list_snippet_ids(self) -> List[str]:
        """List all available snippet IDs."""
        return list(self.snippets.keys())
    
    def reload_snippets(self):
        """Reload snippets from files."""
        self.snippets.clear()
        self.tf_idf_index.clear()
        self.idf_scores.clear()
        self._load_snippets()
        self._build_tf_idf_index()
    
    def add_snippet(self, snippet: Dict[str, Any]):
        """Add a single snippet to the index."""
        snippet_id = snippet.get('id')
        if snippet_id:
            self.snippets[snippet_id] = snippet
            # Rebuild index to include new snippet
            self._build_tf_idf_index()
    
    def remove_snippet(self, snippet_id: str):
        """Remove a snippet from the index."""
        if snippet_id in self.snippets:
            del self.snippets[snippet_id]
            # Rebuild index
            self._build_tf_idf_index()


# Convenience functions
def create_retriever(snippets_dir: str = "snippets") -> SnippetRetriever:
    """Create a snippet retriever instance."""
    return SnippetRetriever(snippets_dir)


def retrieve_snippets(snippet_ids: List[str], retriever: SnippetRetriever = None, k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve snippets by ID."""
    if retriever is None:
        retriever = create_retriever()
    return retriever.retrieve(snippet_ids, k)


def search_snippets(query: str, retriever: SnippetRetriever = None, k: int = 3) -> List[Dict[str, Any]]:
    """Search snippets by query."""
    if retriever is None:
        retriever = create_retriever()
    return retriever.search(query, k)
