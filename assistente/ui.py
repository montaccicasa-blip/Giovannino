"""Interfaccia desktop; nessuna integrazione controlla altre applicazioni."""

from datetime import date, timedelta
import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from . import ai, calendar_export, data, tasks


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assistente personale")
        self.geometry("1060x800")
        self.minsize(720, 600)
        self.path = data.data_path()
        try:
            self.state = data.load(self.path)
            self.state["attivita"] = [tasks.validate_task(x) for x in self.state["attivita"]]
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Dati locali non disponibili", f"Impossibile aprire i dati locali: {exc}\nIl file non è stato modificato.", parent=self)
            self.destroy()
            return
        self.results = queue.Queue()
        self.busy = False
        self.build()
        self.refresh()
        self.after(100, self.check_results)

    def build(self):
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)
        header = ttk.Frame(container)
        header.pack(fill="x")
        ttk.Label(header, text="Assistente personale", font=("TkDefaultFont", 16, "bold")).pack(side="left")
        self.mode = tk.StringVar(value="Dimostrativa (offline)")
        ttk.Label(header, text="Modalità:").pack(side="left", padx=(20, 4))
        ttk.Combobox(header, textvariable=self.mode, state="readonly", width=23,
                     values=("Dimostrativa (offline)", "Provider AI online")).pack(side="left")
        ttk.Label(container, text="Incolla solo i messaggi che vuoi analizzare. Nessuna lettura o invio automatico.", wraplength=950).pack(anchor="w", pady=5)

        panes = ttk.Panedwindow(container, orient="vertical")
        panes.pack(fill="both", expand=True)
        top = ttk.Frame(panes)
        bottom = ttk.Frame(panes)
        panes.add(top, weight=2)
        panes.add(bottom, weight=3)

        ttk.Label(top, text="Messaggio da Thunderbird, WhatsApp o altra fonte:").pack(anchor="w")
        self.source = ScrolledText(top, height=5, wrap="word")
        self.source.pack(fill="both", expand=True)
        ttk.Label(top, text="Tono, stile e istruzioni personali:").pack(anchor="w", pady=(5, 0))
        instruction_row = ttk.Frame(top)
        instruction_row.pack(fill="x")
        self.instructions = ttk.Entry(instruction_row)
        self.instructions.pack(side="left", fill="x", expand=True)
        self.instructions.insert(0, self.state["istruzioni"])
        ttk.Button(instruction_row, text="Salva preferenze", command=self.save_preferences).pack(side="left", padx=5)

        actions = ttk.Frame(top)
        actions.pack(fill="x", pady=5)
        ttk.Button(actions, text="Prepara una risposta", command=lambda: self.run("risposta")).pack(side="left")
        ttk.Button(actions, text="Estrai azioni", command=lambda: self.run("azioni")).pack(side="left", padx=5)
        ttk.Button(actions, text="Organizza il mio tempo", command=lambda: self.run("agenda")).pack(side="left")
        self.period = tk.StringVar(value="Settimana")
        ttk.Combobox(actions, textvariable=self.period, state="readonly", width=10,
                     values=("Giorno", "Settimana")).pack(side="left", padx=5)

        ttk.Label(bottom, text="Risultato / bozza (verifica sempre prima di usarlo):").pack(anchor="w")
        self.output = ScrolledText(bottom, height=6, wrap="word")
        self.output.pack(fill="both", expand=True)
        ttk.Button(bottom, text="Copia risultato", command=self.copy_output).pack(anchor="w", pady=3)
        ttk.Label(bottom, text="Attività locali (seleziona una riga per modificarla):").pack(anchor="w")
        columns = ("titolo", "data", "ora", "priorita", "note")
        self.tree = ttk.Treeview(bottom, columns=columns, show="headings", selectmode="browse", height=5)
        for key, label, width in zip(columns, ("Titolo", "Data", "Ora", "Priorità", "Note"), (220, 100, 65, 75, 300)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=50)
        self.tree.pack(fill="both", expand=True)
        controls = ttk.Frame(bottom)
        controls.pack(fill="x", pady=5)
        for text, command in (
            ("Aggiungi", self.add_task), ("Modifica", self.edit_task),
            ("Rimuovi attività", self.remove_task), ("Esporta .ics", self.export),
            ("Cancella dati locali", self.clear_data),
        ):
            ttk.Button(controls, text=text, command=command).pack(side="left", padx=(0, 5))
        self.status = tk.StringVar(value="Modalità dimostrativa: nessun dato viene inviato online.")
        ttk.Label(container, textvariable=self.status, wraplength=950).pack(anchor="w")

    def persist(self, new_state):
        try:
            data.save(self.path, new_state)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Salvataggio non riuscito", f"Impossibile salvare i dati locali: {exc}", parent=self)
            return False
        self.state = new_state
        return True

    def save_preferences(self):
        if self.persist({**self.state, "istruzioni": self.instructions.get()}):
            self.status.set("Preferenze salvate sul dispositivo.")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(self.state["attivita"]):
            self.tree.insert("", "end", iid=str(index), values=tuple(item[k] for k in ("titolo", "data", "ora", "priorita", "note")))

    def selected_index(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Selezione richiesta", "Seleziona un'attività nella lista.", parent=self)
            return None
        return int(selection[0])

    def task_dialog(self, initial=None):
        dialog = tk.Toplevel(self)
        dialog.title("Attività")
        dialog.transient(self)
        dialog.grab_set()
        values = initial or {"titolo": "", "data": "", "ora": "", "priorita": "Media", "note": ""}
        entries = {}
        for row, (key, label) in enumerate((
            ("titolo", "Titolo"), ("data", "Data (AAAA-MM-GG)"), ("ora", "Ora (HH:MM)"),
            ("priorita", "Priorità"), ("note", "Note"),
        )):
            ttk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=5)
            variable = tk.StringVar(value=values[key])
            widget = (ttk.Combobox(dialog, textvariable=variable, values=tasks.PRIORITIES, state="readonly")
                      if key == "priorita" else ttk.Entry(dialog, textvariable=variable, width=55))
            widget.grid(row=row, column=1, sticky="ew", padx=8, pady=5)
            entries[key] = variable
        result = []

        def accept():
            try:
                result.append(tasks.validate_task({key: value.get() for key, value in entries.items()}))
            except ValueError as exc:
                messagebox.showerror("Attività non valida", str(exc), parent=dialog)
                return
            dialog.destroy()

        ttk.Button(dialog, text="Salva", command=accept).grid(row=5, column=1, sticky="e", padx=8, pady=8)
        dialog.columnconfigure(1, weight=1)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.wait_window(dialog)
        return result[0] if result else None

    def add_task(self):
        item = self.task_dialog()
        if item and self.persist({**self.state, "attivita": self.state["attivita"] + [item]}):
            self.refresh()

    def edit_task(self):
        index = self.selected_index()
        if index is None:
            return
        item = self.task_dialog(self.state["attivita"][index])
        if item:
            updated = self.state["attivita"].copy()
            updated[index] = item
            if self.persist({**self.state, "attivita": updated}):
                self.refresh()

    def remove_task(self):
        index = self.selected_index()
        if index is not None and messagebox.askyesno("Rimuovi attività", "Rimuovere questa attività dall'elenco locale?", parent=self):
            updated = self.state["attivita"].copy()
            updated.pop(index)
            if self.persist({**self.state, "attivita": updated}):
                self.refresh()

    def clear_data(self):
        if messagebox.askyesno("Cancella dati locali", "Cancellare tutte le preferenze e le attività locali? L'operazione non è reversibile.", parent=self):
            if self.persist({"istruzioni": "", "attivita": []}):
                self.instructions.delete(0, "end")
                self.refresh()
                self.status.set("Preferenze e attività locali cancellate.")

    def copy_output(self):
        text = self.output.get("1.0", "end-1c")
        if not text:
            messagebox.showinfo("Nessun risultato", "Non c'è testo da copiare.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("Risultato copiato negli appunti. Incollalo manualmente nell'app desiderata.")

    def set_output(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)

    def run(self, action):
        if self.busy:
            messagebox.showinfo("Operazione in corso", "Attendi la risposta del provider.", parent=self)
            return
        text = self.source.get("1.0", "end-1c").strip()
        if action in ("risposta", "azioni") and not text:
            messagebox.showinfo("Messaggio richiesto", "Incolla prima il testo del messaggio.", parent=self)
            return
        today = date.today()
        end = today + timedelta(days=0 if self.period.get() == "Giorno" else 6)
        items = [item for item in self.state["attivita"] if not item["data"] or today.isoformat() <= item["data"] <= end.isoformat()]
        if self.mode.get() == "Dimostrativa (offline)":
            if action == "risposta":
                self.set_output("Bozza dimostrativa da personalizzare:\n\nGrazie per il messaggio. Ti risponderò appena possibile.\n\n[Completa la risposta dopo aver verificato il contenuto.]")
            elif action == "azioni":
                self.offer_proposals(tasks.demo_extract(text))
            else:
                self.set_output(f"Periodo: {today.isoformat()} – {end.isoformat()}\n" + tasks.agenda(items))
            return
        try:
            url, model, key = ai.configuration()
        except ValueError as exc:
            messagebox.showerror("Configurazione AI", str(exc), parent=self)
            return
        instruction = self.instructions.get()
        if action == "agenda":
            instruction += f"\nPeriodo richiesto: {today.isoformat()} – {end.isoformat()}."
        messages = ai.messages_for(action, instruction, text, items)
        preview = json.dumps({"model": model, "messages": messages}, ensure_ascii=False, indent=2)
        if not self.confirm_details(
            "Conferma invio al provider AI",
            f"Destinatario: {url}\nSaranno inviati esattamente i dati mostrati sotto. La chiave API è trasmessa nell'intestazione di autenticazione.",
            preview, "Invia questi dati"
        ):
            self.status.set("Invio annullato. Nessun dato trasmesso.")
            return
        self.busy = True
        self.status.set("Richiesta al provider in corso...")

        def worker():
            try:
                self.results.put((action, ai.request_completion(url, model, key, messages), None))
            except Exception as exc:
                self.results.put((action, None, f"{type(exc).__name__}: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def confirm_details(self, title, explanation, details, confirm_label):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("800x600")
        ttk.Label(dialog, text=explanation, wraplength=760).pack(anchor="w", padx=10, pady=10)
        preview = ScrolledText(dialog, wrap="word")
        preview.insert("1.0", details)
        preview.configure(state="disabled")
        preview.pack(fill="both", expand=True, padx=10)
        result = [False]

        def send():
            result[0] = True
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.pack(pady=10)
        ttk.Button(buttons, text=confirm_label, command=send).pack(side="left", padx=5)
        ttk.Button(buttons, text="Annulla", command=dialog.destroy).pack(side="left", padx=5)
        self.wait_window(dialog)
        return result[0]

    def check_results(self):
        try:
            action, result, error = self.results.get_nowait()
        except queue.Empty:
            self.after(100, self.check_results)
            return
        self.busy = False
        if error:
            messagebox.showerror("Errore AI", error, parent=self)
            self.status.set("Richiesta non riuscita.")
        elif action == "azioni":
            try:
                parsed = json.loads(result)
                if not isinstance(parsed, list):
                    raise ValueError("Il provider non ha restituito una lista di attività.")
                proposals = [tasks.validate_task(item) for item in parsed]
            except (ValueError, json.JSONDecodeError) as exc:
                self.set_output(result)
                messagebox.showerror("Risposta non valida", f"Le proposte non sono state aggiunte: {exc}\nIl testo ricevuto è disponibile nel risultato.", parent=self)
            else:
                self.offer_proposals(proposals)
            self.status.set("Risposta ricevuta. Verifica le proposte.")
        else:
            self.set_output(result)
            self.status.set("Risposta ricevuta. Verifica il risultato.")
        self.after(100, self.check_results)

    def offer_proposals(self, proposals):
        if not proposals:
            self.set_output("Nessuna attività proposta. Puoi aggiungerne una manualmente.")
            return
        self.set_output("Proposte da verificare:\n\n" + "\n".join(
            f'{p["titolo"]} | {p["data"] or "senza data"} | {p["ora"] or "senza ora"} | {p["priorita"]} | {p["note"]}'
            for p in proposals))
        if messagebox.askyesno("Aggiungi proposte", f"Sono state proposte {len(proposals)} attività. Aggiungerle tutte alla lista locale? Potrai modificarle o rimuoverle.", parent=self):
            if self.persist({**self.state, "attivita": self.state["attivita"] + proposals}):
                self.refresh()

    def export(self):
        items = self.state["attivita"]
        try:
            content = calendar_export.build_ics(items)
        except ValueError as exc:
            messagebox.showerror("Esportazione impossibile", str(exc), parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title="Esporta eventi", defaultextension=".ics",
                                            filetypes=[("Calendario iCalendar", "*.ics")],
                                            confirmoverwrite=False)
        if not path:
            return
        summary = "\n".join(f'{item["data"]} {item["ora"] or "(intera giornata)"} — {item["titolo"]} [{item["priorita"]}]\n  Note: {item["note"]}' for item in items)
        if not self.confirm_details(
            "Conferma esportazione",
            f"Creare il file {path}? Gli eventi con ora durano un'ora; gli altri occupano l'intera giornata. Il calendario non sarà modificato automaticamente.",
            summary, "Crea file .ics"
        ):
            return
        try:
            with open(path, "xb") as file:
                file.write(content)
        except FileExistsError:
            messagebox.showerror("File già esistente", "Per evitare di sovrascrivere file, scegli un nome diverso.", parent=self)
        except OSError as exc:
            messagebox.showerror("Esportazione non riuscita", f"Impossibile creare il file: {exc}", parent=self)
        else:
            self.status.set("File .ics creato. Importalo manualmente nel calendario dopo averlo verificato.")
