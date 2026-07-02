"""Read-only SQL guard — the deterministic guarantee (independent of the LLM)
that only SELECT/WITH queries ever reach BigQuery. `_validate` is a staticmethod,
so we test it without constructing a BigQuery client (no credentials needed)."""
import pytest
from src.bigquery_tool import BigQueryTool, SQLValidationError

VALID = [
    "SELECT 1",
    "select id from `p.d.users`",
    "  \n WITH t AS (SELECT 1) SELECT * FROM t",
    # column names contain the substrings CREATE/RETURN — must NOT be flagged
    "SELECT created_at, returned_at FROM `p.d.orders`",
    "SELECT * FROM `p.d.orders`;",                 # trailing semicolon tolerated
]

FORBIDDEN = [
    "DELETE FROM `p.d.orders`",
    "DROP TABLE `p.d.orders`",
    "UPDATE `p.d.orders` SET status='x'",
    "INSERT INTO `p.d.orders` VALUES (1)",
    "TRUNCATE TABLE `p.d.orders`",
    "SELECT 1; DROP TABLE `p.d.orders`",           # injection: starts SELECT, hides DROP
    "EXPLAIN SELECT 1",                            # doesn't start with SELECT/WITH
]


@pytest.mark.parametrize("sql", VALID)
def test_valid_queries_pass(sql):
    BigQueryTool._validate(sql)                    # must not raise


@pytest.mark.parametrize("sql", FORBIDDEN)
def test_forbidden_queries_rejected(sql):
    with pytest.raises(SQLValidationError):
        BigQueryTool._validate(sql)
