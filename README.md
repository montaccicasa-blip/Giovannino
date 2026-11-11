# Assistente personale

Applicazione desktop in italiano per Windows 10 e 11. Usa Python e Tkinter, senza dipendenze esterne. Non richiede un account per la modalità dimostrativa.

## Installazione e avvio

1. Installa Python 3.10 o successivo da [python.org](https://www.python.org/downloads/windows/), includendo **tcl/tk and IDLE** e il launcher `py`. Se richiesto, abilita anche l'aggiunta di Python al PATH.
2. Scarica o clona questo repository e apri la cartella estratta.
3. Fai doppio clic su `avvia.bat`, oppure apri PowerShell nella cartella ed esegui `py -3 main.py`.
4. L'app si apre in **Dimostrativa (offline)**. Incolla un messaggio, inserisci eventualmente le istruzioni personali e scegli un'azione. Le istruzioni si conservano soltanto premendo **Salva preferenze**.

Non è ancora disponibile un installer o eseguibile autonomo: Python deve rimanere installato. L'interfaccia usa i normali controlli Tk, utilizzabili anche da tastiera; la compatibilità con specifici screen reader non è stata verificata.

## Uso e integrazioni

- **Messaggi:** incolla il testo scelto da Thunderbird, WhatsApp Desktop o un'altra fonte. L'app non legge automaticamente nuove email o chat, non si collega ai rispettivi account e non usa API WhatsApp non ufficiali. Non crea direttamente bozze in Thunderbird: copia il risultato e incollalo manualmente nella relativa applicazione. Nessun messaggio viene inviato dall'app.
- **Risposta:** in modalità demo viene restituito un testo generico da personalizzare, non una risposta che interpreta il messaggio. Con un provider configurato il risultato è una bozza da verificare.
- **Azioni:** la demo propone una voce per ogni riga non vuota, riconoscendo solo date `AAAA-MM-GG` e ore `HH:MM` presenti sulla stessa riga. Non comprende il linguaggio naturale né le date relative; verifica e correggi tutto. L'AI può proporre attività, ma può sbagliare o non rispettare il formato. Prima di aggiungerle tutte all'elenco viene chiesta conferma. Puoi poi modificarle o rimuoverle singolarmente.
- **Agenda:** scegli giorno o settimana, a partire dalla data locale odierna. La demo ordina le attività del periodo e quelle senza data, segnala gli inizi coincidenti e non assegna automaticamente fasce orarie; verifica tu durate e sovrapposizioni. L'AI propone un programma sullo stesso insieme di attività, da controllare.
- **Calendario:** **Esporta .ics** riepiloga tutte le attività e richiede conferma prima di creare il file; tutte devono avere una data. Senza ora, l'evento dura l'intera giornata; con ora, dura convenzionalmente un'ora. Le ore sono locali e senza fuso orario incorporato. L'app non accede al calendario: importa il file manualmente e verifica gli eventi prima di confermare l'importazione. Un file esistente non viene sovrascritto. Ogni esportazione genera nuovi identificativi: importare più volte può creare duplicati.

## Provider AI online (facoltativo)

Serve un servizio con API **Chat Completions compatibile**, endpoint HTTPS completo, modello e chiave API propri. Un abbonamento ChatGPT non implica accesso API; costi, disponibilità e trattamento dei dati dipendono dal provider. L'integrazione è generica e non è stata verificata con ogni provider.

Imposta le variabili nella sessione PowerShell **prima di avviare** l'app (sostituisci URL e modello con quelli del tuo provider; `.env.example` è solo un modello e non viene caricato automaticamente):

```powershell
$env:ASSISTENTE_AI_URL = "https://api.example.com/v1/chat/completions"
$env:ASSISTENTE_AI_MODEL = "nome-del-modello"
$env:ASSISTENTE_AI_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Chiave API" -AsSecureString)).Password
py -3 main.py
```

Non scrivere la chiave nel codice, in `.env.example`, nei messaggi o nel repository. Le variabili impostate così durano per la sessione PowerShell e possono essere accessibili ai processi con adeguati permessi sul PC. Usa un account Windows protetto. Seleziona **Provider AI online** nell'app: ogni richiesta mostra destinatario e corpo completo (modello, istruzioni, testo e, per l'agenda, attività pertinenti) e richiede il consenso esplicito. La chiave è inviata nell'intestazione di autenticazione, non nel corpo mostrato. Annullando non parte alcuna richiesta. I redirect sono bloccati. Il provider potrebbe conservare i dati secondo le proprie condizioni; non inserire informazioni che non desideri condividere.

## Dati locali e rimozione

Preferenze e attività sono salvate in `%LOCALAPPDATA%\AssistentePersonale\dati.json` come testo non cifrato, protetto soltanto dai permessi del tuo account Windows. I messaggi incollati e le risposte non vengono salvati dall'app. **Cancella dati locali** chiede conferma e sostituisce preferenze e attività con dati vuoti; non garantisce la cancellazione sicura di copie, backup o tracce del filesystem. Gli appunti e i file `.ics` esportati restano sotto il controllo dell'utente.

Per rimuovere l'app, cancella prima i dati dall'interfaccia se desideri azzerarli, poi elimina manualmente la cartella del repository e, se presente, `%LOCALAPPDATA%\AssistentePersonale`. Elimina separatamente eventuali esportazioni. Disinstalla Python solo se non ti serve per altre applicazioni. Se hai configurato la chiave soltanto nella sessione PowerShell, chiudi quella finestra.

## Verifica per sviluppatori

Nella cartella del progetto: `py -3 -m unittest discover -s tests`. I test sono offline; non verificano Thunderbird, WhatsApp, provider reali, calendari esterni o l'interfaccia su Windows.
