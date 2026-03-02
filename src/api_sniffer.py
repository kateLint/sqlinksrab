"""
API Sniffer module - captures portal network requests using Playwright.
Intercepts XHR/fetch requests to discover the portal's internal API endpoints.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.sync_api import (
    sync_playwright, Page, Request, Response,
    TimeoutError as PlaywrightTimeout
)

try:
    from .ui_selectors import Selectors
    from .config import Config
except ImportError:
    from ui_selectors import Selectors
    from config import Config


class APISniffer:
    """Captures and logs network requests from the HRM portal."""

    def __init__(self, config: Config, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.captured_requests: list = []
        self.page: Optional[Page] = None

    def _on_request(self, request: Request):
        """Callback for intercepted requests."""
        # Only capture XHR/fetch, skip static assets
        resource_type = request.resource_type
        if resource_type in ("xhr", "fetch", "document"):
            entry = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "url": request.url,
                "resource_type": resource_type,
                "headers": dict(request.headers),
                "post_data": None,
            }
            try:
                entry["post_data"] = request.post_data
            except Exception:
                pass

            self.captured_requests.append(entry)
            print(f"  [{request.method}] {request.url[:100]}")

    def _on_response(self, response: Response):
        """Callback for intercepted responses."""
        # Match response to captured request
        for entry in reversed(self.captured_requests):
            if entry["url"] == response.url and "status" not in entry:
                entry["status"] = response.status
                entry["status_text"] = response.status_text
                entry["response_headers"] = dict(response.headers)

                # Try to capture response body for API calls
                try:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type or "text" in content_type:
                        body = response.text()
                        # Truncate large responses
                        if len(body) > 5000:
                            entry["response_body"] = body[:5000] + "... [truncated]"
                        else:
                            entry["response_body"] = body
                        # Try to parse as JSON
                        try:
                            entry["response_json"] = json.loads(body)
                        except (json.JSONDecodeError, ValueError):
                            pass
                except Exception:
                    pass
                break

    def sniff(self) -> str:
        """
        Main sniffing flow:
        1. Login to portal (with OTP)
        2. Navigate around the calendar
        3. Open a day entry form
        4. Capture all network traffic
        5. Save to JSON file
        """
        playwright = sync_playwright().start()

        try:
            browser = playwright.chromium.launch(
                headless=False,
                slow_mo=100
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="he-IL",
                timezone_id="Asia/Jerusalem"
            )
            self.page = context.new_page()
            self.page.set_default_timeout(self.config.timeout_seconds * 1000)

            # Attach network listeners
            self.page.on("request", self._on_request)
            self.page.on("response", self._on_response)

            print("=" * 60)
            print("  API SNIFFER - Capturing portal network traffic")
            print("=" * 60)

            # Step 1: Login
            print("\n--- Step 1: Login ---")
            self.page.goto(self.config.base_url, wait_until="networkidle")
            self.page.wait_for_selector(Selectors.LOGIN_PASSWORD, timeout=15000)

            id_field = self.page.query_selector(Selectors.LOGIN_EMPLOYEE_ID)
            if id_field:
                id_field.fill(self.config.employee_id)
            pwd_field = self.page.query_selector(Selectors.LOGIN_PASSWORD)
            if pwd_field:
                pwd_field.fill(self.config.password)

            submit = self.page.query_selector(Selectors.LOGIN_SUBMIT)
            if submit:
                submit.click()
            else:
                self.page.keyboard.press("Enter")

            # Wait for OTP
            time.sleep(3)
            try:
                self.page.wait_for_selector(
                    f"{Selectors.CURRENT_MONTH_BUTTON}, {Selectors.NAV_HOME}",
                    timeout=3000
                )
            except PlaywrightTimeout:
                print("\nOTP REQUIRED - Enter OTP in the browser window.")
                print(f"Waiting up to {self.config.otp_timeout} seconds...\n")
                try:
                    self.page.wait_for_selector(
                        f"{Selectors.CURRENT_MONTH_BUTTON}, {Selectors.NAV_HOME}",
                        timeout=self.config.otp_timeout * 1000
                    )
                except PlaywrightTimeout:
                    print("OTP timeout. Saving captured requests anyway.")
                    return self._save_results()

            print("\nLogged in successfully!")

            # Step 2: Navigate to attendance via sidebar
            print("\n--- Step 2: Navigating to attendance ---")
            time.sleep(2)

            # Click "אזור אישי" then "נוכחות"
            personal = self.page.query_selector(Selectors.NAV_PERSONAL)
            if personal:
                print("  Clicking 'אזור אישי'...")
                personal.click()
                time.sleep(1.5)

            attendance = self.page.query_selector(Selectors.NAV_ATTENDANCE)
            if attendance:
                print("  Clicking 'נוכחות'...")
                attendance.click()
                time.sleep(2)

            # Step 3: Navigate calendar
            print("\n--- Step 3: Navigating calendar ---")
            time.sleep(2)

            # Click previous month arrow a couple times
            arrows = self.page.query_selector_all("button:has(svg)")
            if len(arrows) >= 2:
                print("  Clicking prev month...")
                arrows[0].click()
                time.sleep(2)
                print("  Clicking next month...")
                arrows[-1].click()
                time.sleep(2)

            # Step 4: Click on a day
            print("\n--- Step 4: Clicking on a day ---")
            # Try to click on day 1
            try:
                day_elem = self.page.locator(":text-is('01')").first
                day_elem.click()
                time.sleep(2)
            except Exception as e:
                print(f"  Could not click day: {e}")

            # Step 5: Try to open add report form
            print("\n--- Step 5: Opening entry form ---")
            try:
                add_btn = self.page.query_selector(Selectors.ADD_REPORT_BUTTON)
                if add_btn:
                    add_btn.click()
                    time.sleep(2)

                    # Cancel to not actually submit
                    cancel = self.page.query_selector(Selectors.FORM_CANCEL)
                    if cancel:
                        cancel.click()
                        time.sleep(1)
            except Exception as e:
                print(f"  Form interaction error: {e}")

            # Step 6: Save results
            print("\n--- Step 6: Saving captured traffic ---")
            return self._save_results()

        finally:
            browser.close()
            playwright.stop()

    def _save_results(self) -> str:
        """Save captured requests to JSON file."""
        output_file = self.output_dir / f"api_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Group by endpoint type
        api_summary = {
            "captured_at": datetime.now().isoformat(),
            "total_requests": len(self.captured_requests),
            "endpoints": {},
            "requests": self.captured_requests
        }

        # Group endpoints
        for req in self.captured_requests:
            url = req["url"]
            method = req["method"]
            key = f"{method} {url.split('?')[0]}"  # Strip query params for grouping
            if key not in api_summary["endpoints"]:
                api_summary["endpoints"][key] = {
                    "method": method,
                    "url": url.split("?")[0],
                    "count": 0,
                    "statuses": []
                }
            api_summary["endpoints"][key]["count"] += 1
            if "status" in req:
                api_summary["endpoints"][key]["statuses"].append(req["status"])

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(api_summary, f, ensure_ascii=False, indent=2, default=str)

        print(f"\nCaptured {len(self.captured_requests)} requests")
        print(f"Found {len(api_summary['endpoints'])} unique endpoints")
        print(f"Saved to: {output_file}")

        # Print summary
        print("\nDiscovered API Endpoints:")
        print("-" * 60)
        for key, info in sorted(api_summary["endpoints"].items()):
            statuses = set(info["statuses"])
            print(f"  {info['method']:6s} {info['url'][:80]} (x{info['count']}, status: {statuses})")

        return str(output_file)


def run_sniffer(config: Config) -> int:
    """Entry point for sniff mode from main.py."""
    print("API SNIFF MODE: Capturing portal network requests\n")
    sniffer = APISniffer(config)
    try:
        output = sniffer.sniff()
        print(f"\nSniffing complete. Results: {output}")
        return 0
    except Exception as e:
        print(f"Sniffer error: {e}")
        import traceback
        traceback.print_exc()
        return 1
