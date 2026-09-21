# LMS Assignment Automation Tool

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Playwright](https://img.shields.io/badge/automation-Playwright-45ba4b)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

A small command-line tool that uploads your finished assignments to the **RNGPIT LMS** (GNUMS student portal) for you. Instead of clicking through *LMS → subject → Pending Submission → Submit → confirm* for every assignment, you run one command and watch the browser do it.

> **Note:** This tool automates *your own* account, the same clicks you would make by hand. Use it only for your own submissions and follow your college's rules.

---

## Demo

<!-- Add your demo video here. Easiest way: edit this README on GitHub, drag the video
     file into the editor, and GitHub inserts a playable link. Or use a GIF: ![Demo](docs/demo.gif) -->

**Demo video:** _coming soon_

---

## Features

- **Student login handled for you**: selects the *Student* role, fills in your credentials, and waits for the dashboard to load.
- **Guided first-run setup**: asks for your folder path and subjects, so there's no code to edit and no required folder layout.
- **Subject shortcuts**: `--subject fcp`, `--subject calculus`, etc. Each short name maps to its LMS page and to a local folder.
- **`--list` mode**: shows the pending assignments for a subject, so you know what name to pass.
- **Picks the right assignment row**: matches part of the assignment name shown on the LMS (`--assignment "Unit:3"`).
- **Automatic file choice**: uses the newest file in the subject's `Assignment` folder, or the exact file you name with `--file`.
- **Checks the file is attached**: before submitting, it confirms the form really holds your file and stops if not (the page's own file box doesn't always show the name).
- **`--dry-run` mode**: does everything except click **Submit**, and saves a screenshot and the form's HTML for checking.
- **Handles the confirmation pop-up**: clicks *Yes* on "Are you sure want to Submit Assignment?".
- **Verifies the result**: after submitting, it reopens *Pending Submission* and only reports success if the assignment is gone. Otherwise it saves a screenshot and raises an error.
- **Credentials stay out of the code**: read from environment variables.

---

## How it works

```
Login page  ->  choose "Student"  ->  fill username + password
   ->  subject page  ->  "Pending Submission" tab  ->  "Click here to submit" on the chosen row
   ->  attach file  ->  Submit  ->  confirm "Yes"  ->  re-check the pending list
```

The browser runs headed (visible) by default, so you can watch each step.

---

## Screenshots

<!-- Blur your name and enrollment number before adding screenshots. -->

| Step | Screenshot |
|---|---|
| Listing pending assignments | ![List pending](docs/screenshots/list-pending.png) |
| Dry run: file attached, nothing submitted | ![Dry run](docs/screenshots/dry-run.png) |
| Successful upload | ![Success](docs/screenshots/success.png) |

---

## Requirements

- Windows, macOS or Linux (the examples below use Windows Command Prompt)
- Python 3.8 or newer
- [Playwright](https://playwright.dev/python/) with the Chromium browser
- A student account on the RNGPIT LMS

---

## Installation

```bash
git clone https://github.com/<your-username>/LMS-Assignment-Automation-Tool.git
cd LMS-Assignment-Automation-Tool

pip install -r requirements.txt
playwright install chromium
```

---

## Configuration

### 1. Credentials (environment variables)

The script reads `LMS_USERNAME` and `LMS_PASSWORD`. It never stores them in a file.

**Command Prompt (current window only):**
```
set LMS_USERNAME=your-enrollment-no
set "LMS_PASSWORD=your-password"
```

**Command Prompt (permanent, then open a new window):**
```
setx LMS_USERNAME "your-enrollment-no"
setx LMS_PASSWORD "your-password"
```

**PowerShell (current window only):**
```
$env:LMS_USERNAME = "your-enrollment-no"
$env:LMS_PASSWORD = "your-password"
```

**macOS / Linux:**
```
export LMS_USERNAME="your-enrollment-no"
export LMS_PASSWORD="your-password"
```

### 2. First-run setup (your folder and subjects)

You don't need to edit any code or copy a specific folder layout. The first time you run the script, it asks a few questions and saves your answers to `config.json` next to the script. You can run the questions again at any time, for example to add a subject:

```
python lms_upload.py --setup
```

Example session:

```
Folder that contains your subject folders: D:\College\SEM 1
Name of the assignments folder inside each subject folder [Assignment]:

Now add your subjects. Press Enter on the short name to finish.
Short name (e.g. fcp): fcp
Folder name for 'fcp' inside D:\College\SEM 1 [FCP]:
LMS subject page URL (copy it from the browser address bar): https://rngpit.gnums.co.in/...
Saved subject 'fcp'.
Short name (e.g. fcp):
```

Your files are then expected at `<base folder>\<subject folder>\<assignments folder>\`, for example:

```
D:\College\SEM 1\
├── CALCULUS\
│   └── Assignment\
│       └── 2SH103 Unit 3.pdf
├── FCP\
│   └── Assignment\
└── ...
```

**How to get a subject's URL:** log in to the LMS, open the subject, and copy the address bar. These links may stop working after a while; if a subject page shows an error, copy a fresh one and run `--setup` again with the same short name to replace it.

`config.json` holds your personal paths and links, so it is listed in `.gitignore` and won't be committed.

### 3. Selectors (only if the LMS changes)

All page selectors live in the `SELECTORS` dictionary at the top of the script. If the LMS is redesigned and a step fails, update the matching entry there. `playwright codegen https://rngpit.gnums.co.in/Login.aspx` records selectors for you.

---

## Usage

```bash
# 0. First time only: answer the setup questions (also runs automatically on first launch)
python lms_upload.py --setup

# 1. See which assignments are pending for a subject
python lms_upload.py --subject fcp --list

# 2. Dry run: opens the form and selects the file, but does NOT submit
python lms_upload.py --subject fcp --assignment "Unit:3" --file "Unit3.pdf" --dry-run

# 3. Real upload
python lms_upload.py --subject fcp --assignment "Unit:3" --file "Unit3.pdf"
```

### Options

| Option | Required | Description |
|---|---|---|
| `--subject` | Yes (except with `--setup`) | Short name you chose during setup (e.g. `fcp`) |
| `--setup` | No | Run the setup questions (base folder, subjects) and save them to `config.json` |
| `--assignment` | For real uploads | Part of the assignment name shown on the LMS (case-insensitive). Copy it exactly, including punctuation such as `Unit:3` |
| `--file` | No | File name (with extension) inside the subject's `Assignment` folder. Defaults to the newest file |
| `--list` | No | Only list pending assignments and exit |
| `--dry-run` | No | Do everything except click Submit; saves a screenshot and form HTML to `~/assignments/` |
| `--headless` | No | Run without a visible browser. Confirm everything works headed (and with `--dry-run`) first |

> Tip: always pass `--file` when several assignments are pending, so the newest file is not uploaded to the wrong assignment.

---

## Project structure

```
LMS-Assignment-Automation-Tool/
├── lms_upload.py        # the whole tool
├── config.json          # created by the setup questions (not committed)
├── requirements.txt
├── README.md
├── .gitignore
└── docs/
    └── screenshots/     # images used in this README
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `unrecognized arguments: --list` | You're running an older copy of the script | Replace it with the latest `lms_upload.py`, check with `python lms_upload.py -h` |
| `can't open file ... lms_upload.py` | Terminal is in the wrong folder, or the file name differs | `cd` to the script's folder (`cd /d D:\...` on Windows) and check with `dir` |
| "Set the LMS_USERNAME and LMS_PASSWORD..." | Variables not set in this window | Set them again; after `setx`, open a new terminal |
| "Invalid Username or Password" on the login page | Wrong password saved, or the wrong role was selected | Re-run `setx` with the right password; the script selects *Student* automatically |
| "Unknown subject ..." | That short name isn't in your config | Run `python lms_upload.py --setup` and add it |
| "File not found" / "No files found" | The file isn't in `<base folder>\<subject folder>\<assignments folder>` | Check the paths saved in `config.json`, or re-run `--setup` |
| Script waits about 2 minutes at login, then times out | Login failed (wrong credentials) or the LMS asked for extra verification | Check your environment variables; if the LMS asks for anything extra, complete it in the browser window |
| "Several pending assignments found" | More than one pending assignment | Add `--assignment` with part of a name (see `--list`) |
| "Confirmation 'Yes' button not found" | The pop-up looks different | Check the saved screenshot and update `confirm_yes` in `SELECTORS` |
| "... is still pending, so the upload did not go through" | Submission was rejected | Check `~/assignments/screenshot_fallback.png`. Allowed types are doc, docx, pdf, zip, xlsx, max 25 MB |

---

## Security and privacy

- **Never commit your password.** It is read from environment variables only.
- Environment variables set with `setx` are stored unencrypted in your Windows user profile. Use this only on a personal computer.
- Don't publish screenshots that show your name, enrollment number or session IDs; blur them first.
- Your subject URLs contain IDs tied to your account. They are saved only in your local `config.json`, which is git-ignored. Don't commit it.

---

## Limitations

- Built for the RNGPIT LMS (GNUMS). Other portals need different selectors.
- If the LMS ever adds a CAPTCHA or two-factor step to login, you must complete it by hand in the browser window (the script waits up to 2 minutes).
- Uploads one file to one assignment per run.
- If the LMS layout changes, selectors may need updating.

---

## Disclaimer

This is a personal automation project for convenience. It is not affiliated with RNGPIT or GNUMS. You are responsible for what you submit and for following your institution's policies. Always check the LMS after an upload to confirm it went through.
