"""Tiny entrypoint so `leafcheck` is a console script.

Subcommands land in later milestones (data prepare, train, evaluate, verify,
serve). For M1 we just print the version.
"""

from __future__ import annotations

import argparse

from leafcheck import __version__


def main() -> None:
    parser = argparse.ArgumentParser(prog="leafcheck")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(__version__)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
