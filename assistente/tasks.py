"""Validazione, suggerimenti locali e riepilogo dell'agenda."""

from datetime import date, datetime
import re

PRIORITIES = ("Alta", "Media", "Bassa")


def validate_task(item):
    if not isinstance(item, dict):
        raise ValueError("L'attività deve essere un oggetto.")
    result = {}
    for key in ("titolo", "data", "ora", "priorita", "note"):
        value = item.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"Il campo {key} deve essere testo.")
        result[key] = value.strip()
    if not result["titolo"]:
        raise ValueError("Inserisci un titolo.")
    if result["data"]:
        try:
            if date.fromisoformat(result["data"]).isoformat() != result["data"]:
                raise ValueError
        except ValueError:
            raise ValueError("La data deve essere valida e nel formato AAAA-MM-GG.") from None
    if result["ora"]:
        if not result["data"]:
            raise ValueError("Per specificare un'ora serve anche una data.")
        try:
            if not re.fullmatch(r"\d{2}:\d{2}", result["ora"]):
                raise ValueError
            datetime.strptime(result["ora"], "%H:%M")
        except ValueError:
            raise ValueError("L'ora deve essere valida e nel formato HH:MM.") from None
    if result["priorita"] not in PRIORITIES:
        raise ValueError("Seleziona una priorità valida.")
    return result


def demo_extract(text):
    """Crea proposte da righe esplicite; non interpreta date relative."""
    proposals = []
    for line in text.splitlines():
        line = line.strip(" \t-*")
        if not line:
            continue
        date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", line)
        time_match = re.search(r"\b\d{2}:\d{2}\b", line)
        candidate = {
            "titolo": line,
            "data": date_match.group() if date_match else "",
            "ora": time_match.group() if time_match and date_match else "",
            "priorita": "Media",
            "note": "Proposta dimostrativa: verificare titolo e scadenza.",
        }
        try:
            proposals.append(validate_task(candidate))
        except ValueError:
            candidate["data"] = ""
            candidate["ora"] = ""
            candidate["note"] += " Data o ora non riconosciuta."
            proposals.append(validate_task(candidate))
    return proposals


def agenda(items):
    if not items:
        return "Non ci sono attività. Aggiungine almeno una per organizzare il tempo."
    ordered = sorted(items, key=lambda x: (
        x["data"] or "9999", x["ora"] or "99:99",
        PRIORITIES.index(x["priorita"]), x["titolo"].casefold()
    ))
    lines = ["Programma indicativo: affronta prima le attività elencate in ciascuna giornata.",
             "Le attività senza ora o data richiedono una collocazione manuale; verifica durate e disponibilità."]
    slots = {}
    for task in ordered:
        when = task["data"] or "Senza data"
        when += f' {task["ora"]}' if task["ora"] else " (ora da definire)"
        lines.append(f'{when} — {task["titolo"]} [{task["priorita"]}]')
        if task["data"] and task["ora"]:
            slot = (task["data"], task["ora"])
            slots[slot] = slots.get(slot, 0) + 1
    for (day, time), count in slots.items():
        if count > 1:
            lines.append(f"Possibile conflitto: {count} attività iniziano il {day} alle {time}.")
    return "\n".join(lines)
