"""
Entry point for running NC2 as a module: python -m nc2
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("TkAgg")

import ttkbootstrap as tb

from .app import NC2App


def main():
    parser = argparse.ArgumentParser(
        prog="nc2",
        description="NC2 -- Fast, versatile NetCDF viewer for scientists.",
    )
    parser.add_argument(
        "file", nargs="?", default=None,
        help="Path to a NetCDF file to open on launch.",
    )
    args = parser.parse_args()

    file_path = None
    if args.file:
        file_path = os.path.abspath(args.file)
        if not os.path.isfile(file_path):
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)

    root = tb.Window(themename="darkly")
    NC2App(root, file_path=file_path)
    root.mainloop()


if __name__ == "__main__":
    main()
