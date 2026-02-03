from datetime import datetime

def parse_date_from_page(s):
    """Datoer hentet fra nettsiden (kan være flere formater)."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    try:
        return datetime.fromisoformat(s[:10]).date()
    except:
        return None


def parse_cli_date(s):
    """Datoer fra workflow-input (forventer DD.MM.YYYY)."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except:
        raise ValueError(f"Ugyldig datoformat: {s}. Bruk DD.MM.YYYY")


def format_date(d):
    return d.strftime("%d.%m.%Y") if d else ""


def within_range(d, start_date, end_date):
    if not d:
        return False
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True
