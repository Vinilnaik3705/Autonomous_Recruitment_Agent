"""Browser acceptance check for an isolated Compose deployment."""

import os
from io import BytesIO
from uuid import uuid4

from docx import Document
from playwright.sync_api import sync_playwright

# Only the disposable Compose CI database should receive test accounts.
if os.getenv("COMPOSE_SMOKE_TEST") != "1":
    raise SystemExit("Set COMPOSE_SMOKE_TEST=1 in a disposable Compose deployment")

import subprocess

suffix = uuid4().hex
email = f"browser-{suffix}@example.org"
password = uuid4().hex
with sync_playwright() as tool:
    browser = tool.chromium.launch(channel="chrome", args=["--no-sandbox"])
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:3000")
    page.get_by_role("button", name="Create candidate account").click()
    page.get_by_label("Name", exact=True).fill("Browser-" + suffix)
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Register", exact=True).click()
    page.get_by_text("No applications yet.").wait_for()
    page.get_by_role("button", name="Sign out").click()
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "recruitment",
            "-d",
            "recruitment",
            "-v",
            f"email={email}",
        ],
        input="UPDATE users SET role='hr' WHERE email=:'email';",
        text=True,
        check=True,
    )
    page.get_by_role("button", name="Use existing account").click()
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_label("Job description").fill("Python backend developer")
    page.get_by_label("Candidate email").fill(email)
    data = BytesIO()
    doc = Document()
    doc.add_paragraph("Synthetic Python resume for CI")
    doc.save(data)
    page.get_by_label("Resume", exact=True).set_input_files(
        {
            "name": "synthetic.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "buffer": data.getvalue(),
        }
    )
    page.get_by_role("button", name="Queue screening").click()
    page.get_by_role("heading", name="synthetic.docx", exact=False).wait_for()
    assert not errors, errors
    browser.close()
