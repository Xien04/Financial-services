"""Generate the executable OpenAPI contract and fail on unreviewed drift."""

import argparse
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "api" / "openapi.json"


def render_schema() -> str:
    from django.core.management import call_command

    output = io.StringIO()
    call_command(
        "spectacular", format="openapi-json", validate=True, fail_on_warn=True, stdout=output
    )
    return json.dumps(json.loads(output.getvalue()), sort_keys=True, indent=2) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="Write the contract for review")
    options = parser.parse_args(argv)
    schema = render_schema()
    if options.update:
        SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_PATH.write_text(schema, encoding="utf-8")
        print("Generated docs/api/openapi.json; review and commit the contract changes.")
        return 0
    if not SCHEMA_PATH.is_file() or SCHEMA_PATH.read_text(encoding="utf-8") != schema:
        print(
            "OpenAPI contract drift. Run python infra/check_api_schema.py --update and review it."
        )
        return 1
    print("OpenAPI schema validates without warnings and matches the committed contract.")
    return 0


if __name__ == "__main__":
    import django

    sys.path.insert(0, str(ROOT / "backend"))
    # Never inherit production configuration, local .env, or application credentials.
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    django.setup()
    sys.exit(main())
