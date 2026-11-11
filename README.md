# Assistente personale

Applicazione desktop in italiano per Windows 10 e 11. Aiuta a preparare bozze, raccogliere attività e proporre un programma; **non invia messaggi e non modifica direttamente il calendario**.

## Installazione e avvio

1. Installa Python 3.10 o successivo da [python.org](https://www.python.org/downloads/windows/). Nell'installazione includi **Tcl/Tk** e il launcher `py`.
2. Scarica o copia questa cartella sul PC. Non sono necessarie librerie Python aggiuntive.
3. Apri PowerShell nella cartella (in Esplora file, digita `powershell` nella barra dell'indirizzo) ed esegui:

   ```powershell
   py -m assistente
   ```

4. Nella schermata iniziale incolla il testo scelto, imposta eventualmente tono e istruzioni personali, e seleziona un'azione. La modalità **Dimostrativa** è attiva inizialmente e non usa Internet.
5. Controlla e modifica il risultato. Copialo e incollalo manualmente in Thunderbird o WhatsApp; sarai tu a decidere se inviarlo. Per le azioni usa «Aggiungi le azioni dal risultato», poi controllale nella scheda «Attività e agenda».

Le attività sono modificabili dalla tabella: selezionane una, modifica i campi e premi «Salva attività»; usa «Nuova attività» per aggiungerne una. Salva le preferenze con l'apposito pulsante. Le attività vengono salvate quando sono aggiunte, modificate o eliminate.

## Cosa funziona e limiti

- **Thunderbird e WhatsApp Desktop:** solo copia/incolla manuale. Non vengono letti messaggi automaticamente, create bozze in Thunderbird o utilizzate API non ufficiali di WhatsApp. Non sono necessarie password delle app.
- **Dimostrazione locale:** la bozza è un modello generico, non una risposta intelligente. L'estrazione tratta ogni riga non vuota come possibile attività e riconosce solo date `AAAA-MM-GG` e orari `HH:MM`; controlla e correggi tutto. Il programma giornaliero copre oggi, quello settimanale oggi e i sei giorni successivi; include anche attività senza data, ordinate separatamente. Non assegna automaticamente fasce orarie e non rileva tutti i conflitti.
- **AI online opzionale:** usa un endpoint HTTPS compatibile con l'API Chat Completions (richiesta `model`/`messages`, risposta `choices[0].message.content`). Compatibilità, costi e disponibilità dipendono dal provider e non sono verificati da questa applicazione. L'abbonamento ChatGPT non implica accesso API. L'AI può sbagliare o restituire un formato non utilizzabile: controlla sempre bozze, date e attività.
- **Calendario:** nessun collegamento diretto. «Esporta eventi .ics» mostra un riepilogo e chiede conferma prima di creare un nuovo file. Importalo manualmente nel tuo calendario dopo aver controllato gli eventi. Le attività senza data sono escluse; gli eventi con ora durano un'ora, quelli senza ora occupano l'intera giornata. Gli orari sono locali e senza fuso orario esplicito: verifica che il calendario li interpreti correttamente. I file esistenti non vengono sovrascritti.
- Il risultato dell'estrazione AI deve essere un array JSON con `titolo`, `data`, `ora`, `priorita` e `note`. Se il provider restituisce altro, correggi il risultato oppure inserisci le attività manualmente.

## Configurazione AI online

Scegli un provider di cui ti fidi e ottieni separatamente accesso e credenziali API. Configura le seguenti variabili **nella stessa sessione PowerShell** prima dell'avvio; sostituisci i valori di esempio con quelli del tuo provider:

```powershell
$env:ASSISTENTE_AI_URL = "https://provider-esempio.it/v1/chat/completions"
$env:ASSISTENTE_AI_MODEL = "nome-modello"
$env:ASSISTENTE_AI_KEY = Read-Host "Chiave API"
py -m assistente
```

Il file `.env.example` descrive i nomi delle variabili; **non viene caricato automaticamente**. Non scrivere chiavi nel codice o in file condivisi. La chiave resta nell'ambiente della sessione e viene inviata al provider come credenziale HTTPS; chiudi PowerShell per eliminarla da quella sessione. Proteggi l'account Windows e non condividere la sessione o la chiave.

Seleziona «AI online configurata» e un'azione: prima di ogni richiesta apparirà la destinazione e il contenuto completo (istruzioni, testo, prompt, modello e, per l'organizzazione, attività inserite). Solo «Acconsento e invia» trasmette i dati. Annullando non viene inviata alcuna richiesta. I dati possono essere trattati o conservati dal provider secondo le sue condizioni: non includere informazioni che non desideri condividere. L'app non segue redirect del provider.

## Dati locali e rimozione

Preferenze e attività sono salvate in `%APPDATA%\AssistentePersonale\dati.json` in chiaro, protette dai normali permessi dell'account Windows, non cifrate. Il testo incollato e i risultati non sono salvati come messaggi, ma le attività estratte possono contenerli nelle note. Usa «Cancella tutte le preferenze e attività locali» per eliminarle, previa conferma; i file ICS esportati rimangono dove li hai salvati. Per rimuovere l'app, cancella prima i dati locali con quel pulsante, chiudi l'app e poi elimina la cartella dell'applicazione; elimina eventualmente i file ICS esportati manualmente. Nessuna email o file esterno viene cancellato dall'app.

## Verifica per sviluppatori

```powershell
py -m unittest discover -s tests
```

L'interfaccia usa i normali controlli Tk, navigabili con la tastiera. Il funzionamento effettivo con tecnologie assistive, Windows, provider e programmi di calendario specifici va verificato nell'ambiente d'uso.
