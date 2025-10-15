## Development Environment

This project supports both **uv** (recommended) and **venv** workflows:

### Using uv (Recommended - Much Faster!)
```bash
# Install dependencies
uv pip install -e ".[dev,test,github]"

# Run commands
uv run python -m sugar ...
uv run pytest tests/
uv run black .
```

### Using venv (Traditional)
```bash
# Activate venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev,test,github]"

# Run commands
python -m sugar ...
pytest tests/
black .
```

## Code Quality

- Make sure to run Black formatting tests before committing work
- Both uv and venv workflows are supported - use whichever you prefer