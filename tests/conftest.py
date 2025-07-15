"""
Pytest configuration file.
This file helps pytest with test discovery and configuration.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to sys.path to help with imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# This is needed for pytest-asyncio
pytest_plugins = ["pytest_asyncio"]