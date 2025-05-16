import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import json
import os
from pathlib import Path

class SemanticSearch:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the semantic search with a sentence transformer model
        
        Args:
            model_name (str): Name of the sentence transformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.questions = []
        self.embeddings = None
        
    def load_questions(self, questions_file: str):
        """Load questions from a JSON file (dict or list)
        
        Args:
            questions_file (str): Path to the JSON file containing questions
        """
        with open(questions_file, 'r') as f:
            data = json.load(f)
        # Support both dict and list formats
        if isinstance(data, dict):
            self.questions = [
                {"question_id": str(qid), "question_text": qdata["question_text"]}
                for qid, qdata in data.items() if "question_text" in qdata
            ]
        elif isinstance(data, list):
            self.questions = [
                {"question_id": q.get("question_id", str(idx)), "question_text": q["question_text"]}
                for idx, q in enumerate(data) if "question_text" in q
            ]
        else:
            raise ValueError("Unsupported questions.json format")
        # Create embeddings for all questions
        question_texts = [q['question_text'] for q in self.questions]
        self.embeddings = self.model.encode(question_texts)
        
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar questions using semantic similarity
        
        Args:
            query (str): The search query
            top_k (int): Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of similar questions with their similarity scores
        """
        if not self.questions or self.embeddings is None:
            raise ValueError("No questions loaded. Call load_questions() first.")
            
        # Encode the query
        query_embedding = self.model.encode(query)
        
        # Calculate cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top k results
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            question = self.questions[idx].copy()
            question['similarity_score'] = float(similarities[idx])
            results.append(question)
            
        return results 