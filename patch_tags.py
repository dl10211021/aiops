import sqlite3
import os


def migrate():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(root_dir, "opscore.db")

    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}, nothing to migrate.")
        return

    print("Starting migration...")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Ensure new tables exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_tags (
                asset_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (asset_id, tag_id),
                FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        # Check if group_name exists
        cursor.execute("PRAGMA table_info(assets)")
        columns = [col["name"] for col in cursor.fetchall()]
        if "group_name" not in columns:
            print(
                "group_name column already removed. Migration might have run already."
            )
            return

        # Read all assets
        cursor.execute("SELECT id, group_name FROM assets")
        rows = cursor.fetchall()

        print(f"Migrating {len(rows)} assets...")
        for row in rows:
            asset_id = row["id"]
            group_name = row["group_name"] or "未分组"

            # Insert tag if not exists
            cursor.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)", (group_name,)
            )
            cursor.execute("SELECT id FROM tags WHERE name = ?", (group_name,))
            tag_id = cursor.fetchone()["id"]

            # Link asset and tag
            cursor.execute(
                "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                (asset_id, tag_id),
            )

        # Drop group_name column
        print("Dropping group_name column...")
        try:
            cursor.execute("ALTER TABLE assets DROP COLUMN group_name")
            print("Successfully dropped group_name via ALTER TABLE.")
        except sqlite3.OperationalError as e:
            print(
                f"ALTER TABLE DROP COLUMN failed: {e}. Falling back to table recreation."
            )
            # Fallback for old sqlite versions
            cursor.execute("""
                CREATE TABLE assets_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remark TEXT,
                    host TEXT,
                    port INTEGER,
                    username TEXT,
                    password TEXT,
                    protocol TEXT,
                    agent_profile TEXT,
                    extra_args_json TEXT,
                    skills_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO assets_new (id, remark, host, port, username, password, protocol, agent_profile, extra_args_json, skills_json, created_at)
                SELECT id, remark, host, port, username, password, protocol, agent_profile, extra_args_json, skills_json, created_at FROM assets
            """)
            cursor.execute("DROP TABLE assets")
            cursor.execute("ALTER TABLE assets_new RENAME TO assets")
            print("Successfully dropped group_name via table recreation.")

        conn.commit()
    print("Migration complete!")


if __name__ == "__main__":
    migrate()
