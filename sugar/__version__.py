"""Version information for Sugar"""
import tomllib
from pathlib import Path

def _get_version_from_pyproject():
    """Read version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
        return pyproject["project"]["version"]
    except (FileNotFoundError, KeyError, Exception):
        # Fallback version if pyproject.toml can't be read
        return "0.1.0"

__version__ = _get_version_from_pyproject()
__title__ = "Sugar - AI-powered autonomous development system"
__description__ = "Autonomous development assistant for Claude Code CLI"
__author__ = "Steven Leggett"
__author_email__ = "contact@roboticforce.io"
__url__ = "https://github.com/cdnsteve/sugar"

def get_version_info():
    """Get formatted version information"""
    return f"{__title__} v{__version__}"

def get_full_version_info():
    """Get detailed version information"""
    return f"""
{__title__} v{__version__}
{__description__}

Author: {__author__} <{__author_email__}>
Repository: {__url__}
""".strip()