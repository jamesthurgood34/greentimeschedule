"""Utility for loading environment variables from .env files."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Determine the project root directory
project_root = Path(__file__).parent.parent.parent.absolute()

# Load environment variables from .env file
env_file = os.path.join(project_root, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded environment variables from {env_file}")
else:
    print(f"No .env file found at {env_file}, using default values")
