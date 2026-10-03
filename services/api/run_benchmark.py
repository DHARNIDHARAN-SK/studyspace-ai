import asyncio
import os
import sys

# Ensure services/api is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.rag.evaluation.runner import run_full_benchmark

if __name__ == "__main__":
    asyncio.run(run_full_benchmark())
