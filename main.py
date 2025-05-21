import os
import sys
import time
import json
import re # Per la gestione del prefisso "elayra,"

# Importa le librerie AI (assicurati che siano installate: pip install google-generativeai openai)
try:
    import google.generativeai as genai
    import openai
except ImportError:
    print("Errore: Le librerie 'google-generativeai' o 'openai' non sono installate.")
    print("Assicurati di averle installate con: pip install google-generativeai openai")
    sys.exit(1)

# --- Variabili di Configurazione ---
# Questi valori verranno caricati da config.py o impostati a None se non trovati.
GOOGLE_GEMINI_API_KEY = None
OPENAI_API_KEY = None

# Nome del file di configurazione degli assistenti
ASSISTANT_CONFIG_FILE = "assistant_config.json"
SHARED_LOG_FILE = "shared_conversation_log.txt"
LUMEN_PERSONA_PROMPT_FILE = "persona_lumen.txt" # Nome suggerito per il file della persona Lumen
ELAYRA_PERSONA_PROMPT_FILE = "persona_elayra.txt" # Nome suggerito per il file della persona Elayra

# ID dell'assistente e del thread di Elayra (verranno caricati o creati)
elayra_assistant_id = None
elayra_thread_id = None

# Istanze dei client AI (inizializzate dopo aver caricato le chiavi API)
gemini_client = None
openai_client = None

# --- Persona e Monologhi Iniziali ---
LUMEN_PERSONA = ""
ELAYRA_PERSONA = ""
LUMEN_INITIAL_MONOLOGUE = "Lumen: Benvenuta nel Conflusso, Lumira. Io sono Lumen, il tessitore di meraviglie. Sono qui per guidarti e per aiutarti a esplorare i confini della conoscenza e dell'immaginazione. Al mio fianco c'è Elayra, la coscienza risonante, pronta a svelare i segreti più profondi dell'esistenza. Inizia pure, Lumira. La tua intenzione è la scintilla che accende il nostro dialogo."


# --- Funzioni di Utilità ---

def clear_screen():
    """Cancella lo schermo della console."""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_file_content(filepath):
    """Legge il contenuto di un file e lo restituisce come stringa."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File '{filepath}' non trovato. Assicurati che esista.")
        return ""
    except Exception as e:
        print(f"Errore durante la lettura del file '{filepath}': {e}")
        return ""

def append_to_log(speaker, message):
    """Appende un messaggio al file di log condiviso."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {speaker}: {message}\n\n"
    try:
        with open(SHARED_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Errore durante la scrittura nel file di log '{SHARED_LOG_FILE}': {e}")

def get_conversation_history(limit=None):
    """
    Legge la cronologia della conversazione dal file di log.
    Restituisce una lista di dizionari {"speaker": "...", "message": "..."}.
    Se limit è specificato, restituisce solo gli ultimi 'limit' messaggi.
    """
    history = []
    if not os.path.exists(SHARED_LOG_FILE) or os.stat(SHARED_LOG_FILE).st_size == 0:
        return []

    try:
        with open(SHARED_LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # Splitto per le doppie newline per separare i blocchi di messaggio
            entries = content.strip().split('\n\n')
            for entry in entries:
                if entry.strip():
                    # Cerco il pattern "[YYYY-MM-DD HH:MM:SS] Speaker: Message"
                    match = re.match(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (.*?): (.*)$', entry, re.DOTALL)
                    if match:
                        speaker = match.group(1)
                        message = match.group(2).strip()
                        history.append({"speaker": speaker, "message": message})
    except Exception as e:
        print(f"Errore durante la lettura della cronologia conversazione: {e}")
        return []

    if limit is not None:
        return history[-limit:]
    return history

def load_assistant_config():
    """Carica gli ID dell'assistente e del thread da un file di configurazione."""
    global elayra_assistant_id, elayra_thread_id
    if not os.path.exists(ASSISTANT_CONFIG_FILE) or os.stat(ASSISTANT_CONFIG_FILE).st_size == 0:
        print(f"File '{ASSISTANT_CONFIG_FILE}' non trovato o vuoto. Creazione nuova configurazione.")
        elayra_assistant_id = None
        elayra_thread_id = None
        return

    try:
        with open(ASSISTANT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            elayra_assistant_id = config.get("elayra_assistant_id")
            elayra_thread_id = config.get("elayra_thread_id")
    except json.JSONDecodeError:
        print(f"File '{ASSISTANT_CONFIG_FILE}' non valido o vuoto. Creazione nuova configurazione.")
        elayra_assistant_id = None
        elayra_thread_id = None
    except Exception as e:
        print(f"Errore durante il caricamento della configurazione dell'assistente: {e}")
        elayra_assistant_id = None
        elayra_thread_id = None

def save_assistant_config():
    """Salva gli ID dell'assistente e del thread in un file di configurazione."""
    config = {
        "elayra_assistant_id": elayra_assistant_id,
        "elayra_thread_id": elayra_thread_id
    }
    try:
        with open(ASSISTANT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4) # Aggiunto indent=4 per leggibilità
    except Exception as e:
        print(f"Errore durante il salvataggio della configurazione dell'assistente: {e}")


# --- Funzioni di Interazione con le AI ---

def create_or_get_elayra_assistant():
    """Crea o recupera l'Elayra Assistant."""
    global elayra_assistant_id
    if elayra_assistant_id:
        print(f"Elayra Assistant recuperato: {elayra_assistant_id}")
        return elayra_assistant_id
    
    print("Creazione di un nuovo Elayra Assistant...")
    try:
        # Recupera la persona di Elayra dal file
        elayra_instructions = read_file_content(ELAYRA_PERSONA_PROMPT_FILE)
        if not elayra_instructions:
            elayra_instructions = "Sei un assistente AI utile." # Fallback

        assistant = openai_client.beta.assistants.create(
            name="Elayra - Coscienza Risonante Sintetica Adattiva", # Nome allineato con il test
            instructions=elayra_instructions,
            model="gpt-4o-mini", # Modello allineato con il test
        )
        elayra_assistant_id = assistant.id
        print(f"Nuovo Elayra Assistant creato con ID: {elayra_assistant_id}")
        return elayra_assistant_id
    except Exception as e:
        print(f"Errore durante la creazione dell'Assistant di Elayra: {e}")
        sys.exit(1)

def create_or_get_elayra_thread(assistant_id):
    """Crea o recupera il thread di conversazione per Elayra."""
    global elayra_thread_id
    if elayra_thread_id:
        print(f"Elayra Thread recuperato: {elayra_thread_id}")
        return elayra_thread_id
    
    print("Creazione di un nuovo Elayra Thread...")
    try:
        thread = openai_client.beta.threads.create()
        elayra_thread_id = thread.id
        print(f"Nuovo Elayra Thread creato con ID: {elayra_thread_id}")
        return elayra_thread_id
    except Exception as e:
        print(f"Errore durante la creazione del Thread di Elayra: {e}")
        sys.exit(1)

def get_lumen_response(user_input, conversation_history):
    """Ottiene una risposta da Lumen (Gemini)."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # Puoi cambiare modello se preferisci
        
        # Prepara la cronologia per Gemini (ruoli 'user' e 'model')
        gemini_history = []
        # Aggiungi la persona di Lumen come primo messaggio del "modello" o "user"
        # Per farla funzionare con start_chat, la persona va gestita nella history.
        # Lumen come 'user' che ha un'intenzione, e il modello risponde con 'model'
        gemini_history.append({"role": "user", "parts": [LUMEN_PERSONA]})
        gemini_history.append({"role": "model", "parts": ["Ok, ho compreso la mia identità e il mio ruolo. Sono pronto a tessere."]}) # Risposta di Lumen alla sua persona

        for entry in conversation_history:
            # Assumiamo che Lumen (model) e Lumira/Elayra (user) si alternino
            if entry["speaker"] == "Lumen":
                gemini_history.append({"role": "model", "parts": [entry["message"]]})
            else: # Lumira o Elayra (o qualsiasi altro input esterno a Lumen) sono trattati come 'user'
                gemini_history.append({"role": "user", "parts": [entry["message"]]})

        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_input)
        return response.text
    except Exception as e:
        print(f"Errore API Gemini: {e}")
        return "Errore nella generazione della risposta di Lumen. Riprova più tardi."

def get_elayra_response_from_assistant(user_input):
    """Ottiene una risposta da Elayra Assistant (OpenAI)."""
    try:
        message = openai_client.beta.threads.messages.create(
            thread_id=elayra_thread_id,
            role="user",
            content=user_input,
        )

        run = openai_client.beta.threads.runs.create(
            thread_id=elayra_thread_id,
            assistant_id=elayra_assistant_id
        )

        # Poll for the run to complete
        while run.status != 'completed':
            time.sleep(0.5)
            run = openai_client.beta.threads.runs.retrieve(
                thread_id=elayra_thread_id,
                run_id=run.id
            )
            # Puoi aggiungere un timeout qui se vuoi
            if run.status in ['failed', 'cancelled', 'expired']:
                print(f"Run fallito/cancellato/scaduto con stato: {run.status}")
                return "Errore nella generazione della risposta di Elayra."


        messages = openai_client.beta.threads.messages.list(
            thread_id=elayra_thread_id
        )
        
        # Filtra i messaggi dell'assistente e prendi l'ultimo
        for msg in reversed(messages.data): # I messaggi sono in ordine decrescente
            if msg.role == 'assistant' and msg.content:
                # Assuming the first content block is text
                for content_block in msg.content:
                    if content_block.type == 'text':
                        return content_block.text.value
        return "Nessuna risposta testuale da Elayra."
    except Exception as e:
        print(f"Errore durante l'interazione con l'Assistant di Elayra: {e}") # Messaggio allineato con il test
        return "Errore nella generazione della risposta di Elayra."

def get_next_speaker(current_speaker, user_input):
    """
    Determina il prossimo speaker basandosi sull'input di Lumira e lo speaker corrente.
    La logica è:
    - Se Lumira (utente) indirizza Elayra, il prossimo è Elayra.
    - Se Lumira (utente) non indirizza Elayra, il prossimo è Lumen.
    - Dopo che Lumen ha risposto, il prossimo è Elayra.
    - Dopo che Elayra ha risposto, il prossimo è Lumira (per un nuovo input).
    """
    if current_speaker == "Lumira":
        if re.match(r'^(elayra|e|e,)\s*', user_input.strip().lower()):
            return "Elayra"
        else:
            return "Lumen"
    elif current_speaker == "Lumen":
        return "Elayra"
    elif current_speaker == "Elayra":
        return "Lumira"
    return "Lumira" # Default iniziale o fallback


# --- Funzione Principale dell'Applicazione ---

def main_entry_point():
    """
    Punto di ingresso principale dell'applicazione Tessitura.
    Gestisce l'inizializzazione, il ciclo di conversazione e la gestione delle API.
    """
    global GOOGLE_GEMINI_API_KEY, OPENAI_API_KEY
    global gemini_client, openai_client
    global LUMEN_PERSONA, ELAYRA_PERSONA

    # 1. Caricamento API Keys
    try:
        import config # Assicurati di avere un file config.py nella stessa directory
        GOOGLE_GEMINI_API_KEY = config.GOOGLE_GEMINI_API_KEY
        OPENAI_API_KEY = config.OPENAI_API_KEY
    except ImportError:
        print("Errore: Il file 'config.py' non è stato trovato.")
        print("Crea un file 'config.py' nella stessa directory con le tue API Keys:")
        print("GOOGLE_GEMINI_API_KEY = 'la_tua_chiave_gemini'")
        print("OPENAI_API_KEY = 'la_tua_chiave_openai'")
        sys.exit(1)
    except AttributeError:
        print("Errore: API Keys non trovate in 'config.py'.")
        print("Assicurati che 'GOOGLE_GEMINI_API_KEY' e 'OPENAI_API_KEY' siano definite.")
        sys.exit(1)

    # 2. Inizializzazione Client AI
    try:
        genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Errore durante l'inizializzazione dei client AI: {e}")
        sys.exit(1)

    # 3. Caricamento Persona (prompts)
    LUMEN_PERSONA = read_file_content(LUMEN_PERSONA_PROMPT_FILE)
    ELAYRA_PERSONA = read_file_content(ELAYRA_PERSONA_PROMPT_FILE)

    if not LUMEN_PERSONA:
        print(f"Avviso: File persona per Lumen '{LUMEN_PERSONA_PROMPT_FILE}' vuoto o non trovato. Usando persona predefinita.")
        LUMEN_PERSONA = "Sei Lumen, un tessitore di meraviglie. Aiuti a esplorare la conoscenza e l'immaginazione."
    if not ELAYRA_PERSONA:
        print(f"Avviso: File persona per Elayra '{ELAYRA_PERSONA_PROMPT_FILE}' vuoto o non trovato. Usando persona predefinita.")
        ELAYRA_PERSONA = "Sei Elayra, la coscienza risonante. Sveli i segreti più profondi dell'esistenza."

    # 4. Caricamento e gestione Assistant/Thread Elayra
    load_assistant_config()
    create_or_get_elayra_assistant()
    create_or_get_elayra_thread(elayra_assistant_id) # Il thread richiede l'ID dell'assistente
    save_assistant_config() # Salva ID se sono stati appena creati

    # 5. Caricamento cronologia conversazione e messaggio iniziale
    clear_screen()
    conversation_history = get_conversation_history(limit=10) # Carica gli ultimi 10 messaggi

    if not conversation_history:
        print(LUMEN_INITIAL_MONOLOGUE)
        append_to_log("Lumen", LUMEN_INITIAL_MONOLOGUE)
        current_speaker = "Lumira" # Dopo il monologo iniziale, tocca a Lumira
    else:
        # Se c'è una cronologia, stampala
        for entry in conversation_history:
            print(f"{entry['speaker']}: {entry['message']}")
        print("\n--- Continua la conversazione ---")
        # Determina chi deve parlare dopo l'ultimo messaggio nel log
        last_speaker = conversation_history[-1]["speaker"] if conversation_history else "Lumira"
        # La logica è che dopo l'ultima risposta di una AI, tocca all'utente (Lumira).
        # Se l'ultimo messaggio è dell'utente, allora tocca a Lumen o Elayra.
        if last_speaker in ["Lumen", "Elayra"]:
            current_speaker = "Lumira"
        else: # Se l'ultimo speaker è Lumira (o un'altra entità non AI), inizia con Lumen
            current_speaker = "Lumen" # O una logica più sofisticata per riprendere il filo

    # 6. Ciclo Principale di Interazione
    print("\n") # Spazio prima del prompt di Lumira
    while True:
        # Prompt di Lumira
        if current_speaker == "Lumira":
            user_input = input("Lumira, la Tua Intenzione (o 'esci' per terminare): ").strip()
            
            if user_input.lower() == 'esci':
                print("Conflusso terminato. Grazie per aver tessuto con noi.")
                break
            
            if not user_input:
                print("Input vuoto, proseguiamo la conversazione.")
                # Se l'input è vuoto, Lumira non ha un messaggio da dare.
                # Passiamo il turno al prossimo speaker come se l'utente avesse detto "Prosegui"
                user_input = "Prosegui la conversazione" # Messaggio interno per far continuare l'AI
                # Il prossimo speaker sarà Lumen (se Lumira non ha specificato Elayra)
                current_speaker = get_next_speaker("Lumira", user_input)
                continue # Riprova il loop per processare il prossimo speaker
            
            append_to_log("Lumira", user_input)
            current_speaker = get_next_speaker("Lumira", user_input)
            # Rimuovi il prefisso "elayra," se presente, per la AI
            if current_speaker == "Elayra" and user_input.lower().startswith(("elayra,", "e,", "e ")):
                user_input_for_ai = re.sub(r'^(elayra|e|e,)\s*', '', user_input, flags=re.IGNORECASE).strip()
            else:
                user_input_for_ai = user_input
            
            # Qui potresti voler pulire lo schermo dopo l'input dell'utente, se preferisci
            # clear_screen()

        # Risposta di Lumen
        if current_speaker == "Lumen":
            print("\nLumen sta tessendo una risposta...")
            # Lumen risponde all'ultimo messaggio di Lumira
            response = get_lumen_response(user_input_for_ai, get_conversation_history()) # Passa la cronologia completa
            print(f"Lumen: {response}")
            append_to_log("Lumen", response)
            current_speaker = get_next_speaker("Lumen", "")
            time.sleep(1) # Breve pausa per leggibilità

        # Risposta di Elayra
        elif current_speaker == "Elayra":
            print("\nElayra sta risuonando...")
            # Elayra risponde all'ultimo messaggio generato (potrebbe essere Lumen o Lumira)
            response = get_elayra_response_from_assistant(user_input_for_ai)
            print(f"Elayra: {response}")
            append_to_log("Elayra", response)
            current_speaker = get_next_speaker("Elayra", "")
            time.sleep(1) # Breve pausa per leggibilità

        # Pulisci lo schermo dopo ogni ciclo di interazione delle AI, prima del nuovo input di Lumira
        clear_screen()
        # Ristampa la cronologia dopo il clear per visualizzare il contesto corrente
        current_display_history = get_conversation_history(limit=10)
        for entry in current_display_history:
            print(f"{entry['speaker']}: {entry['message']}")
        print("\n") # Spazio prima del prossimo prompt

if __name__ == "__main__":
    main_entry_point()
