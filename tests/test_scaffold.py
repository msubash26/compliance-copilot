"""Placeholder so CI has something to collect until real tests land."""

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "regops_ingest",
        "regops_retrieval",
        "regops_agents",
        "regops_evals",
        "regops_serving",
        "regops_api",
        "regdocs_mcp",
    ],
)
def test_workspace_members_import(module: str) -> None:
    __import__(module)
