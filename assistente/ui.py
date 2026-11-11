import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import ai, calendar, storage


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assistente personale")
        self.geometry("1000x800")
        self.minsize(720, 600)
        try:
            data = storage.load()
        except (OSError, ValueError) as error:
            messagebox.showerror("Dati locali", f"Impossibile leggere i dati locali: {error}\nI dati non saranno sovrascritti. Risolvi il problema e riavvia.")
            self.destroy()
            return
        self.tasks = data["attivita"]
        self.results = queue.Queue()
        self.pending = False

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        home = ttk.Frame(tabs, padding=10)
        agenda = ttk.Frame(tabs, padding=10)
        tabs.add(home, text="Messaggi e assistente")
        tabs.add(agenda, text="Attività e agenda")

        ttk.Label(home, text="Incolla un messaggio scelto da Thunderbird o WhatsApp Desktop. Nessun messaggio viene letto o inviato automaticamente.", wraplength=900).pack(anchor="w")
        self.source = tk.StringVar(value="Email (Thunderbird)")
        ttk.Label(home, text="Origine del testo").pack(anchor="w", pady=(8, 0))
        ttk.Combobox(home, textvariable=self.source, state="readonly", values=("Email (Thunderbird)", "WhatsApp Desktop", "Altro")).pack(anchor="w")
        ttk.Label(home, text="Messaggio da sottoporre all'assistente").pack(anchor="w", pady=(8, 0))
        self.message = scrolledtext.ScrolledText(home, height=6, wrap="word")
        self.message.pack(fill="both", expand=True)
        ttk.Label(home, text="Tono, stile e istruzioni personali (salvati solo con il pulsante sotto)").pack(anchor="w", pady=(8, 0))
        self.instructions = scrolledtext.ScrolledText(home, height=3, wrap="word")
        self.instructions.pack(fill="x")
        self.instructions.insert("1.0", data["istruzioni"])
        ttk.Button(home, text="Salva preferenze", command=self.save).pack(anchor="w", pady=4)
        self.mode = tk.StringVar(value="demo")
        modes = ttk.Frame(home)
        modes.pack(fill="x")
        ttk.Radiobutton(modes, text="Dimostrativa (locale)", variable=self.mode, value="demo").pack(side="left")
        ttk.Radiobutton(modes, text="AI online configurata", variable=self.mode, value="online").pack(side="left", padx=12)
        ttk.Label(modes, text="Programma:").pack(side="left")
        self.period = tk.StringVar(value="settimanale")
        ttk.Combobox(modes, textvariable=self.period, state="readonly", width=13, values=("giornaliero", "settimanale")).pack(side="left", padx=5)
        buttons = ttk.Frame(home)
        buttons.pack(fill="x", pady=5)
        for label, action in (("Prepara una risposta", "risposta"), ("Estrai azioni", "azioni"), ("Organizza il mio tempo", "tempo")):
            ttk.Button(buttons, text=label, command=lambda a=action: self.run_action(a)).pack(side="left", padx=(0, 5))
        ttk.Label(home, text="Risultato modificabile: controlla sempre prima di usarlo").pack(anchor="w")
        self.output = scrolledtext.ScrolledText(home, height=7, wrap="word")
        self.output.pack(fill="both", expand=True)
        output_buttons = ttk.Frame(home)
        output_buttons.pack(fill="x", pady=5)
        ttk.Button(output_buttons, text="Copia risultato", command=self.copy_output).pack(side="left")
        ttk.Button(output_buttons, text="Aggiungi le azioni dal risultato", command=self.add_extracted).pack(side="left", padx=5)
        self.status = tk.StringVar(value="Pronto. Nessun contenuto è inviato senza conferma.")
        ttk.Label(home, textvariable=self.status, wraplength=900).pack(anchor="w")

        ttk.Label(agenda, text="Seleziona un'attività per modificarla. Data: AAAA-MM-GG; ora: HH:MM (facoltative).").pack(anchor="w")
        self.table = ttk.Treeview(agenda, columns=("titolo", "data", "ora", "priorita", "note"), show="headings", selectmode="browse", height=10)
        for key, label, width in (("titolo", "Titolo", 240), ("data", "Data", 110), ("ora", "Ora", 70), ("priorita", "Priorità", 80), ("note", "Note", 300)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=60)
        self.table.pack(fill="both", expand=True, pady=5)
        self.table.bind("<<TreeviewSelect>>", self.select_task)
        form = ttk.Frame(agenda)
        form.pack(fill="x")
        self.fields = {}
        for row, (key, label) in enumerate((("titolo", "Titolo"), ("data", "Data"), ("ora", "Ora"), ("priorita", "Priorità"), ("note", "Note"))):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2)
            variable = tk.StringVar(value="Media" if key == "priorita" else "")
            self.fields[key] = variable
            widget = ttk.Combobox(form, textvariable=variable, values=("Alta", "Media", "Bassa"), state="readonly") if key == "priorita" else ttk.Entry(form, textvariable=variable)
            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        form.columnconfigure(1, weight=1)
        task_buttons = ttk.Frame(agenda)
        task_buttons.pack(fill="x", pady=8)
        for label, command in (("Nuova attività", self.new_task), ("Salva attività", self.save_task), ("Elimina attività", self.remove_task), ("Esporta eventi .ics", self.export)):
            ttk.Button(task_buttons, text=label, command=command).pack(side="left", padx=(0, 5))
        ttk.Label(agenda, text="L'esportazione non modifica il calendario: importa il file manualmente. Eventi con ora: durata predefinita di un'ora; senza ora: giornata intera.", wraplength=900).pack(anchor="w")
        ttk.Button(agenda, text="Cancella tutte le preferenze e attività locali", command=self.clear_data).pack(anchor="w", pady=10)
        self.refresh()

    def save(self):
        try:
            storage.save({"istruzioni": self.instructions.get("1.0", "end-1c"), "attivita": self.tasks})
            self.status.set("Preferenze e attività salvate sul PC.")
            return True
        except OSError as error:
            messagebox.showerror("Salvataggio", f"Impossibile salvare i dati locali: {error}")
            return False

    def run_action(self, action):
        if self.pending:
            return
        text = self.message.get("1.0", "end-1c").strip()
        instructions = self.instructions.get("1.0", "end-1c").strip()
        if action != "tempo" and not text:
            messagebox.showinfo("Messaggio", "Incolla prima il testo del messaggio.")
            return
        if self.mode.get() == "demo":
            self.show_result(ai.demo(action, text, instructions, self.tasks, self.period.get()))
            self.status.set("Risultato dimostrativo locale: controlla e modifica il contenuto.")
            return
        try:
            endpoint, model, key = ai.config()
        except ValueError as error:
            messagebox.showerror("Configurazione AI", str(error))
            return
        body = ai.payload(action, text, instructions, self.tasks, model)
        if action == "tempo":
            body["messages"][0]["content"] += " Prepara un programma " + self.period.get() + " a partire da oggi."
        if not self.confirm_payload(endpoint, body):
            self.status.set("Invio annullato: nessun dato è stato trasmesso.")
            return
        self.pending = True
        self.status.set("Richiesta AI in corso…")
        def worker():
            try:
                self.results.put((True, ai.request(endpoint, key, body)))
            except Exception:
                self.results.put((False, "Richiesta AI non riuscita. Verifica configurazione e connessione."))
        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self.check_result)

    def check_result(self):
        try:
            success, result = self.results.get_nowait()
        except queue.Empty:
            self.after(100, self.check_result)
            return
        self.pending = False
        if success:
            self.show_result(result)
            self.status.set("Risposta ricevuta. Verifica il risultato prima di usarlo.")
        else:
            messagebox.showerror("AI online", result)
            self.status.set("Richiesta non riuscita.")

    def confirm_payload(self, endpoint, body):
        dialog = tk.Toplevel(self)
        dialog.title("Conferma invio al provider AI")
        dialog.geometry("720x560")
        dialog.transient(self)
        ttk.Label(dialog, text="Questi dati saranno inviati al provider indicato tramite Internet. La chiave API sarà usata per l'autenticazione. Continua solo se acconsenti.", wraplength=680).pack(anchor="w", padx=10, pady=10)
        preview = scrolledtext.ScrolledText(dialog, wrap="word")
        preview.pack(fill="both", expand=True, padx=10)
        preview.insert("1.0", "Destinazione: " + endpoint + "\n\nDati della richiesta:\n" + json.dumps(body, ensure_ascii=False, indent=2))
        preview.config(state="disabled")
        answer = tk.BooleanVar(value=False)
        buttons = ttk.Frame(dialog)
        buttons.pack(pady=10)
        def accept():
            answer.set(True)
            dialog.destroy()
        ttk.Button(buttons, text="Annulla", command=dialog.destroy).pack(side="left", padx=5)
        ttk.Button(buttons, text="Acconsento e invia", command=accept).pack(side="left", padx=5)
        dialog.grab_set()
        dialog.wait_window()
        return answer.get()

    def show_result(self, value):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", value)

    def copy_output(self):
        self.clipboard_clear()
        self.clipboard_append(self.output.get("1.0", "end-1c"))
        self.status.set("Risultato copiato: incollalo e verifica prima di inviarlo manualmente.")

    def add_extracted(self):
        try:
            tasks = ai.parse_tasks(self.output.get("1.0", "end-1c"))
        except ValueError as error:
            messagebox.showerror("Azioni", str(error))
            return
        if not tasks:
            messagebox.showinfo("Azioni", "Nessuna attività trovata.")
            return
        if messagebox.askyesno("Aggiungi attività", f"Aggiungere {len(tasks)} attività alla lista locale? Controllale nella scheda Attività e agenda."):
            self.tasks.extend(tasks)
            self.refresh()
            self.save()

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for index, task in enumerate(self.tasks):
            self.table.insert("", "end", iid=str(index), values=tuple(task.get(k, "") for k in ("titolo", "data", "ora", "priorita", "note")))

    def select_task(self, event=None):
        selected = self.table.selection()
        if selected:
            task = self.tasks[int(selected[0])]
            for key, variable in self.fields.items():
                variable.set(task.get(key, ""))

    def new_task(self):
        self.table.selection_remove(self.table.selection())
        for key, variable in self.fields.items():
            variable.set("Media" if key == "priorita" else "")

    def save_task(self):
        task = {key: value.get().strip() for key, value in self.fields.items()}
        try:
            calendar.validate(task)
        except ValueError as error:
            messagebox.showerror("Attività", str(error))
            return
        selected = self.table.selection()
        if selected:
            self.tasks[int(selected[0])] = task
        else:
            self.tasks.append(task)
        self.refresh()
        self.new_task()
        self.save()

    def remove_task(self):
        selected = self.table.selection()
        if selected and messagebox.askyesno("Elimina attività", "Eliminare questa attività locale?"):
            del self.tasks[int(selected[0])]
            self.refresh()
            self.new_task()
            self.save()

    def export(self):
        tasks = [task for task in self.tasks if task.get("data")]
        if not tasks:
            messagebox.showinfo("Esportazione", "Aggiungi almeno un'attività con data.")
            return
        try:
            content = calendar.make_ics(tasks)
        except ValueError as error:
            messagebox.showerror("Esportazione", str(error))
            return
        summary = "\n".join(f"{t['data']} {t.get('ora') or '(giornata intera)'} — {t['titolo']}\nNote: {t.get('note', '')}" for t in tasks)
        if not messagebox.askyesno("Conferma esportazione", f"Esportare questi eventi? L'importazione nel calendario resta manuale.\n\n{summary}\n\nGli eventi con ora durano un'ora. Le attività senza data non sono esportate."):
            return
        path = filedialog.asksaveasfilename(title="Salva nuovi eventi", defaultextension=".ics", filetypes=[("Calendario iCalendar", "*.ics")])
        if path:
            try:
                with open(path, "x", encoding="utf-8", newline="") as file:
                    file.write(content)
                messagebox.showinfo("Esportazione", "File creato. Importalo manualmente nel calendario dopo aver verificato gli eventi.")
            except FileExistsError:
                messagebox.showerror("Esportazione", "Il file esiste già. Scegli un altro nome: nessun file viene sovrascritto.")
            except OSError as error:
                messagebox.showerror("Esportazione", f"Impossibile creare il file: {error}")

    def clear_data(self):
        if messagebox.askyesno("Cancella dati locali", "Cancellare tutte le preferenze e le attività salvate su questo PC? L'operazione non elimina i file ICS esportati."):
            try:
                storage.clear()
            except OSError as error:
                messagebox.showerror("Dati locali", f"Impossibile cancellare i dati: {error}")
                return
            self.tasks = []
            self.instructions.delete("1.0", "end")
            self.refresh()
            self.new_task()
            self.status.set("Preferenze e attività locali cancellate.")
