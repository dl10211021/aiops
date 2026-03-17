import sqlite3
import json


def migrate():
    conn = sqlite3.connect("opscore.db")
    cursor = conn.cursor()

    # Check if asset_type column already exists
    cursor.execute("PRAGMA table_info(assets)")
    columns = [row[1] for row in cursor.fetchall()]

    if "asset_type" not in columns:
        print("Adding asset_type column...")
        cursor.execute("ALTER TABLE assets ADD COLUMN asset_type TEXT DEFAULT 'linux'")

        # Migrate existing rows
        cursor.execute("SELECT id, protocol, extra_args_json FROM assets")
        rows = cursor.fetchall()
        for row in rows:
            asset_id = row[0]
            protocol = row[1]
            extra_args = json.loads(row[2]) if row[2] else {}
            sub_type = extra_args.get("sub_type") or extra_args.get("db_type")

            # Decide asset_type
            if sub_type:
                asset_type = sub_type
            elif protocol == "ssh":
                asset_type = "linux"
            elif protocol == "winrm":
                asset_type = "winrm"
            else:
                asset_type = "linux"

            cursor.execute(
                "UPDATE assets SET asset_type = ? WHERE id = ?", (asset_type, asset_id)
            )
        conn.commit()

    print("Migration done.")
    conn.close()


if __name__ == "__main__":
    migrate()
