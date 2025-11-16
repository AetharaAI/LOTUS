from setuptools import setup, find_packages

setup(
    name="lotus",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "asyncio>=3.4.3",
        "aiofiles>=23.2.1",
        "redis>=4.6.0",
        "hiredis>=2.3.2",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "pydantic>=2.0.3",
        "pydantic-settings>=2.0.3",
        "psycopg[binary]>=3.1.16",
        "sqlalchemy>=2.0.25",
        "alembic>=1.13.1",
        "asyncpg>=0.30.0",
        "chromadb>=0.4.22",
    ],
    entry_points={
        "console_scripts": [
            "lotus=lotus.nucleus:main",
        ],
    },
)