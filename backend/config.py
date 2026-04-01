"""
Purpose:
- Central configuration for backend runtime behavior.
- This file will store environment and app-level settings later.
"""

# Keeping metadata in one place makes startup and deployment settings
# easy to evolve without touching route logic.
APP_NAME = "language"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = (
    "API surface for compiling, running, and AI-assisted suggestions "
    "for language source code."
)
