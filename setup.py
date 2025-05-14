"""
Setup script для модуля Trading APIs & Exchange.
"""
from setuptools import setup, find_packages

setup(
    name="exchange_api",
    version="0.1.0",
    description="Компонент системы VANTA, обеспечивающий унифицированный доступ к API криптовалютных бирж",
    author="VANTA Team",
    author_email="info@vanta.com",
    url="https://github.com/vanta/exchange_api",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=1.9.0,<2.0.0",
        "loguru>=0.6.0",
        "python-dotenv>=0.20.0",
        "aiohttp>=3.8.0",
        "websockets>=10.3",
        "backoff>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
            "black>=22.3.0",
            "isort>=5.10.0",
            "mypy>=0.950",
            "types-requests",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 