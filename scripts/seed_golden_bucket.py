import json
import os
import time
import logging

# Silence ChromaDB's broken posthog telemetry (upstream bug) — must be set
# before importing chromadb.
os.environ["ANONYMIZED_TELEMETRY"] = "false"
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

import requests
import chromadb
from dotenv import load_dotenv

load_dotenv(override=True)

TRIOS_PATH = os.path.join(os.path.dirname(__file__), "../data/golden_trios.json")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../chroma_db")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"


class GeminiEmbeddingFunction:
    def _embed_one(self, text: str) -> list[float]:
        body = {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": text}]}}
        for attempt in range(5):
            r = requests.post(EMBED_URL, headers={"x-goog-api-key": GEMINI_API_KEY}, json=body)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()["embedding"]["values"]
        r.raise_for_status()

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in input]


def seed():
    with open(TRIOS_PATH) as f:
        trios = json.load(f)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = GeminiEmbeddingFunction()

    if "golden_trios" in client.list_collections():
        client.delete_collection("golden_trios")

    collection = client.get_or_create_collection("golden_trios", embedding_function=ef)

    collection.add(
        ids=[t["id"] for t in trios],
        documents=[t["question"] for t in trios],
        metadatas=[{"sql": t["sql"], "report": t["report"], "question": t["question"]} for t in trios],
    )

    print(f"Seeded {len(trios)} trios into ChromaDB.")

    print("\nRetrieval test — 'which products have high return rates?'")
    results = collection.query(query_texts=["which products have high return rates?"], n_results=2)
    for i, meta in enumerate(results["metadatas"][0]):
        print(f"  Match {i+1}: {meta['question']}")


if __name__ == "__main__":
    seed()
