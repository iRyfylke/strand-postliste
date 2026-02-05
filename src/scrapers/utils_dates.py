from datetime import datetime


def parse_date_from_page(s):
    """
    Parser datoer hentet fra nettsiden.
    Støtter flere formater og faller tilbake til ISO-format.
    """
    if not s:
        return None

    formats = ("%Y-%m-%d", "%d.%m.%Y")

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        return None


def parse_cli_date(s):
    """
    Parser datoer fra workflow-input (forventer DD.MM.YYYY).
    """
    if not s:
        return None

    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except Exception:
        raise ValueError(f"Ugyldig datoformat: {s}. Bruk DD.MM.YYYY")


def format_date(d):
    """Formatterer dato som DD.MM.YYYY."""
    return d.strftime("%d.%m.%Y") if d else ""


def within_range(d, start_date, end_date):
    """
    Sjekker om dato d ligger innenfor [start_date, end_date].
    """
    if not d:
        return False
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True
