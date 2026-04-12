from ast import List

from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    def __init__(self, hugging_face_transformer_model="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(hugging_face_transformer_model)
    
    def embed(self, texts: list[str]):
        filtered = [t for t in texts if t and t.strip()]
        if not filtered:
            return []
        return self.model.encode(filtered).tolist()
