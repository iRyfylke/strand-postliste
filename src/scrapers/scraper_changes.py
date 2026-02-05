from datetime import datetime


# ---------------------------------------------------------
# DETECT CHANGES
# ---------------------------------------------------------
def detect_changes(existing, new_doc):
    """
    Sammenligner et nytt dokument med eksisterende data.
    Returnerer:
        (is_new, changes_dict)
    """
    doc_id = new_doc["dokumentID"]
    old = existing.get(doc_id)

    # -----------------------------------------------------
    # NYTT DOKUMENT
    # -----------------------------------------------------
    if not old:
        return True, _build_new_doc_changes(new_doc)

    # -----------------------------------------------------
    # EKSISTERENDE DOKUMENT → SJEKK ENDRINGER
    # -----------------------------------------------------
    changes = {}

    fields_to_check = [
        "status",
        "tittel",
        "dokumenttype",
        "avsender_mottaker",
        "detalj_link",
        "dato",
        "dato_iso",
    ]

    for key in fields_to_check:
        old_val = old.get(key)
        new_val = new_doc.get(key)
        if old_val != new_val:
            changes[key] = {"gammel": old_val, "ny": new_val}

    # Endring i antall filer
    old_files = len(old.get("filer", []))
    new_files = len(new_doc.get("filer", []))
    if old_files != new_files:
        changes["filer_count"] = {"gammel": old_files, "ny": new_files}

    return False, changes


# ---------------------------------------------------------
# HJELPER: NYTT DOKUMENT
# ---------------------------------------------------------
def _build_new_doc_changes(new_doc):
    """Bygger changes-dict for helt nye dokumenter."""
    return {
        "status": {"gammel": None, "ny": new_doc.get("status")},
        "tittel": {"gammel": None, "ny": new_doc.get("tittel")},
        "dokumenttype": {"gammel": None, "ny": new_doc.get("dokumenttype")},
        "avsender_mottaker": {"gammel": None, "ny": new_doc.get("avsender_mottaker")},
        "detalj_link": {"gammel": None, "ny": new_doc.get("detalj_link")},
        "dato": {"gammel": None, "ny": new_doc.get("dato")},
        "dato_iso": {"gammel": None, "ny": new_doc.get("dato_iso")},
        "filer_count": {"gammel": 0, "ny": len(new_doc.get("filer", []))},
    }


# ---------------------------------------------------------
# BUILD CHANGE ENTRY
# ---------------------------------------------------------
def build_change_entry(doc_id, title, change_dict, change_type):
    """
    Lager en endringslogg-entry for lagring i data/changes/.
    """
    return {
        "tidspunkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": change_type,
        "dokumentID": doc_id,
        "tittel": title,
        "endringer": change_dict,
    }
