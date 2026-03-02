#!/usr/bin/env python3
"""
Main orchestrator for HRM portal timesheet automation.
Coordinates PDF extraction, portal automation, and audit reporting.
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from pdf_extractor import PDFExtractor
from portal_client import PortalClient
from reporting import ReportGenerator


def run_discover(config: Config):
    """Discovery mode: login and dump DOM for selector analysis."""
    print("DISCOVERY MODE: Will login and dump page DOM for selector analysis\n")

    with PortalClient(config) as portal:
        login_ok = portal.login()

        # Always dump DOM regardless of login result
        print(f"\nLogin {'successful' if login_ok else 'may have failed'}. Dumping DOM...")
        portal.discover_selectors("output/dom_dump_postlogin.html")

        if not login_ok:
            print("Login returned False, but DOM was dumped. Check the screenshot.")
            portal.take_screenshot("output/login_state.png")
            return 1

        # Try to navigate to attendance and dump that DOM too
        print("\nAttempting to navigate to attendance...")
        if portal._navigate_to_attendance():
            print("Navigation successful. Dumping attendance DOM...")
            portal.discover_selectors("output/dom_dump_attendance.html")
        else:
            print("Navigation failed. Check dom_dump_postlogin.html for page structure.")
            portal.take_screenshot("output/nav_failed_state.png")

        print("\nDiscovery complete. Check output/ for DOM dumps.")
        return 0


def main():
    """Main entry point for the automation."""

    parser = argparse.ArgumentParser(
        description="HRM Portal Timesheet Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run mode (no actual changes)
  python main.py --dry-run

  # Specify custom PDF file
  python main.py --pdf /path/to/timesheet.pdf

  # Discovery mode (login + dump DOM)
  python main.py --discover

  # Custom config file
  python main.py --config my_config.json
        """
    )

    parser.add_argument(
        "--config",
        default="../config.json",
        help="Path to config file (default: ../config.json)"
    )

    parser.add_argument(
        "--pdf",
        help="Path to PDF file (if not specified, uses mock data)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - log actions without making changes"
    )

    parser.add_argument(
        "--discover",
        action="store_true",
        help="Discovery mode - login and dump DOM for selector analysis"
    )

    parser.add_argument(
        "--sniff",
        action="store_true",
        help="API sniff mode - capture portal network requests"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("HRM PORTAL TIMESHEET AUTOMATION")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # Load configuration
        print("Loading configuration...")
        config_path = Path(args.config)
        if not config_path.exists():
            config_path = Path(__file__).parent.parent / "config.example.json"
            if not config_path.exists():
                print("ERROR: Config file not found!")
                print("Please copy config.example.json to config.json and update settings.")
                return 1

        config = Config(str(config_path))

        # Override config with CLI arguments
        if args.dry_run:
            config._config["automation"]["dry_run"] = True
            print("DRY RUN MODE: No changes will be made to the portal\n")

        # Always force headful for OTP
        config._config["automation"]["headless"] = False

        print(f"Target month: {config.target_month}")
        print(f"Portal URL: {config.base_url}")
        print(f"Employee ID: {config.employee_id}\n")

        # Discovery mode
        if args.discover:
            return run_discover(config)

        # Sniff mode
        if args.sniff:
            from api_sniffer import run_sniffer
            return run_sniffer(config)

        # Extract PDF data
        print("-" * 70)
        print("STEP 1: Extracting timesheet data from PDF")
        print("-" * 70)

        pdf_path = args.pdf if args.pdf else None
        if pdf_path and not Path(pdf_path).exists():
            print(f"ERROR: PDF file not found: {pdf_path}")
            return 1

        if pdf_path:
            print(f"PDF file: {pdf_path}")
        else:
            print("No PDF specified - using mock data based on spec examples")

        extractor = PDFExtractor(
            pdf_path or "timesheet.pdf",
            target_month=config.target_month
        )

        records = extractor.extract()
        print(f"Extracted {len(records)} timesheet records\n")

        # Initialize report generator
        report = ReportGenerator(config.report_directory)

        # Process records with portal automation
        print("-" * 70)
        print("STEP 2: Processing timesheet entries")
        print("-" * 70)

        with PortalClient(config) as portal:
            # Login
            print("\nLogging into portal...")
            if not portal.login():
                print("ERROR: Login failed!")
                if config.screenshots_on_failure:
                    screenshot = portal.take_screenshot("login_failure.png")
                    print(f"Screenshot saved: {screenshot}")
                return 1

            # Navigate to timesheet
            if not portal.navigate_to_timesheet():
                print("ERROR: Could not navigate to timesheet view!")
                if config.screenshots_on_failure:
                    screenshot = portal.take_screenshot("navigation_failure.png")
                    print(f"Screenshot saved: {screenshot}")
                return 1

            print(f"\nProcessing {len(records)} days...\n")

            # Process each record
            for i, record in enumerate(records, 1):
                print(f"[{i}/{len(records)}] {record.work_date} ({record.day_type})...", end=" ")

                try:
                    action, status = portal.enter_timesheet_data(
                        record,
                        dry_run=config.dry_run
                    )

                    print(f"{action.upper()} - {status}")

                    # Log to audit report
                    screenshot_path = ""
                    if action == "failed" and config.screenshots_on_failure:
                        screenshot_path = portal.take_screenshot(
                            f"failure_{record.work_date}.png"
                        )

                    report.log_action(
                        date=record.work_date,
                        action=action,
                        values=record.to_dict(),
                        status=status,
                        screenshot=screenshot_path,
                        notes=record.notes
                    )

                except Exception as e:
                    print(f"FAILED - {str(e)}")

                    screenshot_path = ""
                    if config.screenshots_on_failure:
                        screenshot_path = portal.take_screenshot(
                            f"error_{record.work_date}.png"
                        )

                    report.log_action(
                        date=record.work_date,
                        action="failed",
                        values=record.to_dict(),
                        status=f"Exception: {str(e)}",
                        screenshot=screenshot_path,
                        notes=record.notes
                    )

        # Generate audit report
        print("\n" + "-" * 70)
        print("STEP 3: Generating audit report")
        print("-" * 70)

        if config.report_format == "csv":
            report_path = report.generate_csv()
        else:
            report_path = report.generate_json()

        print(f"Audit report saved: {report_path}")

        # Print summary
        report.print_summary()

        # Print recommendations
        summary = report.get_summary()
        if summary["failed"] > 0:
            print("Some entries failed. Please review the audit report and screenshots.")

        if summary["skipped"] > 0:
            print("Some entries were skipped. Review the audit report for details.")

        if config.dry_run:
            print("\nDRY RUN COMPLETE - No actual changes were made.")
            print("Review the report and run without --dry-run to apply changes.")
        else:
            print("\nAUTOMATION COMPLETE")

        print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        print("\n\nAutomation interrupted by user")
        return 130

    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
