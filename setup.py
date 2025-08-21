"""Setup script for claude-ccal package"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
README = (Path(__file__).parent / "README.md").read_text()

# Read requirements
requirements = (Path(__file__).parent / "requirements.txt").read_text().strip().split('\n')

setup(
    name="claude-ccal",
    version="0.1.0",
    description="Claude Code Autonomous Loop - 24/7 autonomous development system",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Steven Leggett",
    author_email="noreply@anthropic.com",
    url="https://github.com/anthropics/claude-ccal",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
    ],
    entry_points={
        "console_scripts": [
            "ccal=claude_ccal.main:cli",
        ],
    },
    keywords=["claude", "autonomous", "development", "ai", "automation"],
    project_urls={
        "Documentation": "https://docs.anthropic.com/claude-code",
        "Source": "https://github.com/anthropics/claude-ccal",
        "Tracker": "https://github.com/anthropics/claude-ccal/issues",
    },
)