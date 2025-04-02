"""
Initialize the test package.

This file ensures proper package imports and test discovery.
"""
import os
import sys

# Add the project root directory to Python path for test discovery
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
