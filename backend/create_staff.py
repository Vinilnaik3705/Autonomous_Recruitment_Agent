"""Create an HR, admin, or interviewer account in the configured database."""

from argparse import ArgumentParser
from getpass import getpass

from pydantic import EmailStr, TypeAdapter

from backend.auth import hash_password
from backend.database import worker_conn
from backend.db.queries import users


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("full_name")
    parser.add_argument("--role", choices=["admin", "hr", "interviewer"], default="hr")
    args = parser.parse_args()
    email = TypeAdapter(EmailStr).validate_python(args.email).lower()
    password = getpass("Password (at least 8 characters): ")
    if not 8 <= len(password) <= 128 or password != getpass("Confirm password: "):
        parser.error("Passwords must match and contain 8–128 characters")
    with worker_conn() as conn:
        user = users.create_staff(
            conn, email, args.full_name.strip(), hash_password(password), args.role
        )
        if not user:
            parser.error("An account already uses this email")
    print(f"Created {args.role} account {user['id']}")


if __name__ == "__main__":
    main()
