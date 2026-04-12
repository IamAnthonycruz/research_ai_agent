from uuid import uuid4

import chromadb

from research_agent.RAG.embeddings import Embedder


class Storage:
    def __init__(self, db_path:str, embedder:Embedder ):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="article_store")
        self.embedder = embedder
        
   
    def write(self, chunks: list[dict]):
        if not chunks:
            return 0
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed(texts)
        
        ids = [str(uuid4()) for _ in chunks]
        metadatas = [
            {"source": c["source"], "title":c["title"], "chunk_index": c["chunk_index"]}
            for c in chunks
        ]
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def read(self, query:str, k:int=5):
        query_embedding = self.embedder.embed([query])
        if not query_embedding:
            return []
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k,
        )
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        
        return [
            {
                "text": doc,
                "source": meta["source"],
                "title": meta["title"],
                "chunk_index": meta["chunk_index"],
            }
            for doc, meta in zip(documents, metadatas)
        ]