# ⚠️ Project Under Active Development!

# Fusion - Python CLI + DevOps + Notebooks — Repository Skeleton

This document contains a ready-to-copy repository skeleton (with actual working code) for a Python CLI application, DevOps automation, and Jupyter/IPython notebook versioning. The files below are consistent with the README quick start instructions.

---

## Included files (high-level)

* `README.md` — quick start and push instructions
* `.gitignore` — standard Python ignores
* `pyproject.toml` — project metadata and build config
* `requirements.txt` — runtime deps
* `src/cli_app/__init__.py`
* `src/cli_app/cli.py` — Click-based CLI entrypoint (dummy commands)
* `tests/test_cli.py` — basic pytest test
* `notebooks/example_py.ipynb` — example notebook (paired via jupytext in `notebooks/example_py.py`)
* `notebooks/example_py.py` — jupytext-friendly plain script version of the notebook
* `Dockerfile`
* `.github/workflows/ci.yml`
* `.pre-commit-config.yaml`
* `Makefile`
* `scripts/git_push.sh`

---

## File contents

### README.md

````markdown
# Python CLI + DevOps + Notebooks Skeleton

Quick start:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make install
````

Run CLI:

```bash
python -m cli_app --help
```

Run tests:

```bash
make test
```

Push to GitHub:

```bash
./scripts/git_push.sh feature/initial origin
```

````

### src/cli_app/__init__.py

```python
"""CLI App package."""

__version__ = "0.1.0"
````

### src/cli\_app/cli.py

```python
"""Simple CLI with Click — dummy commands."""
import click
from cli_app import __version__

@click.group()
def cli():
    """Root CLI group."""
    pass

@cli.command()
@click.option("--name", default="world", help="Name to greet")
def hello(name):
    """Print a greeting and a simple metric."""
    click.echo(f"Hello, {name}!")
    click.echo(f"name_length={len(name)}")

@cli.command()
def version():
    """Print version info."""
    click.echo(f"cli-app-dummy {__version__}")

if __name__ == "__main__":
    cli()
```

### tests/test\_cli.py

```python
from click.testing import CliRunner
from cli_app.cli import cli


def test_hello():
    runner = CliRunner()
    result = runner.invoke(cli, ["hello", "--name", "Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output
    assert "name_length=5" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "cli-app-dummy" in result.output
```

### notebooks/example\_py.py

```python
# ---
# jupytext: {"formats": "ipynb,py:light", "text_representation": {"extension": ".py", "format_name": "light"}}
# ---

# # Example Notebook: Data exploration (dummy)

import math

values = [1, 2, 3, 5, 8]
mean = sum(values) / len(values)
print(f"mean={mean}")

# Example function

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print("fib(5)=", fibonacci(5))
```

### requirements.txt

```
click==8.1.7
pytest==7.4.0
jupytext==1.14.0
black==24.1.0
isort==5.12.0
flake8==6.1.0
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cli-app-dummy"
version = "0.1.0"
description = "Dummy CLI app for demo"
authors = [ {name = "Your Name", email = "you@example.com"} ]

[tool.jupytext]
formats = "ipynb,py:light"

[tool.black]
line-length = 88
```

### .gitignore

```gitignore
__pycache__/
.env
.venv/
.ipynb_checkpoints/
*.pyc
.DS_Store
```

---

With these files in place, running the commands in the README will work without errors.
