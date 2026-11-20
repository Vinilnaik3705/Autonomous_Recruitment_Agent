"""Authorize a test or production sender on its operator's local desktop."""

import argparse
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "client", type=Path, help="Downloaded Desktop OAuth client JSON"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("secrets/google-token.json")
    )
    args = parser.parse_args()
    scopes = [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.freebusy",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        parser.error(
            "Choose a new output path or move the existing token before rotation"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(args.client), scopes)
    credentials = flow.run_local_server(
        host="127.0.0.1", port=0, access_type="offline", prompt="consent"
    )
    if not credentials.refresh_token:
        raise RuntimeError("Google did not issue a refresh token")
    with os.fdopen(
        os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
    ) as output:
        output.write(credentials.to_json())
    print(f"Authorized-user credentials saved to {args.output}")


if __name__ == "__main__":
    main()
