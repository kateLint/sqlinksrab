"""
Audit report generation module.
Generates CSV/JSON reports with action logs and screenshots.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class AuditRecord:
    """Represents a single audit record for a timesheet entry attempt."""
    
    def __init__(
        self,
        date: str,
        action: str,
        values_attempted: Optional[Dict[str, Any]] = None,
        portal_status: str = "",
        screenshot_path: str = "",
        notes: str = ""
    ):
        """
        Initialize audit record.
        
        Args:
            date: Date in YYYY-MM-DD format
            action: Action taken (created/updated/skipped/failed)
            values_attempted: Dictionary of attempted values
            portal_status: Confirmation or error message from portal
            screenshot_path: Path to screenshot (for failures)
            notes: Additional notes
        """
        self.timestamp = datetime.now().isoformat()
        self.date = date
        self.action = action
        self.values_attempted = values_attempted or {}
        self.portal_status = portal_status
        self.screenshot_path = screenshot_path
        self.notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "timestamp": self.timestamp,
            "date": self.date,
            "action": self.action,
            "start_time": self.values_attempted.get("start_time"),
            "end_time": self.values_attempted.get("end_time"),
            "total_hours": self.values_attempted.get("total_hours_decimal"),
            "portal_status": self.portal_status,
            "screenshot_path": self.screenshot_path,
            "notes": self.notes
        }


class ReportGenerator:
    """Generates audit reports for timesheet automation."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory for report output
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.records: List[AuditRecord] = []
    
    def add_record(self, record: AuditRecord):
        """
        Add audit record to the report.
        
        Args:
            record: AuditRecord to add
        """
        self.records.append(record)
    
    def log_action(
        self,
        date: str,
        action: str,
        values: Optional[Dict[str, Any]] = None,
        status: str = "",
        screenshot: str = "",
        notes: str = ""
    ):
        """
        Log an action for the audit report.
        
        Args:
            date: Date in YYYY-MM-DD format
            action: Action type (created/updated/skipped/failed)
            values: Values attempted
            status: Portal response status
            screenshot: Screenshot path
            notes: Additional notes
        """
        record = AuditRecord(
            date=date,
            action=action,
            values_attempted=values,
            portal_status=status,
            screenshot_path=screenshot,
            notes=notes
        )
        self.add_record(record)
    
    def generate_csv(self, filename: str = None) -> Path:
        """
        Generate CSV report.
        
        Args:
            filename: Custom filename (default: auto-generated with timestamp)
            
        Returns:
            Path to generated CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_report_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if not self.records:
                # Write headers only for empty report
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "date", "action", "start_time", "end_time",
                    "total_hours", "portal_status", "screenshot_path", "notes"
                ])
                writer.writeheader()
            else:
                # Write records
                writer = csv.DictWriter(f, fieldnames=self.records[0].to_dict().keys())
                writer.writeheader()
                for record in self.records:
                    writer.writerow(record.to_dict())
        
        return output_path
    
    def generate_json(self, filename: str = None) -> Path:
        """
        Generate JSON report.
        
        Args:
            filename: Custom filename (default: auto-generated with timestamp)
            
        Returns:
            Path to generated JSON file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_report_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "records": [record.to_dict() for record in self.records]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Returns:
            Dictionary with summary stats
        """
        total = len(self.records)
        created = sum(1 for r in self.records if r.action == "created")
        updated = sum(1 for r in self.records if r.action == "updated")
        skipped = sum(1 for r in self.records if r.action == "skipped")
        failed = sum(1 for r in self.records if r.action == "failed")
        
        return {
            "total_records": total,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "success_rate": f"{((created + updated) / total * 100):.1f}%" if total > 0 else "N/A"
        }
    
    def print_summary(self):
        """Print summary statistics to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("AUDIT REPORT SUMMARY")
        print("=" * 60)
        print(f"Total Records:    {summary['total_records']}")
        print(f"Created:          {summary['created']}")
        print(f"Updated:          {summary['updated']}")
        print(f"Skipped:          {summary['skipped']}")
        print(f"Failed:           {summary['failed']}")
        print(f"Success Rate:     {summary['success_rate']}")
        print("=" * 60 + "\n")
