"""
Shared test setup
"""

# Standard
import os
import sys

# Add the sample_libs directory to the path so that those libs can be imported
# as standalone packages
SAMPLE_LIBS_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "sample_libs")
)
sys.path.append(SAMPLE_LIBS_DIR)
