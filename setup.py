#!/usr/bin/env python3
"""
Setup script for BioMCP
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
requirements_file = this_directory / "bio_mcp" / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="bio-mcp",
    version="1.0.0",
    author="BioMCP Team",
    author_email="contact@bio-mcp.org",
    description="AI-Powered Biological Research Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/bio-mcp",
    packages=find_packages(where="bio_mcp"),
    package_dir={"": "bio_mcp"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11", 
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0",
            "flake8>=6.0",
        ],
        "gui": [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bio-mcp=bio_mcp.bio_mcp:main",
            "bio-mcp-server=bio_mcp.mcp_server.bio_mcp_server.main:main",
            "bio-mcp-host=bio_mcp.mcp_host.bio_mcp_host.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "bio_mcp": [
            "bio_data/*",
            "bio_data/**/*",
            "*.yml",
            "*.json",
            "*.md",
        ],
    },
    zip_safe=False,
)