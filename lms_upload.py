"""Upload an assignment file to the RNGPIT LMS using Playwright (sync API).

The first run asks a few questions (folder path, subjects) and saves the
answers to config.json, so there is no need to edit this file.

Usage:
    python lms_upload.py --setup
    python lms_upload.py --subject fcp --list
    python lms_upload.py --subject fcp --assignment "Unit:3" --dry-run
    python lms_upload.py --subject fcp --assignment "Unit:3" --file Unit3.pdf
"""

import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------- Configuration
LMS_URL = "https://rngpit.gnums.co.in/Login.aspx"
USERNAME = os.environ.get("LMS_USERNAME")
PASSWORD = os.environ.get("LMS_PASSWORD")

DASHBOARD_URL_PATTERN = "**/StudentPanel/StudentDashboard.aspx*"  # logged-in check

CONFIG_PATH = Path(__file__).with_name("config.json")  # created by the setup questions
SCREENSHOT_PATH = Path.home() / "assignments" / "screenshot_fallback.png"

# CSS/text selectors for the LMS pages. If the LMS UI changes, edit them here
# (`playwright codegen <url>` is a handy way to find new ones).
SELECTORS = {
    "student_role": "label:text-is('Student')",  # Role radio, defaults to Staff
    "username": "#txtUsername",
    "password": "#txtPassword",
    "login_button": "#btnLogin",
    "pending_tab": "text=/pending submission/i",
    "upload_link": "text=/click here to submit/i",
    "file_input": "#ctl00_cphPageContent_fuSubmissionDocumentPath",
    "submit_button": "#ctl00_cphPageContent_btnSubmit",
    "confirm_yes": "text=/^\\s*yes\\s*$/i >> visible=true",  # pop-up: 'Are you sure want to Submit Assignment?'
}


# ------------------------------------------------------------------ Setup / config
def ask(prompt, default=None):
    """Ask a question in the terminal and return the answer (or the default)."""
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip().strip('"')
    return answer or default or ""


def read_config():
    """Read config.json, or return an empty config if it does not exist yet."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"subjects": {}}


def run_setup():
    """Ask for the folder layout and subjects, then save them to config.json."""
    config = read_config()
    print("\n--- LMS Assignment Tool setup ---")

    # Where do the subject folders live?
    while True:
        base = ask("Folder that contains your subject folders", config.get("base_folder"))
        base_path = Path(base).expanduser()
        if base_path.is_dir():
            break
        print("That folder doesn't exist, please try again.")

    config["base_folder"] = str(base_path)
    config["assignment_subfolder"] = ask(
        "Name of the assignments folder inside each subject folder",
        config.get("assignment_subfolder", "Assignment"),
    )

    # Which subjects should the tool know about?
    print("\nNow add your subjects. Press Enter on the short name to finish.")
    while True:
        key = ask("Short name (e.g. fcp)").lower().replace(" ", "")
        if not key:
            break

        folder = ask(f"Folder name for '{key}' inside {base_path}", key.upper())
        url = ask("LMS subject page URL (copy it from the browser address bar)")
        if not url.startswith("http"):
            print("That doesn't look like a URL, subject skipped.")
            continue

        config["subjects"][key] = {"folder": folder, "url": url}
        assignment_dir = base_path / folder / config["assignment_subfolder"]
        if not assignment_dir.is_dir():
            print(f"Note: {assignment_dir} doesn't exist yet, create it before uploading.")
        print(f"Saved subject '{key}'.")

    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nSetup saved to {CONFIG_PATH}")


def load_config():
    """Load config.json, running the setup questions first if it is missing."""
    if not CONFIG_PATH.exists():
        print("No config.json found, starting first-time setup.")
        run_setup()
    return read_config()


# ---------------------------------------------------------------------- Helpers
def pick_file(config, subject_folder, file_name=None):
    """Return the given file, or the newest file, in the subject's assignment folder."""
    folder = Path(config["base_folder"]) / subject_folder / config["assignment_subfolder"]

    if file_name:
        path = folder / file_name
        if not path.is_file():
            sys.exit(f"File not found: {path}")
        return path

    files = [f for f in folder.glob("*") if f.is_file() and not f.name.startswith("~$")]
    if not files:
        sys.exit(f"No files found in: {folder}")
    return max(files, key=lambda f: f.stat().st_mtime)


def login(page):
    """Select the Student role, fill the login form and wait for the dashboard."""
    page.on("dialog", lambda dialog: dialog.accept())  # auto-dismiss any alert pop-up
    page.goto(LMS_URL)
    page.click(SELECTORS["student_role"])  # page defaults to Staff
    page.wait_for_load_state("networkidle")  # role change may reload the form
    page.fill(SELECTORS["username"], USERNAME)
    page.fill(SELECTORS["password"], PASSWORD)
    page.click(SELECTORS["login_button"])

    print("Waiting for the dashboard (finish any extra login step in the browser if asked)...")
    page.wait_for_url(DASHBOARD_URL_PATTERN, timeout=120_000)
    print("Logged in.")


def list_pending(page, subject_url):
    """Print the names of all pending assignments for a subject."""
    page.goto(subject_url)
    page.click(SELECTORS["pending_tab"])

    rows = page.locator("tr").filter(has=page.locator(SELECTORS["upload_link"]))
    try:
        rows.first.wait_for(timeout=15_000)
    except PlaywrightTimeout:
        print("No pending assignments for this subject.")
        return

    print("Pending assignments:")
    for row in rows.all():
        print("  -", row.locator("td").nth(1).inner_text().strip())


def is_still_pending(page, subject_url, assignment):
    """Reopen the Pending Submission list and check if the assignment is still there."""
    page.goto(subject_url)
    page.click(SELECTORS["pending_tab"])
    page.wait_for_load_state("networkidle")

    rows = page.locator("tr").filter(has=page.locator(SELECTORS["upload_link"]))
    return rows.filter(has_text=assignment).count() > 0


def go_to_upload_form(page, subject_url, assignment=None):
    """Subject page -> Pending Submission -> the chosen row's submit link -> file input."""
    page.goto(subject_url)
    page.click(SELECTORS["pending_tab"])

    rows = page.locator("tr").filter(has=page.locator(SELECTORS["upload_link"]))
    rows.first.wait_for(timeout=15_000)

    if assignment:
        rows = rows.filter(has_text=assignment)
        if rows.count() == 0:
            sys.exit(f"No pending assignment matches '{assignment}'.")
    elif rows.count() > 1:
        names = [row.locator("td").nth(1).inner_text().strip() for row in rows.all()]
        sys.exit("Several pending assignments found, use --assignment with part of a name:\n  "
                 + "\n  ".join(names))

    rows.first.locator(SELECTORS["upload_link"]).click()
    page.wait_for_selector(SELECTORS["file_input"], state="attached", timeout=15_000)


# ------------------------------------------------------------------------- Main
def main():
    parser = argparse.ArgumentParser(description="Upload an assignment to the LMS")
    parser.add_argument("--subject", help="Short subject name from your setup (e.g. fcp)")
    parser.add_argument("--file", help="File name inside the Assignment folder (default: newest)")
    parser.add_argument("--assignment", help="Part of the assignment name, e.g. 'Unit:3'")
    parser.add_argument("--setup", action="store_true", help="Run the setup questions (folder, subjects)")
    parser.add_argument("--list", action="store_true", help="Only list pending assignments")
    parser.add_argument("--headless", action="store_true", help="Run without a visible browser")
    parser.add_argument("--dry-run", action="store_true", help="Do everything except click submit")
    args = parser.parse_args()

    if args.setup:
        run_setup()
        return

    config = load_config()  # runs the setup questions on the very first launch
    subjects = config["subjects"]

    if not args.subject:
        parser.error("--subject is required (or run with --setup)")
    if args.subject not in subjects:
        known = ", ".join(subjects) or "none yet"
        sys.exit(f"Unknown subject '{args.subject}'. Known subjects: {known}. Add one with --setup.")

    if not USERNAME or not PASSWORD:
        sys.exit("Set the LMS_USERNAME and LMS_PASSWORD environment variables first.")

    if not args.list and not args.dry_run and not args.assignment:
        sys.exit("Use --assignment for a real upload, so the result can be verified.")

    subject = subjects[args.subject]
    file_path = None if args.list else pick_file(config, subject["folder"], args.file)
    if file_path:
        print(f"Will upload: {file_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        try:
            login(page)
            if args.list:
                list_pending(page, subject["url"])
                return
            go_to_upload_form(page, subject["url"], args.assignment)
            page.set_input_files(SELECTORS["file_input"], str(file_path))

            # The page's visible file box may not update, so ask the input itself what it holds
            attached = page.eval_on_selector(
                SELECTORS["file_input"], "el => el.files.length ? el.files[0].name : ''"
            )
            if attached != file_path.name:
                raise RuntimeError(f"File was not attached to the form (form has: '{attached}').")
            print(f"File attached in the form: {attached}")

            if args.dry_run:
                page.wait_for_timeout(1000)  # let the page show the chosen file name
                SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(SCREENSHOT_PATH.with_name("dry_run_form.png")))

                # Save the form's inputs/buttons so selectors can be checked (no right-click needed)
                elements = page.locator("input:not([type='hidden']), button, textarea").evaluate_all(
                    "els => els.map(e => e.outerHTML.slice(0, 300))"
                )
                dump = SCREENSHOT_PATH.with_name("form_elements.txt")
                dump.write_text("\n\n".join(elements), encoding="utf-8")

                print(f"Dry run: file selected, submit NOT clicked. Saved {dump}")
                page.wait_for_timeout(3000)
                return

            SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

            page.click(SELECTORS["submit_button"])
            try:  # the site asks "Are you sure want to Submit Assignment?"
                page.click(SELECTORS["confirm_yes"], timeout=10_000)
            except PlaywrightTimeout:
                page.screenshot(path=str(SCREENSHOT_PATH))
                raise RuntimeError(f"Confirmation 'Yes' button not found. Screenshot: {SCREENSHOT_PATH}")
            page.wait_for_load_state("networkidle")

            page.screenshot(path=str(SCREENSHOT_PATH))  # what the page showed after submit

            if is_still_pending(page, subject["url"], args.assignment):
                raise RuntimeError(
                    f"'{args.assignment}' is still pending, so the upload did not go through. "
                    f"Screenshot: {SCREENSHOT_PATH}"
                )
            print(f"Success: {file_path.name} uploaded, and the assignment left the pending list.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()

# ------------------------------------------------------------------- Setup notes
# 1. Install:
#        pip install -r requirements.txt
#        playwright install chromium
# 2. Set credentials (never hardcode them). Command Prompt, current window:
#        set LMS_USERNAME=your-enrollment-no
#        set "LMS_PASSWORD=your-password"
#    Permanent (open a new terminal afterwards):
#        setx LMS_USERNAME "your-enrollment-no"
#        setx LMS_PASSWORD "your-password"
# 3. First run asks for your folder path and subjects (or run: python lms_upload.py --setup)
# 4. Test first with:  python lms_upload.py --subject fcp --dry-run
