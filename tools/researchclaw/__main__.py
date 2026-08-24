"""Allow running as `python -m researchclaw`."""

from researchclaw.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
