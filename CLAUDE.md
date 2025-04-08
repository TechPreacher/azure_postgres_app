# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Commands
- Setup: `poetry install`
- Run CLI app: `poetry run python app.py`
- Run Streamlit web app: `poetry run streamlit run streamlit_app.py`
- Run type check: `poetry run mypy .`
- Run lint: `poetry run flake8`
- Format code: `poetry run black .`

## Code Style Guidelines
- Python: Follow PEP 8 style guide
- Imports: Group standard library, third-party, and local imports
- Types: Use type annotations for function parameters and return values
- Error handling: Use try/except blocks with specific exceptions
- Naming: snake_case for variables/functions, PascalCase for classes
- Documentation: Docstrings for all functions, classes, and modules
- SQLAlchemy: Close sessions with try/finally pattern
- Environment: Load variables from .env using python-dotenv
- UI: Follow Streamlit best practices for caching and reactivity