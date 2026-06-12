"""Security hardening — input validation, header security, OWASP AST10 checks."""

import re
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses (OWASP recommendations)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks (OWASP AST10)."""

    # Patterns that might indicate injection attempts
    DANGEROUS_PATTERNS = [
        re.compile(r"<script", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # event handlers
        re.compile(r"UNION\s+SELECT", re.IGNORECASE),
        re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
        re.compile(r"'\s*OR\s+'1'\s*=\s*'1", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_string(cls, value: str, field_name: str = "input") -> str:
        """Sanitize a string input value."""
        if not isinstance(value, str):
            return value

        # Check length
        if len(value) > 100_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name}: Input too long (max 100,000 characters)",
            )

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(value):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name}: Potentially malicious input detected",
                )

        return value.strip()

    @classmethod
    def sanitize_dict(cls, data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        """Recursively sanitize a dict."""
        if depth > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input too deeply nested (max 10 levels)",
            )

        sanitized = {}
        for key, value in data.items():
            clean_key = cls.sanitize_string(str(key), f"key.{key}")
            if isinstance(value, str):
                sanitized[clean_key] = cls.sanitize_string(value, clean_key)
            elif isinstance(value, dict):
                sanitized[clean_key] = cls.sanitize_dict(value, depth + 1)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    cls.sanitize_dict(item, depth + 1) if isinstance(item, dict)
                    else cls.sanitize_string(str(item), clean_key) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[clean_key] = value
        return sanitized


def validate_dag_structure(dag: dict[str, Any]) -> list[str]:
    """Validate DAG JSON structure before storage (OWASP AST10: skill authorization)."""
    errors = []

    if not isinstance(dag, dict):
        return ["DAG must be a JSON object"]

    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])

    if not isinstance(nodes, list):
        errors.append("'nodes' must be an array")
    if not isinstance(edges, list):
        errors.append("'edges' must be an array")

    # Check node count limit
    if len(nodes) > 500:
        errors.append(f"Too many nodes ({len(nodes)}). Maximum is 500.")

    # Check edge count limit
    if len(edges) > 2000:
        errors.append(f"Too many edges ({len(edges)}). Maximum is 2000.")

    # Validate node types
    valid_types = {"agent", "tool", "router", "evaluator", "hitl", "input", "output"}
    for node in nodes:
        if not isinstance(node, dict):
            errors.append("Each node must be an object")
            continue
        if "id" not in node:
            errors.append("Each node must have an 'id'")
        node_type = node.get("type", "")
        if node_type not in valid_types:
            errors.append(f"Invalid node type '{node_type}'")

    # Validate edge references
    node_ids = {n.get("id") for n in nodes if isinstance(n, dict)}
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append("Each edge must be an object")
            continue
        source = edge.get("source", "")
        target = edge.get("target", "")
        if source and source not in node_ids:
            errors.append(f"Edge references non-existent source node '{source}'")
        if target and target not in node_ids:
            errors.append(f"Edge references non-existent target node '{target}'")

    return errors
