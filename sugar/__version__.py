"""Version information for the Sugar package.

This module provides version information and package metadata for Sugar,
an autonomous development assistant. It supports multiple version resolution
strategies to work correctly in both installed and development environments.

The version is resolved in the following order of precedence:
1. Package metadata (for installed packages via pip/uv)
2. pyproject.toml (for development environments)
3. Fallback default version (as a last resort)

Attributes:
    __version__: The current version string (e.g., "2.1.0").
    __title__: The display title with decorative emojis.
    __description__: A brief description of the package.
    __author__: The package author's name.
    __author_email__: Contact email for the author.
    __url__: URL to the project's source repository.

Example:
    >>> from sugar.__version__ import __version__, get_version_info
    >>> print(__version__)
    2.1.0
    >>> print(get_version_info())
    Sugar ... Autonomous development assistant v2.1.0
"""

import tomllib
from pathlib import Path

# Python 3.8+ has importlib.metadata in stdlib; older versions need backport
try:
    from importlib.metadata import version as get_package_version
except ImportError:
    from importlib_metadata import version as get_package_version


def _get_version() -> str:
    """Resolve the package version using a cascading fallback strategy.

    This internal function attempts to determine the package version through
    multiple methods to ensure it works in all environments:

    1. **Installed package metadata**: Uses importlib.metadata to query the
       installed package version. This is the most reliable method when the
       package is properly installed via pip or uv.

    2. **pyproject.toml**: Falls back to reading the version directly from
       pyproject.toml. This is useful during development when the package
       may not be installed in editable mode.

    3. **Default fallback**: Returns "0.1.0" as a last resort if all other
       methods fail. This should rarely occur in practice.

    Returns:
        The version string (e.g., "2.1.0").

    Note:
        The package name used for metadata lookup is "sugarai", which matches
        the name specified in pyproject.toml.
    """
    try:
        # Primary method: query installed package metadata
        # This works when package is installed via `pip install` or `uv pip install`
        return get_package_version("sugarai")
    except Exception:
        # PackageNotFoundError or other issues - package not installed
        pass

    try:
        # Secondary method: read directly from pyproject.toml
        # Useful during development without editable install
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
        return pyproject["project"]["version"]
    except (FileNotFoundError, KeyError, Exception):
        # pyproject.toml not found, malformed, or missing version key
        pass

    # Final fallback: return a default version
    # This indicates the version couldn't be determined through normal means
    return "0.1.0"


# Package metadata constants
__version__ = _get_version()
__title__ = "Sugar ✨ 🍰 ✨ "
__description__ = "Autonomous development assistant"
__author__ = "Steven Leggett"
__author_email__ = "contact@roboticforce.io"
__url__ = "https://github.com/cdnsteve/sugar"


def get_version_info() -> str:
    """Get a single-line formatted version string for display.

    Constructs a user-friendly version string that includes the title,
    description, and version number. Handles Windows terminal encoding
    limitations by falling back to a plain ASCII version if emoji
    characters cannot be encoded.

    Returns:
        A formatted version string like "Sugar ... v2.1.0".
        On Windows terminals with limited encoding support, emojis
        are omitted.

    Example:
        >>> print(get_version_info())
        Sugar ✨ 🍰 ✨  Autonomous development assistant v2.1.0
    """
    import sys

    try:
        # Attempt to construct and validate the full output with emojis
        output = f"{__title__} {__description__} v{__version__}"
        # Test encoding to detect terminal limitations before returning
        output.encode(sys.stdout.encoding or "utf-8")
        return output
    except (UnicodeEncodeError, AttributeError):
        # Windows terminals (cmd.exe, PowerShell) may not support emoji encoding
        # Fall back to plain ASCII version
        return f"Sugar {__description__} v{__version__}"


def get_full_version_info() -> str:
    """Get a multi-line formatted version string with full package details.

    Constructs a detailed version banner including the title, version,
    description, author information, and repository URL. Like
    `get_version_info()`, this handles Windows terminal encoding
    limitations gracefully.

    Returns:
        A multi-line string containing:
        - Title and version
        - Description
        - Author name and email
        - Repository URL

    Example:
        >>> print(get_full_version_info())
        Sugar ✨ 🍰 ✨  v2.1.0
        Autonomous development assistant

        Author: Steven Leggett <contact@roboticforce.io>
        Repository: https://github.com/cdnsteve/sugar
    """
    import sys

    try:
        # Test if terminal can handle emoji characters
        title_line = f"{__title__} v{__version__}"
        title_line.encode(sys.stdout.encoding or "utf-8")
        title = __title__
    except (UnicodeEncodeError, AttributeError):
        # Use plain ASCII title for limited terminals
        title = "Sugar"

    return f"""
{title} v{__version__}
{__description__}

Author: {__author__} <{__author_email__}>
Repository: {__url__}
""".strip()
