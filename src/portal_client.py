"""
Portal automation client using Playwright.
Handles login, OTP verification, calendar navigation, and timesheet entry.
"""

import time
from typing import Optional, Tuple
from pathlib import Path
from playwright.sync_api import (
    sync_playwright, Page, Browser, BrowserContext,
    TimeoutError as PlaywrightTimeout
)

try:
    from .ui_selectors import Selectors, HEBREW_MONTHS
    from .config import Config
    from .pdf_extractor import TimesheetRecord
except ImportError:
    from ui_selectors import Selectors, HEBREW_MONTHS
    from config import Config
    from pdf_extractor import TimesheetRecord


class PortalClient:
    """Automation client for HRM portal with SPA calendar UI."""

    def __init__(self, config: Config):
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Start browser and create page."""
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=100
        )

        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="he-IL",
            timezone_id="Asia/Jerusalem"
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config.timeout_seconds * 1000)

    def close(self):
        """Close browser and cleanup."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    # =====================================================================
    # LOGIN + OTP
    # =====================================================================

    def login(self) -> bool:
        """
        Log into the HRM portal with OTP support.

        Flow:
        1. Navigate to portal
        2. Enter employee ID and password
        3. Submit credentials
        4. Wait for OTP input (user enters manually in the browser)
        5. Detect successful login (calendar page loads)
        """
        try:
            print("Navigating to portal login...")
            self.page.goto(self.config.base_url, wait_until="networkidle")

            # Wait for login form
            print("Waiting for login form...")
            self.page.wait_for_selector(
                Selectors.LOGIN_PASSWORD, timeout=15000
            )

            # Fill credentials
            print("Entering credentials...")
            # Find the employee ID field (first text/tel input before password)
            id_field = self.page.query_selector(Selectors.LOGIN_EMPLOYEE_ID)
            if id_field:
                id_field.click()
                id_field.fill(self.config.employee_id)

            pwd_field = self.page.query_selector(Selectors.LOGIN_PASSWORD)
            if pwd_field:
                pwd_field.click()
                pwd_field.fill(self.config.password)

            # Submit
            print("Submitting login...")
            submit_btn = self.page.query_selector(Selectors.LOGIN_SUBMIT)
            if submit_btn:
                submit_btn.click()
            else:
                # Try pressing Enter as fallback
                self.page.keyboard.press("Enter")

            time.sleep(2)

            # Handle OTP (or detect that we're already logged in)
            if not self._handle_otp():
                return False

            print("Login successful!")
            return True

        except PlaywrightTimeout as e:
            print(f"Login timeout: {e}")
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def _is_logged_in(self) -> bool:
        """Check if we're on a post-login page by looking for known elements."""
        checks = [
            Selectors.CURRENT_MONTH_BUTTON,  # "חודש נוכחי" on calendar
            Selectors.NAV_ATTENDANCE,         # "נוכחות" in sidebar
            "text=עמוד הבית",                  # "עמוד הבית" in sidebar
            "text=אזור אישי",                  # "אזור אישי" in sidebar
            "text=SQlink",                     # Brand logo visible in screenshot
        ]
        for selector in checks:
            try:
                el = self.page.query_selector(selector)
                if el:
                    return True
            except Exception:
                continue
        return False

    def _handle_otp(self) -> bool:
        """
        Handle OTP verification step.
        Pauses automation and prompts user to enter OTP manually in the browser,
        then waits for the page to transition to the main app.
        """
        # Give the page a moment to potentially redirect to OTP or main page
        time.sleep(3)

        # Check if we're already past OTP
        if self._is_logged_in():
            print("Already logged in - no OTP needed")
            return True

        # OTP page likely showing
        print("\n" + "=" * 50)
        print("  OTP VERIFICATION REQUIRED")
        print("=" * 50)
        print("  An OTP code has been sent to your phone.")
        print("  Please enter the OTP in the browser window.")
        print(f"  Waiting up to {self.config.otp_timeout} seconds...")
        print("=" * 50 + "\n")

        # Poll for login success (check every 2 seconds)
        elapsed = 0
        interval = 2
        while elapsed < self.config.otp_timeout:
            time.sleep(interval)
            elapsed += interval
            if self._is_logged_in():
                print("OTP verified successfully!")
                return True

        print("OTP timeout - user did not complete verification.")
        return False

    # =====================================================================
    # CALENDAR NAVIGATION
    # =====================================================================

    def _is_calendar_visible(self) -> bool:
        """Check if the attendance calendar is already visible on the page."""
        # Look for calendar-specific elements
        checks = [
            Selectors.CURRENT_MONTH_BUTTON,  # "חודש נוכחי"
            "text=יום ראשון",                  # Day-of-week header
            "text=יום שני",
            "text=יום שבת",
        ]
        for selector in checks:
            try:
                el = self.page.query_selector(selector)
                if el:
                    return True
            except Exception:
                continue
        return False

    def _navigate_to_attendance(self) -> bool:
        """
        Navigate from the post-login page to the attendance/calendar view.
        The portal typically auto-navigates to the calendar after OTP login.
        Check the URL first, then fall back to sidebar navigation if needed.
        """
        try:
            print("Navigating to attendance view...")

            # Wait a bit for any post-OTP redirects to complete
            time.sleep(5)

            # Check if we're already on the calendar page by URL
            current_url = self.page.url
            print(f"  Current URL: {current_url}")
            
            if "/timesheets/timesheets-report/calendar" in current_url:
                print(f"  Already on calendar page!")
                return True

            # Check if calendar is already visible (auto-navigation after OTP)
            if self._is_calendar_visible():
                print("  Calendar already visible - skipping sidebar navigation")
                return True

            # If not on calendar, navigate via sidebar
            print("  Navigating via sidebar menu...")
            
            # Step 1: Ensure "איזור אישי" (Personal Area) is expanded
            # First check if it's already expanded by looking for the attendance link
            attendance_link = self.page.query_selector("a[href='/timesheets/timesheets-report/calendar']")
            
            if not attendance_link:
                # Need to expand the Personal Area menu
                personal_area_selectors = [
                    "div.v-list-item:has-text('איזור אישי')",
                    "text=איזור אישי",
                    Selectors.NAV_PERSONAL
                ]
                
                for selector in personal_area_selectors:
                    try:
                        personal_area = self.page.query_selector(selector)
                        if personal_area:
                            print(f"  Clicking 'איזור אישי' to expand menu...")
                            personal_area.click(timeout=5000)
                            time.sleep(1.5)
                            break
                    except Exception as e:
                        print(f"  Could not click 'איזור אישי' with selector {selector}: {e}")
                        continue

            # Step 2: Click the "נוכחות" (Attendance) link
            # Use the href selector which is most reliable
            attendance_selectors = [
                "a[href='/timesheets/timesheets-report/calendar']",
                "a[href*='timesheets-report/calendar']",
                "div.v-list-item:has-text('נוכחות') a",
                "text=נוכחות"
            ]
            
            for selector in attendance_selectors:
                try:
                    attendance = self.page.query_selector(selector)
                    if attendance:
                        print(f"  Clicking 'נוכחות' using selector: {selector}")
                        attendance.click(timeout=5000)
                        time.sleep(3)
                        break
                except Exception as e:
                    print(f"  Failed with selector {selector}: {e}")
                    continue

            # Verify calendar loaded
            time.sleep(2)
            current_url = self.page.url
            print(f"  Final URL: {current_url}")
            
            if self._is_calendar_visible() or "/timesheets/timesheets-report/calendar" in current_url:
                print("  Attendance calendar loaded!")
                return True

            print("  Calendar did not load after navigation")
            return False

        except Exception as e:
            print(f"  Attendance navigation error: {e}")
            return False

    def navigate_to_timesheet(self) -> bool:
        """
        Navigate to the correct month in the calendar view.
        First navigates to attendance section, then uses month arrows.
        """
        try:
            print(f"Navigating to timesheet for {self.config.target_month}...")

            # First navigate to the attendance/calendar view
            if not self._navigate_to_attendance():
                return False

            # Wait for calendar to stabilize
            time.sleep(2)

            target_year, target_month = map(int, self.config.target_month.split("-"))
            target_month_name = HEBREW_MONTHS[target_month]

            max_attempts = 24
            for attempt in range(max_attempts):
                # Read current month/year from the page
                current_text = self._get_current_month_text()
                print(f"  Current view: {current_text}")

                if target_month_name in current_text and str(target_year) in current_text:
                    print(f"Reached target month: {target_month_name} {target_year}")
                    return True

                # Determine which direction to click based on target vs current
                # Parse current month from the text
                current_month_num = None
                current_year_num = None
                
                for month_num, month_name in HEBREW_MONTHS.items():
                    if month_name in current_text:
                        current_month_num = month_num
                        break
                
                # Extract year from current_text
                import re
                year_match = re.search(r'\\d{4}', current_text)
                if year_match:
                    current_year_num = int(year_match.group())
                
                # Determine direction
                if current_year_num and current_month_num:
                    # Compare dates: if target is before current, go prev, else go next
                    if target_year < current_year_num or (target_year == current_year_num and target_month < current_month_num):
                        direction = "prev"
                    else:
                        direction = "next"
                else:
                    # Fallback: assume we need to go back (most common case)
                    direction = "prev"
                
                self._click_month_arrow(direction=direction)
                time.sleep(1.5)

            print("Could not navigate to target month after max attempts")
            return False

        except Exception as e:
            print(f"Navigation error: {e}")
            return False

    def _get_current_month_text(self) -> str:
        """Read the current month/year text from the calendar header."""
        try:
            # Look for text that contains a year (4 digits)
            # The header shows something like "ינואר 2026" or "פברואר 2026"
            for month_name in HEBREW_MONTHS.values():
                element = self.page.query_selector(f"text=/{month_name}.*\\d{{4}}/")
                if element:
                    return element.inner_text()
                element = self.page.query_selector(f"text=/\\d{{4}}.*{month_name}/")
                if element:
                    return element.inner_text()

            # Fallback: try to find any element with a year
            header = self.page.query_selector(Selectors.MONTH_YEAR_HEADER)
            if header:
                return header.inner_text()

            return ""
        except Exception:
            return ""

    def _click_month_arrow(self, direction: str = "prev"):
        """
        Click the month navigation arrow.
        direction: 'prev' to go to previous month, 'next' for next month.
        """
        try:
            # Use aria-label selectors which are most reliable
            if direction == "prev":
                selector = "button.page-month-picker__btn[aria-label='חודש קודם']"
            else:
                selector = "button.page-month-picker__btn[aria-label='חודש הבא']"
            
            btn = self.page.query_selector(selector)
            if btn:
                print(f"  Clicking {direction} month arrow...")
                btn.click()
                time.sleep(2)  # Wait for calendar to update
            else:
                print(f"  {direction} month arrow not found")
        except Exception as e:
            print(f"  Arrow click error: {e}")

    # =====================================================================
    # DAY INTERACTION
    # =====================================================================

    def _click_day(self, day: int) -> bool:
        """
        Click on a specific day number in the calendar grid.
        Returns True if the day cell was found and clicked.
        """
        try:
            # Use the date-specific class selector which is most reliable
            # Format: div.cv-day.dYYYY-MM-DD
            year, month = map(int, self.config.target_month.split("-"))
            date_class = f"d{year:04d}-{month:02d}-{day:02d}"
            selector = f"div.cv-day.{date_class}"
            
            cell = self.page.query_selector(selector)
            if cell:
                print(f"  Clicking day {day}...")
                cell.click()
                time.sleep(2)  # Wait for side panel to update
                return True
            
            print(f"  Day cell not found for day {day} (selector: {selector})")
            return False

        except Exception as e:
            print(f"  Error clicking day {day}: {e}")
            return False

    def _check_existing_report(self) -> bool:
        """
        Check if the currently selected day already has a report.
        Returns True if a report already exists for this day.
        """
        try:
            no_reports = self.page.query_selector(Selectors.NO_REPORTS_MESSAGE)
            return no_reports is None
        except Exception:
            return False

    def _open_entry_form(self, has_existing: bool) -> bool:
        """
        Open the entry form for the selected day.
        Clicks "Add report" or "Edit" depending on whether a report exists.
        """
        try:
            if has_existing:
                btn = self.page.query_selector(Selectors.EDIT_BUTTON)
                if btn:
                    btn.click()
                else:
                    print("  Edit button not found")
                    return False
            else:
                # Try "הוספת דיווח" first, then "דיווח חדש"
                btn = self.page.query_selector(Selectors.ADD_REPORT_BUTTON)
                if not btn:
                    btn = self.page.query_selector(Selectors.NEW_REPORT_BUTTON)
                if btn:
                    btn.click()
                else:
                    print("  Add report button not found")
                    return False

            # Wait for the form to appear
            time.sleep(1.5)

            # Verify form appeared by checking for save button or entry time field
            save_btn = self.page.query_selector(Selectors.FORM_SAVE)
            if save_btn:
                return True

            print("  Entry form did not appear after clicking")
            return False

        except Exception as e:
            print(f"  Error opening entry form: {e}")
            return False

    def _fill_entry_form(self, record: TimesheetRecord) -> bool:
        """
        Fill the time entry form fields.
        """
        try:
            # Ensure "Work" radio is selected (usually default)
            try:
                work_label = self.page.query_selector(Selectors.REPORT_CODE_WORK_RADIO)
                if work_label:
                    work_label.click()
                    time.sleep(0.3)
            except Exception:
                pass  # May already be selected

            # Fill entry time (שעת כניסה)
            if record.start_time:
                filled = self._fill_time_field("entry", record.start_time)
                if not filled:
                    print(f"  Could not fill entry time: {record.start_time}")
                    return False

            # Fill exit time (שעת יציאה)
            if record.end_time:
                filled = self._fill_time_field("exit", record.end_time)
                if not filled:
                    print(f"  Could not fill exit time: {record.end_time}")
                    return False

            # Wait for total to calculate
            time.sleep(0.5)

            return True

        except Exception as e:
            print(f"  Error filling form: {e}")
            return False

    def _fill_time_field(self, field_type: str, time_value: str) -> bool:
        """
        Fill a time input field. Tries multiple strategies since
        time inputs in SPAs can be custom widgets.
        """
        if field_type == "entry":
            selector = Selectors.FORM_ENTRY_TIME
        else:
            selector = Selectors.FORM_EXIT_TIME

        try:
            field = self.page.query_selector(selector)
            if not field:
                # Fallback: find all inputs and pick by position
                inputs = self.page.query_selector_all("input[type='text'], input[type='time'], input:not([type])")
                # Entry time is typically the first time input, exit is second
                time_inputs = [inp for inp in inputs if self._looks_like_time_input(inp)]
                idx = 0 if field_type == "entry" else 1
                if len(time_inputs) > idx:
                    field = time_inputs[idx]

            if not field:
                return False

            # Try fill() first
            field.click()
            time.sleep(0.2)
            field.fill("")
            field.fill(time_value)
            time.sleep(0.3)

            # Verify value was set
            current_value = field.input_value()
            if current_value and time_value.replace(":", "") in current_value.replace(":", ""):
                return True

            # Fallback: clear and type character by character
            field.click(click_count=3)  # Select all
            time.sleep(0.1)
            self.page.keyboard.press("Backspace")
            self.page.keyboard.type(time_value, delay=80)
            time.sleep(0.3)

            return True

        except Exception as e:
            print(f"  Time field fill error ({field_type}): {e}")
            return False

    def _looks_like_time_input(self, element) -> bool:
        """Check if an element looks like a time input field."""
        try:
            # Check placeholder or nearby text for time-related content
            placeholder = element.get_attribute("placeholder") or ""
            input_type = element.get_attribute("type") or ""
            if input_type == "time":
                return True
            if "שעה" in placeholder or ":" in placeholder or "HH" in placeholder:
                return True
            # Check if it's near time-related labels
            return True  # Be permissive, filter by position
        except Exception:
            return False

    def _save_form(self) -> Tuple[str, str]:
        """Click save and verify the result."""
        try:
            save_btn = self.page.query_selector(Selectors.FORM_SAVE)
            if not save_btn:
                return "failed", "Save button not found"

            save_btn.click()
            time.sleep(2)

            # Check for error toast/message
            error = self.page.query_selector(Selectors.ERROR_TOAST)
            if error:
                try:
                    error_text = error.inner_text()
                    if error_text.strip():
                        return "failed", f"Save error: {error_text}"
                except Exception:
                    pass

            # If the form disappears (save button gone), consider it success
            save_still = self.page.query_selector(Selectors.FORM_SAVE)
            if not save_still:
                return "created", "Saved successfully"

            # Form still visible but no error - might have saved
            return "created", "Saved (form still visible, no error detected)"

        except Exception as e:
            return "failed", f"Save error: {str(e)}"

    def _reset_to_calendar(self):
        """Reset to clean calendar state by clicking cancel if form is open."""
        try:
            cancel = self.page.query_selector(Selectors.FORM_CANCEL)
            if cancel:
                cancel.click()
                time.sleep(0.5)
        except Exception:
            pass

    # =====================================================================
    # MAIN ENTRY POINT
    # =====================================================================

    def enter_timesheet_data(self, record: TimesheetRecord, dry_run: bool = False) -> Tuple[str, str]:
        """
        Enter timesheet data for a record.
        Flow: click day -> check existing -> open form -> fill -> save
        """
        date = record.work_date

        # Check for skip conditions
        if record.day_type in ["friday", "saturday"] and self.config.skip_weekends:
            return "skipped", f"Weekend ({record.day_type})"

        if "missing entry/exit" in record.notes.lower() and self.config.skip_missing_flags:
            return "skipped", f"Flagged: {record.notes}"

        if not record.start_time and not record.end_time and record.total_hours_decimal:
            if self.config.handle_total_hours_only == "skip_and_flag":
                return "skipped", "Total hours only - needs manual decision"

        if not record.start_time and not record.end_time and not record.total_hours_decimal:
            return "skipped", "No data to enter"

        # Extract day number
        day = int(date.split("-")[2])

        # Dry run mode
        if dry_run:
            return "created", f"[DRY RUN] Would create: entry={record.start_time}, exit={record.end_time}"

        # Click the day in calendar
        if not self._click_day(day):
            return "failed", f"Could not select day {day} in calendar"

        # Check if report already exists
        has_existing = self._check_existing_report()

        # Open form (edit if exists, new if not)
        if not self._open_entry_form(has_existing):
            self._reset_to_calendar()
            return "failed", "Could not open entry form"

        # Fill form
        if not self._fill_entry_form(record):
            self._reset_to_calendar()
            return "failed", "Could not fill entry form"

        # Save
        action, status = self._save_form()

        # Delay between entries for SPA stability
        time.sleep(self.config.inter_entry_delay)

        return action, status

    # =====================================================================
    # UTILITIES
    # =====================================================================

    def take_screenshot(self, filename: str) -> str:
        """Take a screenshot of the current page."""
        try:
            screenshot_path = self.config.report_directory / filename
            self.page.screenshot(path=str(screenshot_path))
            return str(screenshot_path)
        except Exception as e:
            print(f"Screenshot error: {e}")
            return ""

    def discover_selectors(self, output_path: str = "output/dom_dump.html"):
        """
        Dump the current page HTML for selector analysis.
        Useful for initial setup and debugging.
        """
        try:
            html = self.page.content()
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"DOM dumped to {output_path}")
            print(f"Page URL: {self.page.url}")
            print(f"Page title: {self.page.title()}")

            # Also take a screenshot
            self.page.screenshot(path=str(path.with_suffix('.png')))
            print(f"Screenshot saved to {path.with_suffix('.png')}")
        except Exception as e:
            print(f"DOM dump error: {e}")
