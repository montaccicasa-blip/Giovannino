"""Esportazione iCalendar, senza accesso diretto al calendario."""

from datetime import date, datetime, timedelta, timezone
import uuid

from .tasks import validate_task


def escape(value):
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold(line):
    chunks = []
    chunk = ""
    limit = 75
    for char in line:
        if len((chunk + char).encode("utf-8")) > limit:
            chunks.append(chunk)
            chunk = char
            limit = 74
        else:
            chunk += char
    chunks.append(chunk)
    return "\r\n ".join(chunks)


def build_ics(items):
    if not items:
        raise ValueError("Non ci sono attività da esportare.")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Assistente personale//IT", "CALSCALE:GREGORIAN"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for item in items:
        task = validate_task(item)
        if not task["data"]:
            raise ValueError(f'Inserisci una data per «{task["titolo"]}» prima di esportare.')
        day = date.fromisoformat(task["data"])
        lines.extend(["BEGIN:VEVENT", f"UID:{uuid.uuid4()}@assistente-personale", f"DTSTAMP:{stamp}"])
        if task["ora"]:
            start = datetime.strptime(task["data"] + " " + task["ora"], "%Y-%m-%d %H:%M")
            lines.extend([f'DTSTART:{start.strftime("%Y%m%dT%H%M%S")}',
                          f'DTEND:{(start + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")}'])
        else:
            lines.extend([f'DTSTART;VALUE=DATE:{day.strftime("%Y%m%d")}',
                          f'DTEND;VALUE=DATE:{(day + timedelta(days=1)).strftime("%Y%m%d")}'])
        lines.extend([f'SUMMARY:{escape(task["titolo"])}',
                      f'DESCRIPTION:{escape("Priorità: " + task["priorita"] + chr(10) + task["note"])}',
                      "END:VEVENT"])
    lines.append("END:VCALENDAR")
    return ("\r\n".join(fold(line) for line in lines) + "\r\n").encode("utf-8")
