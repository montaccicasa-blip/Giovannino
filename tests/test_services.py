import json
import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from assistente import ai, calendar, storage


class ServiceTests(unittest.TestCase):
    def test_demo_extraction_and_invalid_date(self):
        tasks = ai.parse_tasks(ai.demo("azioni", "Riunione 2026-12-01 10:30\nScadenza 2026-02-31", "", []))
        self.assertEqual((tasks[0]["data"], tasks[0]["ora"]), ("2026-12-01", "10:30"))
        self.assertEqual(tasks[1]["data"], "")

    def test_schedule_period_and_undated(self):
        today = date.today().isoformat()
        tasks = [{"titolo": "Oggi", "data": today}, {"titolo": "Senza data", "data": ""}, {"titolo": "Passato", "data": "2000-01-01"}]
        result = ai.demo("tempo", "", "", tasks, "giornaliero")
        self.assertIn("Oggi", result)
        self.assertIn("Senza data", result)
        self.assertNotIn("Passato", result)

    def test_parse_rejects_bad_data(self):
        for value in ('{}', '[{"titolo":"x","data":"2026-02-31"}]', '[{"titolo":"x","ora":"10:00"}]', '[{"titolo":3}]'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ai.parse_tasks(value)

    def test_extract_strips_dates(self):
        task = ai.parse_tasks('[{"titolo":" Riunione ", "data":" 2026-12-01 ", "ora":" 10:30 "}]')[0]
        self.assertEqual((task["titolo"], task["data"], task["ora"]), ("Riunione", "2026-12-01", "10:30"))
        self.assertIn("DTSTART:20261201T103000", calendar.make_ics([task]))

    def test_ics_escaping_folding_and_dates(self):
        task = {"titolo": "È" * 50 + ", test", "data": "2026-12-01", "ora": "10:30", "priorita": "Alta", "note": "prima\nseconda; fine"}
        ics = calendar.make_ics([task, {**task, "ora": ""}])
        self.assertIn("DTSTART:20261201T103000\r\nDTEND:20261201T113000", ics)
        self.assertIn("DTSTART;VALUE=DATE:20261201\r\nDTEND;VALUE=DATE:20261202", ics)
        self.assertIn("DESCRIPTION:prima\\nseconda\\; fine", ics)
        self.assertIn("\\, test", ics)
        self.assertTrue(all(len(line.encode("utf-8")) <= 75 for line in ics.split("\r\n")))

    def test_missing_export_date(self):
        with self.assertRaises(ValueError):
            calendar.make_ics([{"titolo": "Senza data"}])

    def test_storage_roundtrip_and_clear(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"APPDATA": directory}):
            data = {"istruzioni": "Cordiale", "attivita": [{"titolo": "Prova", "data": "", "ora": "", "priorita": "Media", "note": ""}]}
            storage.save(data)
            self.assertEqual(storage.load(), data)
            storage.clear()
            self.assertEqual(storage.load(), {"istruzioni": "", "attivita": []})
            storage.data_path().parent.mkdir(parents=True, exist_ok=True)
            storage.data_path().write_text(json.dumps({"attivita": [None]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                storage.load()

    def test_provider_config_and_payload(self):
        with patch.dict(os.environ, {"ASSISTENTE_AI_URL": "http://example.com", "ASSISTENTE_AI_MODEL": "m", "ASSISTENTE_AI_KEY": "k"}, clear=True):
            with self.assertRaises(ValueError):
                ai.config()
        with patch.dict(os.environ, {"ASSISTENTE_AI_URL": "https://example.com/v1/chat/completions", "ASSISTENTE_AI_MODEL": "m", "ASSISTENTE_AI_KEY": "k"}, clear=True):
            endpoint, model, key = ai.config()
            self.assertEqual((endpoint, model, key), ("https://example.com/v1/chat/completions", "m", "k"))
            body = ai.payload("tempo", "messaggio", "cordiale", [{"titolo": "privato"}], model)
            self.assertIn("privato", body["messages"][1]["content"])
            self.assertNotIn(key, json.dumps(body))


if __name__ == "__main__":
    unittest.main()
