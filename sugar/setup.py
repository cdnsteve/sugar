"""Setup script for Sugar - AI-powered autonomous development system"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="sugar",
    version="1.0.0",
    author="Steven Leggett",
    author_email="contact@roboticforce.io",
    description="Sugar - AI-powered autonomous development system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cdnsteve/sugar",
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
            "sugar=sugar.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "sugar": ["config/*.yaml"],
    },
)