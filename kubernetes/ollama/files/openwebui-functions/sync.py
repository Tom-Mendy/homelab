import json
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, text

FUNCTION_ID = "token_usage_display"
FUNCTION_PATH = Path("/functions/token_usage_display.py")


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    function_source = FUNCTION_PATH.read_text(encoding="utf-8")
    now = int(time.time())
    metadata = {
        "description": "Shows Ollama output tokens per second below each response.",
        "manifest": {
            "title": "Token rate display",
            "author": "homelab",
            "version": "1.0.0",
            "required_open_webui_version": "0.9.0",
        },
    }

    engine = create_engine(database_url)
    with engine.begin() as connection:
        owner_id = connection.execute(
            text(
                'SELECT id FROM "user" '
                "WHERE role = 'admin' ORDER BY created_at LIMIT 1"
            )
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO function (
                    id, user_id, name, type, content, meta, valves,
                    is_active, is_global, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :name, 'filter', :content, :meta, :valves,
                    TRUE, TRUE, :now, :now
                )
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    content = EXCLUDED.content,
                    meta = EXCLUDED.meta,
                    valves = EXCLUDED.valves,
                    is_active = TRUE,
                    is_global = TRUE,
                    updated_at = :now
                """
            ),
            {
                "id": FUNCTION_ID,
                "user_id": owner_id,
                "name": "Token rate display",
                "content": function_source,
                "meta": json.dumps(metadata),
                "valves": json.dumps({"priority": 10}),
                "now": now,
            },
        )

    print(f"Reconciled Open WebUI function {FUNCTION_ID}")


if __name__ == "__main__":
    main()
