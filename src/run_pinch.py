"""PyInstaller entry point for Pinch.

This wrapper exists because PyInstaller runs the entry point script
directly, which breaks relative imports in __main__.py. This file
uses absolute imports to bootstrap the package correctly.
"""

from pinch.__main__ import main

main()
