# Contributing to AgentForge

Thank you for your interest in contributing to AgentForge!

## Development Setup

### Backend
```bash
cd backend
python -m venv .venv
pip install -e ".[dev]"
```

### Frontend
```bash
cd frontend
npm install
```

## Coding Standards

- Backend: Ruff (line-length 100), mypy strict, type hints everywhere
- Frontend: ESLint + Prettier, TypeScript strict, Tailwind CSS

## Pull Request Process

1. Fork and create a feature branch
2. Make changes with tests
3. Run linting and tests
4. Open a PR with a detailed description linking to the related issue (use `Fixes #XXX` or `Closes #XXX`)

## Reporting Issues

Use GitHub Issues with steps to reproduce and expected behavior.
