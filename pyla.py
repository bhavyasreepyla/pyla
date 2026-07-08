#!/usr/bin/env python3
"""Thin wrapper so `python pyla.py` works from the repo without installing.

The real CLI lives in pyla/cli.py; after `pip install .` you get a global
`pyla` command that runs the same code.
"""

import sys

from pyla.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
