import json
import os
from pathlib import Path


def data_path():
    root = os.environ.get("APPDATA")
    return (Path(root) if root else Path.home() / ".assistente_personale") / "AssistentePersonale" / "dati.json"


def load():
    path = data_path()
    if not path.exists():
        return {"istruzioni": "", "attivita": []}
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not isinstance(data.get("istruzioni", ""), str) or not isinstance(data.get("attivita", []), list):
        raise ValueError("Il file dei dati locali non ha un formato valido.")
    from .calendar import validate
    for task in data.get("attivita", []):
        if not isinstance(task, dict) or any(not isinstance(task.get(key, ""), str) for key in ("titolo", "data", "ora", "priorita", "note")):
            raise ValueError("Il file dei dati locali contiene un'attività non valida.")
        validate(task)
    return {"istruzioni": data.get("istruzioni", ""), "attivita": data.get("attivita", [])}


def save(data):
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def clear():
    path = data_path()
    if path.exists():
        path.unlink()
