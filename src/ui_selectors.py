"""
UI selector definitions for the HRM portal.
Centralized Page Object Model for the modern SPA calendar UI.
"""


HEBREW_MONTHS = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל",
    5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
    9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר"
}


class Selectors:
    """UI selectors for HRM portal automation - Modern SPA calendar UI."""

    # ===== LOGIN PAGE =====
    LOGIN_EMPLOYEE_ID = "input[type='text'], input[type='tel'], input[inputmode='numeric']"
    LOGIN_PASSWORD = "input[type='password']"
    LOGIN_SUBMIT = "button[type='submit'], button:has-text('כניסה'), button:has-text('התחבר'), button:has-text('שלח')"
    LOGIN_ERROR = "[class*='error'], [class*='Error'], .alert-danger"

    # ===== OTP PAGE =====
    OTP_INPUT = "input[type='text'], input[type='tel'], input[type='number'], input[inputmode='numeric']"
    OTP_SUBMIT = "button[type='submit'], button:has-text('אישור'), button:has-text('אימות'), button:has-text('שלח')"

    # ===== CALENDAR NAVIGATION =====
    MONTH_YEAR_HEADER = "[class*='header'] >> text=/\\d{4}/, [class*='title'] >> text=/\\d{4}/"
    MONTH_PREV_ARROW = "button:has(svg):left-of(:text-matches('\\\\d{4}'))"
    MONTH_NEXT_ARROW = "button:has(svg):right-of(:text-matches('\\\\d{4}'))"
    CURRENT_MONTH_BUTTON = "text=חודש נוכחי"

    # ===== CALENDAR GRID =====
    REST_DAY_LABEL = "text=יום מנוחה"

    # ===== LEFT SIDE PANEL =====
    ADD_REPORT_BUTTON = "button:has-text('הוספת דיווח'), button:has-text('דיווח חדש')"
    NEW_REPORT_BUTTON = "button:has-text('דיווח חדש'), button:has-text('+ דיווח חדש')"
    EDIT_BUTTON = "button:has-text('עריכה')"
    DELETE_BUTTON = "button:has-text('מחיקה')"
    NO_REPORTS_MESSAGE = "text=לא קיימים דיווחי נוכחות"

    # ===== ENTRY FORM (inside left panel) =====
    REPORT_CODE_WORK_RADIO = "label:has-text('עבודה'), input[type='radio'] >> .. >> text=עבודה"
    FORM_ENTRY_TIME = "input:near(:text('שעת כניסה'), 100)"
    FORM_EXIT_TIME = "input:near(:text('שעת יציאה'), 100)"
    FORM_TOTAL_DISPLAY = "text=/סה.כ/"
    FORM_NOTES = "textarea"
    MULTI_DAY_CHECKBOX = "input[type='checkbox']:near(:text('דיווח רב-יומי'))"
    FORM_SAVE = "button:has-text('שמירה')"
    FORM_CANCEL = "button:has-text('ביטול')"

    # ===== STATUS/FEEDBACK =====
    SUCCESS_TOAST = "[class*='toast'][class*='success'], [class*='snackbar'], [class*='success']"
    ERROR_TOAST = "[class*='toast'][class*='error'], [class*='snackbar'][class*='error'], [class*='error-message']"
    LOADING_SPINNER = "[class*='spinner'], [class*='loading'], [class*='loader']"

    # ===== NAVIGATION SIDEBAR (right side, blue) =====
    NAV_HOME = "text=עמוד הבית"
    NAV_PERSONAL = "text=אזור אישי"
    NAV_ATTENDANCE = "text=נוכחות"
    NAV_ABSENCE_REQUESTS = "text=בקשות היעדרות"
    NAV_PAY_SLIPS = "text=תלושי שכר"
    NAV_DOCUMENTS = "text=מסמכים ארגוניים"

    @staticmethod
    def day_cell(day_number: int) -> str:
        """Build selector for a specific day cell in the calendar grid."""
        return f":text-is('{day_number:02d}'), :text-is('{day_number}')"
