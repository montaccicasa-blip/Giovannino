"""Archiviazione locale delle sole preferenze e attività."""

import json
import os
from pathlib import Path
import tempfile


def data_path():
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".assistente-personale")
    return base / "AssistentePersonale" / "dati.json"


def load(path):
    if not path.exists():
        return {"istruzioni": "", "attivita": []}
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if (not isinstance(data, dict) or not isinstance(data.get("istruzioni"), str)
            or not isinstance(data.get("attivita"), list)
            or not all(isinstance(item, dict) for item in data["attivita"])):
        raise ValueError("Il file dei dati locali ha un formato non valido.")
    return data


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as file:
            temporary = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
