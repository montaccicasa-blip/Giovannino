import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from assistente.ui import Application


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "Interfaccia grafica non disponibile")
class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.directory.name})
        self.environment.start()
        self.app = Application()
        self.app.withdraw()
        self.app.source.insert("1.0", "Scrivi a Marco 2026-11-12 09:30")

    def tearDown(self):
        self.app.destroy()
        self.environment.stop()
        self.directory.cleanup()

    def test_demo_extract_and_persist_without_network(self):
        with patch("assistente.ui.messagebox.askyesno", return_value=True), \
             patch("assistente.ai.request_completion") as network:
            self.app.run("azioni")
            network.assert_not_called()
        self.assertEqual(len(self.app.state["attivita"]), 1)
        self.assertEqual(self.app.state["attivita"][0]["data"], "2026-11-12")
        self.assertTrue((Path(self.directory.name) / "AssistentePersonale" / "dati.json").exists())

    def test_online_request_requires_confirmation(self):
        config = ("https://example.com/api", "model", "secret")
        self.app.mode.set("Provider AI online")
        with patch("assistente.ai.configuration", return_value=config), \
             patch.object(self.app, "confirm_details", return_value=False) as confirm, \
             patch("assistente.ai.request_completion") as network:
            self.app.run("risposta")
            network.assert_not_called()
            self.assertIn("Scrivi a Marco", confirm.call_args.args[2])
            self.assertNotIn("secret", confirm.call_args.args[2])

    def test_export_requires_confirmation_and_never_overwrites(self):
        target = Path(self.directory.name) / "evento.ics"
        target.write_text("originale", encoding="utf-8")
        self.app.state["attivita"] = [{
            "titolo": "Riunione", "data": "2026-11-12", "ora": "09:30",
            "priorita": "Media", "note": "",
        }]
        with patch("assistente.ui.filedialog.asksaveasfilename", return_value=str(target)), \
             patch.object(self.app, "confirm_details", return_value=False), \
             patch("assistente.ui.messagebox.showerror") as error:
            self.app.export()
            error.assert_not_called()
        self.assertEqual(target.read_text(encoding="utf-8"), "originale")
        with patch("assistente.ui.filedialog.asksaveasfilename", return_value=str(target)), \
             patch.object(self.app, "confirm_details", return_value=True), \
             patch("assistente.ui.messagebox.showerror") as error:
            self.app.export()
            error.assert_called_once()
        self.assertEqual(target.read_text(encoding="utf-8"), "originale")

    def test_confirmed_online_reply_is_displayed(self):
        self.app.mode.set("Provider AI online")
        with patch("assistente.ai.configuration", return_value=("https://example.com", "model", "secret")), \
             patch.object(self.app, "confirm_details", return_value=True), \
             patch("assistente.ai.request_completion", return_value="Risposta pronta") as network:
            self.app.run("risposta")
            deadline = time.monotonic() + 2
            while self.app.results.empty() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.app.check_results()
            network.assert_called_once()
        self.assertEqual(self.app.output.get("1.0", "end-1c"), "Risposta pronta")


if __name__ == "__main__":
    unittest.main()
