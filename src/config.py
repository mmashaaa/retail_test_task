"""Central configuration. Loads .env and exposes typed settings."""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Silence ChromaDB's broken posthog telemetry (upstream bug, harmless).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

# Cost guardrail: cap bytes scanned per BigQuery query (resilience requirement).
MAX_BYTES_BILLED = int(os.getenv("MAX_BYTES_BILLED", str(2 * 1024**3)))  # 2 GB

# Self-correction: how many times to retry a failing SQL query before giving up.
MAX_SQL_ATTEMPTS = int(os.getenv("MAX_SQL_ATTEMPTS", "3"))

# Golden Bucket
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
TRIOS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "golden_trios.json")
N_RETRIEVED_TRIOS = int(os.getenv("N_RETRIEVED_TRIOS", "3"))

# Saved Reports library
REPORTS_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "reports.db")

# Persona (tone) — editable by non-developers without redeploy.
PERSONA_PATH = os.path.join(os.path.dirname(__file__), "..", "persona.yaml")

# Dataset
DATASET = "bigquery-public-data.thelook_ecommerce"
