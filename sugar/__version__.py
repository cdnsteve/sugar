"""Version information for Sugar"""

__version__ = "0.1.0"
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