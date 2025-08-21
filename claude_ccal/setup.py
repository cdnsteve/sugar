"""Setup script for CCAL - Claude Code Autonomous Loop"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ccal",
    version="1.0.0",
    author="Steven Leggett",
    author_email="contact@roboticforce.io",
    description="Claude Code Autonomous Loop - Proactive autonomous development system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ccal",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ccal=ccal.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ccal": ["config/*.yaml"],
    },
)