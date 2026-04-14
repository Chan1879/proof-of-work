"""JSON-schema contract validation for MCP resume tools.

Loads tool-contracts.json from the policies/ directory and validates
tool inputs and outputs against the declared schemas.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

CONTRACTS_PATH = Path(os.environ.get(
    "CONTRACTS_PATH",
    Path(__file__).resolve().parent.parent / "policies" / "tool-contracts.json",
))


class ContractValidationError(ValueError):
    """Raised when a tool payload fails schema validation."""


class ContractRegistry:
    """Load and validate tool payloads against JSON Schema contracts.

    On instantiation the registry reads the contract file (defaulting to
    ``CONTRACTS_PATH``) and builds an in-memory lookup of tool schemas.

    Args:
        contract_file: Optional override path to ``tool-contracts.json``.
    """

    def __init__(self, contract_file: str | Path | None = None):
        self.contract_file = Path(contract_file) if contract_file else CONTRACTS_PATH
        self.contracts = self._load()

    def _load(self) -> dict[str, Any]:
        """Read and parse the JSON contract file."""
        with self.contract_file.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _tool(self, name: str) -> dict[str, Any]:
        """Look up a tool's contract entry by name.

        Raises:
            ContractValidationError: If no tool with *name* exists.
        """
        for tool in self.contracts.get("tools", []):
            if tool.get("name") == name:
                return tool
        raise ContractValidationError(f"Unknown tool: {name}")

    def _with_shared_defs(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Attach top-level shared ``$defs`` so local ``$ref`` resolves."""
        merged = dict(schema)
        if "$defs" not in merged and "$defs" in self.contracts:
            merged["$defs"] = self.contracts["$defs"]
        return merged

    def validate_input(self, tool_name: str, payload: dict[str, Any]) -> None:
        """Validate *payload* against the tool's ``input_schema``.

        Args:
            tool_name: Registered tool name (e.g. ``"analyze_job_description"``).
            payload: Dict of tool input arguments.

        Raises:
            ContractValidationError: If *payload* does not conform to the schema.
        """
        schema = self._with_shared_defs(self._tool(tool_name)["input_schema"])
        try:
            validate(instance=payload, schema=schema)
        except ValidationError as exc:
            raise ContractValidationError(
                f"Input validation failed for {tool_name}: {exc.message}"
            ) from exc

    def validate_output(self, tool_name: str, payload: dict[str, Any]) -> None:
        """Validate a tool's result *payload* against the ``output_schema``.

        Args:
            tool_name: Registered tool name.
            payload: Dict of tool output fields.

        Raises:
            ContractValidationError: If *payload* does not conform to the schema.
        """
        schema = self._with_shared_defs(self._tool(tool_name)["output_schema"])
        try:
            validate(instance=payload, schema=schema)
        except ValidationError as exc:
            raise ContractValidationError(
                f"Output validation failed for {tool_name}: {exc.message}"
            ) from exc
