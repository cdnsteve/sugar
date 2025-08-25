"""Version information for Sugar"""

import tomllib
from pathlib import Path

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version


def _get_version():
    """Get version from package metadata or pyproject.toml"""
    try:
        # First try to get version from installed package metadata
        return version("sugarai")
    except Exception:
        pass

    try:
        # Fallback: read from pyproject.toml (for development)
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
        return pyproject["project"]["version"]
    except (FileNotFoundError, KeyError, Exception):
        # Final fallback version
        return "0.1.0"


__version__ = _get_version()
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
