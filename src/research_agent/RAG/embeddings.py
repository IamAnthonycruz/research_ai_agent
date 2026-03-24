from ast import List

from sentence_transformers import SentenceTransformer
import numpy as np
model = SentenceTransformer("all-MiniLM-L6-v2")

def text_embedder(text:list[str]):
    filteredText = [s for s in text if s.strip()]
    if len(filteredText) == 0:
        return []
    
    return model.encode(filteredText)
print(text_embedder(["hi"]))
print(text_embedder([]))
print(text_embedder([""]))