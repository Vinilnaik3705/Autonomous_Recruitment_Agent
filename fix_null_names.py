"""Fix NULL candidate_name/email in interview_schedules by looking up from resume_data."""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, database='hr_db', user='hr_user', password='hr_pass')
cur = conn.cursor()

# First, check how many NULL rows exist
cur.execute("SELECT id, candidate_name, candidate_email FROM interview_schedules WHERE candidate_name IS NULL ORDER BY created_at DESC")
null_rows = cur.fetchall()
print(f"Found {len(null_rows)} rows with NULL candidate_name")

# Get the best candidate from resume_data
cur.execute("""
    SELECT DISTINCT ON (LOWER(TRIM(email))) candidate_name, email 
    FROM resume_data 
    WHERE candidate_name IS NOT NULL AND email IS NOT NULL AND ai_score >= 35
    ORDER BY LOWER(TRIM(email)), ai_score DESC
""")
candidates = {row[1].strip().lower(): row[0] for row in cur.fetchall() if row[1]}
print(f"Found {len(candidates)} candidates in resume_data: {candidates}")

# Update only the first NULL row per candidate, cancel the rest as duplicates
updated = 0
seen_emails = set()
for row_id, _, _ in null_rows:
    if not candidates:
        break
    # Pick a candidate email that hasn't been assigned yet
    for email, name in list(candidates.items()):
        if email not in seen_emails:
            try:
                cur.execute(
                    "UPDATE interview_schedules SET candidate_name = %s, candidate_email = %s WHERE id = %s",
                    (name, email, row_id)
                )
                seen_emails.add(email)
                updated += 1
                print(f"  Updated ID={row_id} -> Name={name}, Email={email}")
                del candidates[email]
                break
            except Exception as e:
                conn.rollback()
                # If unique constraint fails, cancel this duplicate row
                cur.execute(
                    "UPDATE interview_schedules SET status = 'cancelled' WHERE id = %s",
                    (row_id,)
                )
                print(f"  Cancelled duplicate ID={row_id}: {e}")
                break

# Cancel remaining NULL rows (they're orphaned duplicates)
cur.execute("""
    UPDATE interview_schedules 
    SET status = 'cancelled' 
    WHERE candidate_name IS NULL AND candidate_email IS NULL
""")
cancelled = cur.rowcount
if cancelled:
    print(f"Cancelled {cancelled} remaining orphaned NULL rows")

conn.commit()

# Verify final state
cur.execute("SELECT id, candidate_name, candidate_email, status FROM interview_schedules ORDER BY created_at DESC LIMIT 10")
print("\nFinal state:")
for row in cur.fetchall():
    print(f"  ID={row[0]}, Name={row[1]}, Email={row[2]}, Status={row[3]}")

conn.close()
print("\nDone!")
