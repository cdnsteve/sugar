"""Setup script for sugar package"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
README = (Path(__file__).parent / "README.md").read_text()

# Read requirements
requirements = (Path(__file__).parent / "requirements.txt").read_text().strip().split('\n')

setup(
    name="sugar",
    version="0.1.0",
    description="Sugar - AI-powered autonomous development system for Claude Code CLI",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Steven Leggett",
    author_email="contact@roboticforce.io",
    url="https://github.com/cdnsteve/sugar",
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
            "sugar=sugar.main:cli",
        ],
    },
    keywords=["claude", "autonomous", "development", "ai", "automation"],
    project_urls={
        "Documentation": "https://docs.roboticforce.io/sugar",
        "Source": "https://github.com/cdnsteve/sugar",
        "Tracker": "https://github.com/cdnsteve/sugar/issues",
    },
)