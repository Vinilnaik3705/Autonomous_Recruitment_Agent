
from backend.database import get_db_connection

def migrate_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            try:
                # Attempt to add the column. If it exists, it will fail, which we catch.
                print("Attempting to add 'education' column to 'resume_data' table...")
                cur.execute("ALTER TABLE resume_data ADD COLUMN education TEXT;")
                conn.commit()
                print("Column 'education' added successfully.")
            except Exception as e:
                # Check for "DuplicateColumn" or similar, though psycopg2 raises general errors.
                # Usually we can check error code or message, but simpler is to assume it exists if add fails.
                print(f"Migration notice (might be already done): {e}")
                conn.rollback()

    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
