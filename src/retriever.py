import hashlib

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

COLLECTION_NAME = "rag_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DB_PATH = "db"
BATCH_SIZE = 100


class Retriever:
    def __init__(self):
        ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        client = chromadb.PersistentClient(path=DB_PATH)
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=ef
        )

    def add_chunks(self, chunks: list[dict]) -> None:
        ids = [
            hashlib.md5(
                f"{c['source']}|{c['page']}|{idx}|{c['text'][:80]}".encode()
            ).hexdigest()
            for idx, c in enumerate(chunks)
        ]
        docs = [c["text"] for c in chunks]
        metas = [{"source": c["source"], "page": c["page"]} for c in chunks]

        for i in range(0, len(chunks), BATCH_SIZE):
            self._collection.upsert(
                ids=ids[i : i + BATCH_SIZE],
                documents=docs[i : i + BATCH_SIZE],
                metadatas=metas[i : i + BATCH_SIZE],
            )

    def query(self, text: str, k: int = 5) -> list[dict]:
        results = self._collection.query(
            query_texts=[text],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "text": doc,
                "source": meta["source"],
                "page": meta["page"],
                "distance": dist,
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
