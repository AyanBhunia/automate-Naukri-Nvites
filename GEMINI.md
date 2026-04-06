# GEMINI.md - Naukri NVites Automation Context

## Project Overview
**Naukri NVites Automation** is a production-grade Python tool designed to automate the job application process on the Naukri.com "NVites" platform. It leverages **Playwright** to navigate the user's inbox, filter out irrelevant or promotional content, and apply to job opportunities.

### Main Technologies
- **Python 3.10+**: Core programming language.
- **Playwright (Sync API)**: Browser automation engine.
- **Chromium**: The underlying browser used for automation.
- **Windows Task Scheduler**: Used for daily automated execution via `run_daily.bat`.

### Architecture & Key Features
- **Persistent Sessions**: Uses a local `./user_data` directory to store cookies and local storage, bypassing repetitive logins and CAPTCHAs after the initial setup.
- **Human-Like Interaction**: Employs coordinate-based mouse movements and clicks (`page.mouse.click`) to navigate the SPA and avoid bot detection.
- **Smart Filtering**: Automatically identifies and skips "Sponsored" ads, "Naukri Pro" widgets, and jobs marked as "Applied".
- **Cognitive Knowledge Base**: Contains a dictionary of common application questions (notice period, CTC, etc.) to assist in future form-filling automation.
- **Resilient Navigation**: Handles dynamic shimmers, loading states, and chatbot overlays (`.chatbot_Overlay`).

---

## Building and Running

### Prerequisites
- Python 3.8 or higher.
- Playwright dependencies.

### Key Commands
- **Install Dependencies**:
  ```powershell
  pip install playwright
  playwright install chromium
  ```
- **Run Manually**:
  ```powershell
  python naukri_automation.py
  ```
- **Scheduled Run**:
  Execute `run_daily.bat` or verify the "NaukriAutomation" task in Windows Task Scheduler:
  ```powershell
  schtasks /Query /TN "NaukriAutomation"
  ```

### First-Run Protocol
The first execution must be performed in non-headless mode (default) to allow for **manual login**. Once the user logs in and navigates to the inbox, the session is saved to `./user_data` for subsequent automated runs.

---

## Development Conventions

### Coding Style
- **Sync Playwright**: The project uses the synchronous version of the Playwright API.
- **Modular Functions**: Logic is divided into specialized functions:
  - `login_check(page)`: Validates session state.
  - `wait_for_shimmers(page)`: Handles dynamic loading.
  - `get_valid_cards(page)`: Implements job filtering logic.
  - `process_job_application(...)`: Orchestrates the click-and-apply flow for a single job.
- **Error Handling**: Uses broad try-except blocks to ensure the script continues processing the next job even if one fails.

### Key Files
- `naukri_automation.py`: The entry point and core logic.
- `run_daily.bat`: Wrapper for automated execution.
- `user_data/`: **CRITICAL** - Stores the persistent browser profile. Do not delete unless a fresh login is required.
- `README.md`: High-level user documentation.

### Troubleshooting / Debugging
- If clicks are failing, check the bounding box logic in `process_job_application`.
- If "Applied" status is misidentified, verify the `.inbox-company-card` inner text parsing logic.
- The script stays open after completion to allow manual review; use `Ctrl+C` to terminate.
