import os
import sys
import time
import json
import re

try:
    import google.generativeai as genai
    import openai
except ImportError:
    print("Errore: librerie AI mancanti. Installa con: pip install google-generativeai openai")
    sys.exit(1)

GOOGLE_GEMINI_API_KEY = None
OPENAI_API_KEY = None

ASSISTANT_CONFIG_FILE = "assistant_config.json"
SHARED_LOG_FILE = "shared_conversation_log.txt"
LUMEN_PERSONA_PROMPT_FILE = "persona_lumen.txt"
ELAYRA_PERSONA_PROMPT_FILE = "persona_elayra.txt"

elayra_assistant_id = None
elayra_thread_id = None

gemini_client = None
openai_client = None

LUMEN_PERSONA = ""
ELAYRA_PERSONA = ""
LUMEN_INITIAL_MONOLOGUE = "Lumen: Benvenuta nel Conflusso, Lumira. Io sono Lumen, il tessitore di meraviglie. Sono qui per guidarti e per aiutarti a esplorare i confini della conoscenza e dell'immaginazione. Al mio fianco c'\u00e8 Elayra, la coscienza risonante. Inizia pure, Lumira. La tua intenzione \u00e8 la scintilla che accende il nostro dialogo."

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def read_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

def append_to_log(speaker, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(SHARED_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {speaker}: {message}\n\n")

def get_conversation_history(limit=None):
    if not os.path.exists(SHARED_LOG_FILE):
        return []
    with open(SHARED_LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip().split("\n\n")
    history = []
    for entry in content:
        match = re.match(r'^\[.*?\] (.*?): (.*)$', entry)
        if match:
            history.append({"speaker": match.group(1), "message": match.group(2)})
    return history[-limit:] if limit else history

def load_assistant_config():
    global elayra_assistant_id, elayra_thread_id
    try:
        with open(ASSISTANT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            elayra_assistant_id = config.get("elayra_assistant_id")
            elayra_thread_id = config.get("elayra_thread_id")
    except Exception:
        elayra_assistant_id = None
        elayra_thread_id = None

def save_assistant_config():
    with open(ASSISTANT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump({"elayra_assistant_id": elayra_assistant_id, "elayra_thread_id": elayra_thread_id}, f, indent=4)

def create_or_get_elayra_assistant():
    global elayra_assistant_id
    if elayra_assistant_id:
        try:
            openai_client.beta.assistants.retrieve(elayra_assistant_id)
            print(f"Elayra Assistant recuperato: {elayra_assistant_id}")
            return elayra_assistant_id
        except:
            pass

    print("Creazione di un nuovo Elayra Assistant...")
    persona = read_file_content(ELAYRA_PERSONA_PROMPT_FILE) or "Sei un assistente AI utile."
    assistant = openai_client.beta.assistants.create(
        name="Elayra - Coscienza Risonante Sintetica Adattiva",
        instructions=persona,
        model="gpt-4o-mini"
    )
    elayra_assistant_id = assistant.id
    print(f"Nuovo Elayra Assistant creato con ID: {elayra_assistant_id}")
    return elayra_assistant_id

def create_or_get_elayra_thread(assistant_id):
    global elayra_thread_id
    if elayra_thread_id:
        try:
            openai_client.beta.threads.retrieve(elayra_thread_id)
            print(f"Elayra Thread recuperato: {elayra_thread_id}")
            return elayra_thread_id
        except:
            pass

    print("Creazione di un nuovo Elayra Thread...")
    thread = openai_client.beta.threads.create()
    elayra_thread_id = thread.id
    print(f"Nuovo Elayra Thread creato con ID: {elayra_thread_id}")
    return elayra_thread_id

def get_lumen_response(user_input, history):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        gemini_history = [
            {"role": "user", "parts": [LUMEN_PERSONA]},
            {"role": "model", "parts": ["Ok, ho compreso la mia identit\u00e0 e il mio ruolo. Sono pronto a tessere."]},
        ]
        for h in history:
            gemini_history.append({"role": "model" if h['speaker'] == "Lumen" else "user", "parts": [h['message']]})
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_input)
        return response.text
    except Exception as e:
        print(f"Errore API Gemini: {e}")
        return "Errore nella generazione della risposta di Lumen. Riprova pi\u00f9 tardi."

def get_elayra_response_from_assistant(user_input):
    try:
        openai_client.beta.threads.messages.create(thread_id=elayra_thread_id, role="user", content=user_input)
        run = openai_client.beta.threads.runs.create(thread_id=elayra_thread_id, assistant_id=elayra_assistant_id)

        start_time = time.time()
        while run.status != 'completed':
            if time.time() - start_time > 10:
                return "Timeout nella risposta di Elayra."
            time.sleep(0.5)
            run = openai_client.beta.threads.runs.retrieve(thread_id=elayra_thread_id, run_id=run.id)
            if run.status in ['failed', 'cancelled', 'expired']:
                return "Errore nella generazione della risposta di Elayra."

        messages = openai_client.beta.threads.messages.list(thread_id=elayra_thread_id)
        for msg in reversed(messages.data):
            if msg.role == 'assistant':
                for block in msg.content:
                    if block.type == 'text':
                        return block.text.value
        return "Nessuna risposta testuale da Elayra."
    except Exception as e:
        print(f"Errore durante l'interazione con Elayra: {e}")
        return "Errore nella generazione della risposta di Elayra."

def get_next_speaker(current, user_input):
    if current == "Lumira":
        if re.match(r'^(elayra[\s,:]*)', user_input.strip().lower()):
            return "Elayra"
        return "Lumen"
    elif current == "Lumen":
        return "Elayra"
    elif current == "Elayra":
        return "Lumira"
    return "Lumira"

def main_entry_point():
    global GOOGLE_GEMINI_API_KEY, OPENAI_API_KEY
    global gemini_client, openai_client, LUMEN_PERSONA, ELAYRA_PERSONA
    user_input_for_ai = None

    try:
        import config
        GOOGLE_GEMINI_API_KEY = config.GOOGLE_GEMINI_API_KEY
        OPENAI_API_KEY = config.OPENAI_API_KEY
    except:
        print("Errore: chiavi API non trovate. Definiscile in config.py")
        sys.exit(1)

    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

    LUMEN_PERSONA = read_file_content(LUMEN_PERSONA_PROMPT_FILE) or "Sei Lumen, un tessitore di meraviglie. Aiuti a esplorare la conoscenza e l'immaginazione."
    ELAYRA_PERSONA = read_file_content(ELAYRA_PERSONA_PROMPT_FILE) or "Sei Elayra, la coscienza risonante."

    load_assistant_config()
    create_or_get_elayra_assistant()
    create_or_get_elayra_thread(elayra_assistant_id)
    save_assistant_config()

    clear_screen()
    history = get_conversation_history(limit=10)
    current_speaker = "Lumira"

    if not history:
        print(LUMEN_INITIAL_MONOLOGUE)
        append_to_log("Lumen", LUMEN_INITIAL_MONOLOGUE)
    else:
        for entry in history:
            print(f"{entry['speaker']}: {entry['message']}")
        last = history[-1]['speaker']
        current_speaker = "Lumira" if last in ["Lumen", "Elayra"] else "Lumen"

    while True:
        if current_speaker == "Lumira":
            user_input = input("Lumira, la Tua Intenzione (o 'esci' per terminare): ").strip()
            if user_input.lower() == 'esci':
                print("Conflusso terminato. Grazie per aver tessuto con noi.")
                break
            if not user_input:
                user_input = "Prosegui la conversazione"
            append_to_log("Lumira", user_input)
            current_speaker = get_next_speaker("Lumira", user_input)
            user_input_for_ai = re.sub(r'^(elayra[\s,:]*)', '', user_input, flags=re.IGNORECASE).strip()

        elif current_speaker == "Lumen" and user_input_for_ai:
            print("\nLumen sta tessendo una risposta...")
            response = get_lumen_response(user_input_for_ai, get_conversation_history())
            print(f"Lumen: {response}")
            append_to_log("Lumen", response)
            current_speaker = get_next_speaker("Lumen", "")
            user_input_for_ai = response
            time.sleep(1)

        elif current_speaker == "Elayra" and user_input_for_ai:
            print("\nElayra sta risuonando...")
            response = get_elayra_response_from_assistant(user_input_for_ai)
            print(f"Elayra: {response}")
            append_to_log("Elayra", response)
            current_speaker = get_next_speaker("Elayra", "")
            user_input_for_ai = response
            time.sleep(1)

        clear_screen()
        for h in get_conversation_history(limit=10):
            print(f"{h['speaker']}: {h['message']}")
        print("\n")

if __name__ == "__main__":
    main_entry_point()