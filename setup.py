#!/usr/bin/env python3
"""
ETF Stock Analysis Platform - Setup Script
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取requirements文件
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="etf-stock-analysis-platform",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered ETF and stock analysis web platform",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/etf-stock-analysis-platform",
    project_urls={
        "Bug Reports": "https://github.com/your-username/etf-stock-analysis-platform/issues",
        "Source": "https://github.com/your-username/etf-stock-analysis-platform",
        "Documentation": "https://github.com/your-username/etf-stock-analysis-platform/wiki",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Framework :: Flask",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "flake8>=5.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
        ],
        "security": [
            "safety>=2.0.0",
            "bandit>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "etf-analysis=run:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="etf, stock, analysis, ai, investment, finance, web, flask",
)
