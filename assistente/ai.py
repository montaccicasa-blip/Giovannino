import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit


PROMPTS = {
    "risposta": "Prepara soltanto una bozza di risposta al messaggio, seguendo le istruzioni personali. Non inviare nulla.",
    "azioni": ('Estrai attività, scadenze, appuntamenti e promemoria. Rispondi solo con un array JSON di oggetti '
               'con chiavi "titolo", "data" (AAAA-MM-GG o stringa vuota), "ora" (HH:MM o stringa vuota), '
               '"priorita" (Alta, Media o Bassa) e "note". Non inventare date.'),
    "tempo": "Proponi un programma realistico usando soltanto gli impegni forniti. Segnala informazioni mancanti e conflitti; non modificare il calendario.",
}


def config():
    endpoint = os.environ.get("ASSISTENTE_AI_URL", "").strip()
    model = os.environ.get("ASSISTENTE_AI_MODEL", "").strip()
    key = os.environ.get("ASSISTENTE_AI_KEY", "").strip()
    parts = urlsplit(endpoint)
    if not endpoint or not model or not key:
        raise ValueError("Configura ASSISTENTE_AI_URL, ASSISTENTE_AI_MODEL e ASSISTENTE_AI_KEY prima di usare l'AI online.")
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError("L'indirizzo del provider deve essere un URL HTTPS senza credenziali o frammenti.")
    return endpoint, model, key


def payload(action, text, instructions, tasks, model):
    user = "Istruzioni personali:\n" + instructions + "\n\n"
    if action == "tempo":
        user += "Impegni inseriti:\n" + json.dumps(tasks, ensure_ascii=False, indent=2) + "\n\n"
    user += "Testo fornito:\n" + text
    return {"model": model, "messages": [
        {"role": "system", "content": PROMPTS[action] + " Rispondi in italiano. Data corrente: " + date.today().isoformat() + "."},
        {"role": "user", "content": user},
    ]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(endpoint, key, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError
        return content
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError):
        raise ValueError("Richiesta AI non riuscita. Verifica indirizzo, modello, credenziali e connessione; riprova.") from None


def demo(action, text, instructions, tasks, period="settimanale"):
    if action == "risposta":
        return "Bozza dimostrativa da modificare:\n\nGrazie per il messaggio. Ti risponderò appena possibile."
    if action == "azioni":
        result = []
        for line in text.splitlines():
            line = line.strip(" \t-*")
            if not line:
                continue
            match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", line)
            hour = re.search(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b", line)
            day = match.group() if match else ""
            try:
                if day:
                    datetime.strptime(day, "%Y-%m-%d")
            except ValueError:
                day = ""
            result.append({"titolo": line[:100], "data": day, "ora": hour.group() if hour and day else "", "priorita": "Media", "note": line})
        return json.dumps(result, ensure_ascii=False, indent=2)
    today = date.today()
    end = today + timedelta(days=0 if period == "giornaliero" else 6)
    ordered = sorted((item for item in tasks if not item.get("data") or today.isoformat() <= item["data"] <= end.isoformat()),
                     key=lambda item: (item.get("data") or "9999", item.get("ora") or "99:99", {"Alta": 0, "Media": 1, "Bassa": 2}.get(item.get("priorita"), 1)))
    if not ordered:
        return "Nessun impegno nel periodo scelto. Aggiungi attività con date e orari per organizzare il tempo."
    return f"Programma {period} indicativo ({today.isoformat()} – {end.isoformat()}); verifica durate e conflitti:\n" + "\n".join(
        f"- {item.get('data') or 'Data da definire'} {item.get('ora') or ''}: {item.get('titolo', '')} (priorità {item.get('priorita', 'Media')})" for item in ordered)


def parse_tasks(text):
    from .calendar import validate

    try:
        items = json.loads(text)
        if not isinstance(items, list):
            raise ValueError
        result = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError
            task = {key: item.get(key, default) for key, default in (
                ("titolo", ""), ("data", ""), ("ora", ""), ("priorita", "Media"), ("note", ""))}
            if not all(isinstance(value, str) for value in task.values()):
                raise ValueError
            validate(task)
            result.append(task)
        return result
    except (ValueError, TypeError):
        raise ValueError("Non è stato possibile leggere le attività. Controlla il risultato e aggiungile manualmente.") from None
