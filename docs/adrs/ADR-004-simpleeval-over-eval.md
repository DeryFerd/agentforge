# ADR-004: simpleeval over eval() for Router Expressions

**Status:** Accepted
**Date:** 2026-06-13

## Context

The Router node needs to evaluate user-defined conditional expressions like `upstream['classifier']['intent'] == 'billing'` to determine routing paths. The initial implementation used Python's `eval()` with `{"__builtins__": {}}`.

## Problem

`eval()` with empty builtins is **trivially exploitable** via:
```python
().__class__.__bases__[0].__subclasses__()
```
This allows arbitrary code execution — a critical security vulnerability (CVE-level).

## Options Considered

### 1. simpleeval (Selected)
- **Pros:** Purpose-built safe expression evaluator. Supports comparisons, boolean ops, arithmetic, attribute access. Blocks function calls, imports, and class access. Active maintenance. Small dependency.
- **Cons:** Limited expression power (no function calls, no comprehensions).

### 2. asteval
- **Pros:** More powerful (supports numpy, function definitions). Good for scientific computing.
- **Cons:** Overpowered for routing expressions. Larger attack surface.

### 3. Custom DSL
- **Pros:** Full control over allowed operations.
- **Cons:** Weeks of parser development. Edge cases in expression parsing.

### 4. JSON-based conditions
- **Pros:** No code evaluation at all. Fully declarative.
- **Cons:** Too restrictive. Can't express `upstream['x']['score'] > 0.8`.

## Decision

**simpleeval** — provides safe expression evaluation with sufficient power for routing conditions. Blocks all code execution vectors while supporting the comparison and access patterns needed for routing.

## Consequences

- `eval()` completely removed from the codebase
- Router expressions support: `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, `in`, `+`, `-`, `*`, `/`, `[]` access
- Malicious expressions like `__import__('os').system('...')` fail safely (return None)
- Test coverage: `test_safeeval_blocks_malicious_expression` verifies security
