from datetime import datetime, timedelta, timezone
import uuid


def validate(task):
    title = task.get("titolo", "").strip()
    if not title:
        raise ValueError("Inserisci un titolo.")
    date = task.get("data", "").strip()
    time = task.get("ora", "").strip()
    if time and not date:
        raise ValueError("Inserisci una data se specifichi un'ora.")
    try:
        if date:
            if datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d") != date:
                raise ValueError
        if time:
            if datetime.strptime(time, "%H:%M").strftime("%H:%M") != time:
                raise ValueError
    except ValueError:
        raise ValueError("Usa data AAAA-MM-GG e ora HH:MM valide.") from None
    if task.get("priorita", "Media") not in ("Alta", "Media", "Bassa"):
        raise ValueError("Seleziona una priorità valida.")


def escape(value):
    return str(value).replace("\\", "\\\\").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold(line):
    lines = []
    current = ""
    for char in line:
        if len((current + char).encode("utf-8")) > 75:
            lines.append(current)
            current = " "
        current += char
    lines.append(current)
    return "\r\n".join(lines)


def make_ics(tasks):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Assistente personale//IT", "CALSCALE:GREGORIAN"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for task in tasks:
        validate(task)
        if not task.get("data"):
            raise ValueError("Ogni evento da esportare deve avere una data.")
        day = datetime.strptime(task["data"].strip(), "%Y-%m-%d")
        lines += ["BEGIN:VEVENT", "UID:" + str(uuid.uuid4()) + "@assistente-personale", "DTSTAMP:" + stamp]
        if task.get("ora"):
            start = datetime.strptime(task["data"].strip() + " " + task["ora"].strip(), "%Y-%m-%d %H:%M")
            lines += ["DTSTART:" + start.strftime("%Y%m%dT%H%M%S"), "DTEND:" + (start + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")]
        else:
            lines += ["DTSTART;VALUE=DATE:" + day.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + (day + timedelta(days=1)).strftime("%Y%m%d")]
        lines += ["SUMMARY:" + escape(task["titolo"]), "DESCRIPTION:" + escape(task.get("note", "")), "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"
