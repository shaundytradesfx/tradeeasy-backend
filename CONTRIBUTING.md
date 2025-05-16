# Contributing to TradeEasy Backend

Thank you for your interest in contributing to TradeEasy! This document provides guidelines and instructions for contributing to this project.

## Development Workflow

1. **Fork the repository** and clone your fork locally.
2. **Create a branch** for your feature or bugfix: `git checkout -b feature/your-feature-name` or `bugfix/issue-description`.
3. **Make your changes** following our coding standards.
4. **Write or update tests** as necessary.
5. **Run all tests** to ensure they pass: `pytest`.
6. **Commit your changes** with clear, descriptive commit messages.
7. **Push your branch** to your fork: `git push origin your-branch-name`.
8. **Submit a pull request** to the main repository.

## Branch Naming Convention

- `feature/` - for new features
- `bugfix/` - for bug fixes
- `hotfix/` - for critical fixes
- `docs/` - for documentation updates
- `refactor/` - for code refactoring
- `test/` - for test improvements

## Commit Message Guidelines

Follow these guidelines for commit messages:
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Pull Request Process

1. Update the README.md or documentation with details of changes, if applicable.
2. Update the requirements.txt file if you've added dependencies.
3. The PR should work for Python 3.11 and pass all tests.
4. Make sure the PR description clearly describes the problem and solution.

## Coding Standards

- Follow PEP 8 for Python code style.
- Use type hints for function parameters and return values.
- Write docstrings for all functions and classes.
- Keep functions small and focused.
- Use meaningful variable and function names.

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=app
```

## Setting up Development Environment

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (see README.md).

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## Questions?

If you have any questions, feel free to open an issue or contact the project maintainers directly.

Thank you for contributing to TradeEasy! 