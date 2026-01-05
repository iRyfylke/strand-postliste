from datetime import datetime

def detect_changes(existing, new_doc):
    """Returnerer (is_new, changes_dict)."""
    doc_id = new_doc["dokumentID"]
    old = existing.get(doc_id)

    if not old:
        return True, {
            "status": {"gammel": None, "ny": new_doc.get("status")},
            "tittel": {"gammel": None, "ny": new_doc.get("tittel")},
            "dokumenttype": {"gammel": None, "ny": new_doc.get("dokumenttype")},
            "avsender_mottaker": {"gammel": None, "ny": new_doc.get("avsender_mottaker")},
            "detalj_link": {"gammel": None, "ny": new_doc.get("detalj_link")},
            "dato": {"gammel": None, "ny": new_doc.get("dato")},
            "dato_iso": {"gammel": None, "ny": new_doc.get("dato_iso")},
            "filer_count": {"gammel": 0, "ny": len(new_doc.get("filer", []))}
        }

    changes = {}
    for key in ["status", "tittel", "dokumenttype", "avsender_mottaker", "detalj_link", "dato", "dato_iso"]:
        if old.get(key) != new_doc.get(key):
            changes[key] = {"gammel": old.get(key), "ny": new_doc.get(key)}

    if len(old.get("filer", [])) != len(new_doc.get("filer", [])):
        changes["filer_count"] = {
            "gammel": len(old.get("filer", [])),
            "ny": len(new_doc.get("filer", []))
        }

    return False, changes

def build_change_entry(doc_id, title, change_dict, change_type):
    return {
        "tidspunkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": change_type,
        "dokumentID": doc_id,
        "tittel": title,
        "endringer": change_dict
    }
