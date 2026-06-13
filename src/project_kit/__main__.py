"""Allow `python -m project_kit` invocation as an alternate entry point.

`prog_name="pkit"` overrides Click's auto-derived program name so help
text and error messages read `pkit ...` rather than `python -m
project_kit ...` regardless of how the runtime was invoked.
"""

from project_kit.cli import main

if __name__ == "__main__":
    main(prog_name="pkit")
