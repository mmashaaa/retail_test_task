"""Read-only BigQuery access with cost guardrails and schema introspection."""
import re
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from . import config

# Anything that could mutate data or run unbounded — rejected before execution.
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class SQLValidationError(Exception):
    """Raised when a query is unsafe (non-SELECT / mutating)."""


class SQLExecutionError(Exception):
    """Raised when BigQuery rejects a syntactically-issued query.

    Carries the raw BigQuery message so the self-correction node can feed it
    back to the LLM.
    """


class BigQueryTool:
    def __init__(self):
        self._client = bigquery.Client(project=config.GCP_PROJECT_ID)

    @staticmethod
    def _validate(sql: str) -> None:
        stripped = sql.strip().rstrip(";")
        if not re.match(r"^\s*(SELECT|WITH)\b", stripped, re.IGNORECASE):
            raise SQLValidationError("Only SELECT/WITH queries are permitted.")
        if _FORBIDDEN.search(stripped):
            raise SQLValidationError("Query contains a forbidden mutating keyword.")

    def run(self, sql: str) -> list[dict]:
        """Validate then execute a query. Returns rows as a list of dicts."""
        self._validate(sql)
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=config.MAX_BYTES_BILLED,
            use_query_cache=True,
        )
        try:
            job = self._client.query(sql, job_config=job_config)
            rows = job.result()
        except GoogleAPIError as e:
            raise SQLExecutionError(str(e)) from e
        return [dict(r) for r in rows]

    def schema_overview(self) -> str:
        """Compact schema of the four required tables, for SQL-gen grounding."""
        tables = ["orders", "order_items", "products", "users"]
        lines = []
        for t in tables:
            ref = f"{config.DATASET}.{t}"
            table = self._client.get_table(ref)
            cols = ", ".join(f"{f.name} {f.field_type}" for f in table.schema)
            lines.append(f"{t} ({cols})")
        return "\n".join(lines)
