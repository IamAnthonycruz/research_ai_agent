from sentence_transformers import SentenceTransformer
import numpy as np
model = SentenceTransformer("all-MiniLM-L6-v2")

def cosine_similarity(a,b):
    return np.dot(a,b)/(np.linalg.norm(a) * np.linalg.norm(b))

e1 = model.encode("Nuclear fusion energy breakthroughs 2024")
e2 = model.encode("Nuclear energy advancements 2024")
e3 = model.encode("Best chocolate cake recipe")

print(f"fusion vs energy: {cosine_similarity(e1, e2):.4f}")
print(f"fusion vs cake:   {cosine_similarity(e1, e3):.4f}")