# Contributing

Thank you for your interest in contributing to mixin-suite!

## Development Setup

### Prerequisites
- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) for dependency management

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/jekhator/mixin-suite.git
   cd mixin-suite
   ```

2. Install dependencies and all optional extras:
   ```bash
   uv sync --all-extras
   ```

3. Verify the setup by running tests:
   ```bash
   uv run pytest
   ```

## Running Tests

Execute the full test suite:
```bash
uv run pytest
```

For coverage report:
```bash
uv run pytest --cov=mixin_logging --cov=mixin_sensitivity --cov-report=term-missing
```

## Linting and Code Style

Format and lint your code before committing:
```bash
uv run ruff check --fix .
uv run ruff format .
```

## Submitting Changes

1. Create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Add tests for new functionality
4. Ensure all tests pass: `uv run pytest`
5. Ensure linting passes: `uv run ruff check .`
6. Push your branch and open a pull request against `main`

## Pull Request Requirements

All pull requests must:
- Pass all CI checks (tests, linting, type checks)
- Include tests for new code
- Update documentation if needed
- Have clear commit messages

Thank you for contributing!
