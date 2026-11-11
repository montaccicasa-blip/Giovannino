import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from assistente import ai, calendar_export, data, tasks


def task(**changes):
    return {"titolo": "Appuntamento", "data": "2026-11-12", "ora": "09:30",
            "priorita": "Media", "note": "", **changes}


class TaskTests(unittest.TestCase):
    def test_validation_rejects_bad_dates_and_times(self):
        for changes in ({"data": "2026-02-30"}, {"data": "12/11/2026"},
                        {"ora": "25:00"}, {"data": "", "ora": "09:30"},
                        {"priorita": "Urgente"}, {"titolo": ""}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                tasks.validate_task(task(**changes))

    def test_demo_requires_verification_and_does_not_invent_invalid_dates(self):
        result = tasks.demo_extract("Chiama 2026-11-12 09:30\nInvia 2026-02-30\n")
        self.assertEqual(len(result), 2)
        self.assertEqual((result[0]["data"], result[0]["ora"]), ("2026-11-12", "09:30"))
        self.assertEqual(result[1]["data"], "")
        self.assertIn("non riconosciuta", result[1]["note"])

    def test_agenda_flags_identical_start_times(self):
        result = tasks.agenda([task(), task(titolo="Altra"), task(data="", ora="")])
        self.assertIn("Possibile conflitto", result)
        self.assertIn("Senza data", result)


class StorageTests(unittest.TestCase):
    def test_roundtrip_and_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dati.json"
            self.assertEqual(data.load(path)["attivita"], [])
            data.save(path, {"istruzioni": "Cordiale", "attivita": [task()]})
            self.assertEqual(data.load(path)["attivita"][0]["titolo"], "Appuntamento")
            data.save(path, {"istruzioni": "", "attivita": []})
            self.assertEqual(data.load(path), {"istruzioni": "", "attivita": []})

    def test_bad_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dati.json"
            path.write_text('{"attivita": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
                data.load(path)
            self.assertEqual(path.read_text(encoding="utf-8"), '{"attivita": []}')


class CalendarTests(unittest.TestCase):
    def test_timed_all_day_escaping_and_utf8_folding(self):
        content = calendar_export.build_ics([
            task(titolo="È" * 50 + ", riunione", note="uno;due\r\naltro\rfine"),
            task(titolo="Giorno", data="2026-12-31", ora=""),
        ])
        self.assertTrue(all(len(line) <= 75 for line in content.split(b"\r\n")))
        unfolded = content.decode("utf-8").replace("\r\n ", "")
        self.assertIn("DTSTART:20261112T093000\r\nDTEND:20261112T103000", unfolded)
        self.assertIn("DTSTART;VALUE=DATE:20261231\r\nDTEND;VALUE=DATE:20270101", unfolded)
        self.assertIn("È" * 50 + r"\, riunione", unfolded)
        self.assertIn(r"uno\;due\naltro\nfine", unfolded)

    def test_missing_date_rejected(self):
        with self.assertRaises(ValueError):
            calendar_export.build_ics([task(data="", ora="")])


class ProviderTests(unittest.TestCase):
    def test_configuration_requires_https_and_no_credentials_in_url(self):
        for url in ("http://example.com/api", "https://user:pass@example.com/", "https://example.com/?token=x"):
            with self.subTest(url=url), patch.dict(os.environ, {
                "ASSISTENTE_AI_URL": url, "ASSISTENTE_AI_MODEL": "model",
                "ASSISTENTE_AI_API_KEY": "key",
            }, clear=True), self.assertRaises(ValueError):
                ai.configuration()
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            ai.configuration()

    def test_messages_include_only_relevant_tasks(self):
        items = [task()]
        reply = ai.messages_for("risposta", "Conciso", "Testo", items)
        agenda = ai.messages_for("agenda", "Conciso", "Testo", items)
        self.assertNotIn("Appuntamento", reply[1]["content"])
        self.assertIn("Appuntamento", agenda[1]["content"])
        self.assertIn("Testo", reply[1]["content"])

    def test_request_sends_previewed_messages_and_reports_http_errors(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, size):
                return b'{"choices":[{"message":{"content":"Bozza"}}]}'

        messages = ai.messages_for("risposta", "Cordiale", "Ciao", [])
        with patch("assistente.ai.build_opener") as opener:
            opener.return_value.open.return_value = Response()
            self.assertEqual(ai.request_completion("https://example.com/api", "modello", "chiave", messages), "Bozza")
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(json.loads(request.data), {"model": "modello", "messages": messages})
            self.assertEqual(request.get_header("Authorization"), "Bearer chiave")
            opener.return_value.open.side_effect = HTTPError(request.full_url, 401, "no", {}, None)
            with self.assertRaisesRegex(ValueError, "HTTP 401"):
                ai.request_completion(request.full_url, "modello", "chiave", messages)


if __name__ == "__main__":
    unittest.main()
