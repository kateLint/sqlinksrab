"""
Configuration management module.
Loads settings from config.json and environment variables.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    """Configuration manager for HRM portal automation."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.json file
        """
        # Load environment variables
        load_dotenv()
        
        # Load config file
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            # Use default config if file doesn't exist
            config_example = Path(__file__).parent.parent / "config.example.json"
            if config_example.exists():
                with open(config_example, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                raise FileNotFoundError(f"Config file not found: {config_path}")
        
        # Load credentials from environment (optional - can be set later)
        self.employee_id = os.getenv("HRM_EMPLOYEE_ID")
        self.password = os.getenv("HRM_PASSWORD")
    
    @property
    def base_url(self) -> str:
        """Get portal base URL."""
        return self._config["portal"]["base_url"]
    
    @property
    def target_month(self) -> str:
        """Get target month (YYYY-MM format)."""
        return self._config["automation"]["target_month"]
    
    @property
    def dry_run(self) -> bool:
        """Check if running in dry-run mode."""
        return self._config["automation"].get("dry_run", False)
    
    @property
    def headless(self) -> bool:
        """Check if running in headless mode."""
        return self._config["automation"].get("headless", True)
    
    @property
    def timeout_seconds(self) -> int:
        """Get timeout for portal operations."""
        return self._config["automation"].get("timeout_seconds", 30)
    
    @property
    def retry_attempts(self) -> int:
        """Get number of retry attempts for failed operations."""
        return self._config["automation"].get("retry_attempts", 3)

    @property
    def otp_timeout(self) -> int:
        """Get timeout in seconds for OTP manual entry."""
        return self._config["automation"].get("otp_timeout_seconds", 120)

    @property
    def inter_entry_delay(self) -> float:
        """Get delay in seconds between processing each day."""
        return self._config["automation"].get("inter_entry_delay", 1.5)

    @property
    def entry_rules(self) -> Dict[str, Any]:
        """Get entry rules configuration."""
        return self._config.get("entry_rules", {})
    
    @property
    def skip_weekends(self) -> bool:
        """Check if weekends should be skipped."""
        return self.entry_rules.get("skip_weekends", True)
    
    @property
    def skip_missing_flags(self) -> bool:
        """Check if days with missing entry/exit flags should be skipped."""
        return self.entry_rules.get("skip_missing_entry_exit_flags", True)
    
    @property
    def handle_total_hours_only(self) -> str:
        """Get strategy for handling days with only total hours."""
        return self.entry_rules.get("handle_total_hours_only", "skip_and_flag")
    
    @property
    def decimal_hours_format(self) -> str:
        """Get decimal hours format interpretation (standard or special)."""
        return self.entry_rules.get("decimal_hours_format", "standard")
    
    @property
    def report_directory(self) -> Path:
        """Get output directory for reports."""
        dir_path = Path(self._config["output"].get("report_directory", "./output"))
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    @property
    def report_format(self) -> str:
        """Get report format (csv or json)."""
        return self._config["output"].get("report_format", "csv")
    
    @property
    def screenshots_on_failure(self) -> bool:
        """Check if screenshots should be captured on failures."""
        return self._config["output"].get("screenshots_on_failure", True)
    
    def redact_sensitive(self, text: str) -> str:
        """
        Redact sensitive information from text for logging.
        
        Args:
            text: Text potentially containing sensitive data
            
        Returns:
            Text with sensitive data redacted
        """
        if self.employee_id and self.employee_id in text:
            text = text.replace(self.employee_id, "***EMPLOYEE_ID***")
        if self.password and self.password in text:
            text = text.replace(self.password, "***PASSWORD***")
        return text
