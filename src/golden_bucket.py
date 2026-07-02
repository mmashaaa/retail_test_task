"""Golden Bucket: retrieval of historical analyst Trios for few-shot grounding.

A "Trio" is (question -> SQL -> analyst report) authored by a human expert.
At query time we embed the user's question and pull the k most similar Trios,
which are injected into the SQL-generation and report-writing prompts so the
agent reproduces how analysts reason about *this* business, not generic SQL.
"""
import time
import requests
import chromadb

from . import config

_EMBED_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{config.EMBED_MODEL}:embedContent"
)


class GeminiEmbeddingFunction:
    """ChromaDB-compatible embedding function backed by the Gemini REST API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.GOOGLE_API_KEY

    def _embed_one(self, text: str) -> list[float]:
        body = {"model": f"models/{config.EMBED_MODEL}",
                "content": {"parts": [{"text": text}]}}
        for attempt in range(5):
            r = requests.post(_EMBED_URL,
                              headers={"x-goog-api-key": self.api_key}, json=body,
                              timeout=60)
            if r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()["embedding"]["values"]
        r.raise_for_status()

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in input]

    # ChromaDB >=0.4 expects this for persisted collections.
    def name(self) -> str:
        return "gemini-embedding"


class GoldenBucket:
    def __init__(self):
        self._client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        self._collection = self._client.get_collection(
            "golden_trios", embedding_function=GeminiEmbeddingFunction())

    def retrieve(self, question: str, k: int = None) -> list[dict]:
        """Return the k most semantically similar Trios for a question."""
        k = k or config.N_RETRIEVED_TRIOS
        res = self._collection.query(query_texts=[question], n_results=k)
        return res["metadatas"][0] if res["metadatas"] else []
