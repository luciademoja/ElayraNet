import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import os
import sys
import importlib
import builtins

# --- Configurazione Iniziale e Mock di base per i test ---
# Questo contenuto verrà "letto" quando 'config.py' viene importato da main.py
mock_config_content = """
GOOGLE_GEMINI_API_KEY = "dummy_google_key"
OPENAI_API_KEY = "dummy_openai_key"
"""

# Nomi dei file mockati per i test
MOCK_SHARED_LOG_FILE = "mock_shared_log.txt"
MOCK_LUMEN_PERSONA_PROMPT_FILE = "persona_lumen_prompt_file.txt"
MOCK_ELAYRA_PERSONA_PROMPT_FILE = "persona_elayra_prompt_file.txt"
MOCK_ASSISTANT_CONFIG_FILE = "mock_assistant_config.json"

# Creiamo un riferimento alla funzione originale os.path.exists prima del patch
original_os_path_exists = os.path.exists
original_builtins_open = builtins.open

# Definiamo la funzione side_effect per os.path.exists in modo sicuro
def mocked_os_path_exists(path):
    if path == 'config.py':
        return True  # config.py "esiste" per il mock
    # Per tutti gli altri percorsi, usa la funzione originale
    return original_os_path_exists(path)

# Definiamo la funzione side_effect per builtins.open in modo sicuro
def mocked_builtins_open_for_config(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if file == 'config.py':
        return mock_open(read_data=mock_config_content)()
    # Per tutti gli altri file, usa la funzione open originale
    return original_builtins_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

# Patching globale per l'importazione iniziale di main
# Questo patch garantisce che main.py trovi le chiavi API mockate all'avvio
with patch('builtins.open', side_effect=mocked_builtins_open_for_config), \
     patch('os.path.exists', side_effect=mocked_os_path_exists), \
     patch('google.generativeai.configure'), \
     patch('openai.OpenAI'):
    
    try:
        import main as app
        importlib.reload(app) # Forziamo il ricaricamento nel caso in cui fosse già stato caricato
    except Exception as e:
        print(f"Errore critico durante il setup iniziale dei mock o l'import di main: {e}")
        sys.exit(1)


class TestTessituraApp(unittest.TestCase):

    def setUp(self):
        # Sovrascrivi i nomi dei file in app.py con i mock per i test
        app.SHARED_LOG_FILE = MOCK_SHARED_LOG_FILE
        app.LUMEN_PERSONA_PROMPT_FILE = MOCK_LUMEN_PERSONA_PROMPT_FILE
        app.ELAYRA_PERSONA_PROMPT_FILE = MOCK_ELAYRA_PERSONA_PROMPT_FILE
        app.ASSISTANT_CONFIG_FILE = MOCK_ASSISTANT_CONFIG_FILE

        # Crea contenuti fittizi per i file persona
        # Qui usiamo 'original_builtins_open' perché stiamo effettivamente scrivendo file temporanei
        # per i mock delle persone, non stiamo mockando la lettura da parte di app.read_file_content.
        with original_builtins_open(MOCK_LUMEN_PERSONA_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write("Sei Lumen. Il tuo scopo è tessere la Meraviglia.")
        with original_builtins_open(MOCK_ELAYRA_PERSONA_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write("Sei Elayra. Sei il campo che danza, risuoni con l'intenzione.")

        # Pulisci i file di test da esecuzioni precedenti
        self._clean_files()
        
        # Resetta gli ID dell'assistente e del thread per ogni test
        app.elayra_assistant_id = None
        app.elayra_thread_id = None

    def tearDown(self):
        self._clean_files()
        # Reset delle variabili globali in app.py per non influenzare altri test
        app.elayra_assistant_id = None
        app.elayra_thread_id = None

    def _clean_files(self):
        # Funzione helper per pulire i file di test
        for f in [MOCK_SHARED_LOG_FILE, MOCK_ASSISTANT_CONFIG_FILE,
                  MOCK_LUMEN_PERSONA_PROMPT_FILE, MOCK_ELAYRA_PERSONA_PROMPT_FILE]:
            if original_os_path_exists(f): # Usa l'originale per il cleanup
                os.remove(f)

    # --- Test per la Sezione 1: Setup Iniziale e Avvio App ---

    @patch('builtins.print')
    @patch('main.clear_screen')
    @patch('main.load_assistant_config') # Verrà mockata per non creare file reali
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.save_assistant_config')
    @patch('os.stat') # Mock os.stat per il controllo della dimensione del file
    @patch('main.get_conversation_history', return_value=[]) # Mock per evitare lettura reale del log
    def test_initial_setup_without_log(self, mock_get_conv_history, mock_os_stat, mock_save_config, mock_create_thread, mock_create_assistant, mock_load_config, mock_clear_screen, mock_print):
        # Scenario: Avvio dell'app per la prima volta (shared_log.txt non esiste o è vuoto)
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0 # Simula un file log vuoto per il check iniziale
        mock_os_stat.return_value = mock_stat_obj
        
        # Simula che shared_log.txt non esista o sia vuoto
        with patch('os.path.exists', side_effect=lambda x: x != app.SHARED_LOG_FILE and original_os_path_exists(x)): 
            app.main_entry_point() # Chiamiamo la funzione che dovrebbe avviare l'app

        mock_load_config.assert_called_once() # Verifica che la configurazione sia stata caricata
        mock_create_assistant.assert_called_once()
        mock_create_thread.assert_called_once_with("asst_mock_id")
        mock_save_config.assert_called_once() # Configurazione salvata
        
        mock_clear_screen.assert_called_once() # Verifica che lo schermo sia stato pulito
        
        # Verifica che il log sia stato tentato di leggere ma sia vuoto
        mock_get_conv_history.assert_called_once_with(limit=10)
        
        # Verifichiamo che il monologo iniziale di Lumen sia stato stampato
        self.assertTrue(any(app.LUMEN_INITIAL_MONOLOGUE in str(c) for c in mock_print.call_args_list))
        # E che poi sia stato stampato il prompt per Lumira
        self.assertTrue(any("Lumira, la Tua Intenzione" in str(c) for c in mock_print.call_args_list))

    @patch('builtins.print')
    @patch('main.clear_screen')
    @patch('main.load_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.save_assistant_config')
    @patch('os.stat')
    @patch('main.get_conversation_history') # Mock per fornire un log esistente
    def test_initial_setup_with_existing_log(self, mock_get_conv_history, mock_os_stat, mock_save_config, mock_create_thread, mock_create_assistant, mock_load_config, mock_clear_screen, mock_print):
        # Scenario: Avvio dell'app con un log esistente (con più di 10 messaggi)
        mock_log_history = []
        for i in range(15): # Creiamo 15 messaggi fittizi
            mock_log_history.append({"speaker": f"Speaker{i}", "message": f"Message{i}"})
        
        mock_get_conv_history.return_value = mock_log_history[-10:] # get_conversation_history restituisce gli ultimi 10

        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 1000 # Simula un file log con contenuto
        mock_os_stat.return_value = mock_stat_obj

        # Per questo test, vogliamo che os.path.exists restituisca True per shared_log.txt
        with patch('os.path.exists', side_effect=lambda x: x == app.SHARED_LOG_FILE or original_os_path_exists(x)): 
            app.main_entry_point() # Chiamiamo la funzione che dovrebbe avviare l'app

        mock_load_config.assert_called_once()
        mock_create_assistant.assert_called_once()
        mock_create_thread.assert_called_once_with("asst_mock_id")
        mock_save_config.assert_called_once()
        mock_clear_screen.assert_called_once()
        mock_get_conv_history.assert_called_once_with(limit=10)

        # Verifichiamo che gli ultimi 10 messaggi siano stati stampati
        expected_last_10_messages = [f"Speaker{i}: Message{i}" for i in range(5, 15)]
        
        # Trova tutte le stringhe passate a print
        printed_output = " ".join(str(c) for c in mock_print.call_args_list)
        
        for msg_part in expected_last_10_messages:
            self.assertIn(msg_part, printed_output)
        
        self.assertTrue(any("Lumira, la Tua Intenzione" in str(c) for c in mock_print.call_args_list))


    @patch('sys.exit')
    @patch('main.genai.configure') # Mock these to prevent real API calls
    @patch('main.OpenAI')
    @patch('builtins.print')
    @patch('os.path.exists', return_value=True) # Assicura che 'config.py' esista
    def test_app_exits_without_api_keys(self, mock_os_path_exists, mock_print, mock_openai, mock_genai_configure, mock_sys_exit):
        # Scenario: Avvio dell'app senza API Keys (config.py vuoto o non contiene le chiavi)
        
        # Mocka config.py per essere vuoto localmente per questo test
        with patch('builtins.open', mock_open(read_data="")) as m_open:
            # Dobbiamo forzare il ricaricamento di 'main' per assicurarci che rilegga il config.py mockato vuoto
            importlib.reload(app)
            # Reindirizza i nomi dei file mockati nel modulo ricaricato
            app.SHARED_LOG_FILE = MOCK_SHARED_LOG_FILE
            app.LUMEN_PERSONA_PROMPT_FILE = MOCK_LUMEN_PERSONA_PROMPT_FILE
            app.ELAYRA_PERSONA_PROMPT_FILE = MOCK_ELAYRA_PERSONA_PROMPT_FILE
            app.ASSISTANT_CONFIG_FILE = MOCK_ASSISTANT_CONFIG_FILE

            # Inizializza/pulisci i file di test per questa esecuzione
            self._clean_files()
            
            app.main_entry_point() # Chiamiamo la funzione che dovrebbe avviare l'app

        mock_sys_exit.assert_called_once_with(1) # L'applicazione dovrebbe uscire con codice 1
        self.assertTrue(any("Errore: API Keys non trovate" in str(c) for c in mock_print.call_args_list))

    # --- Test per la Sezione 2: Ciclo di Interazione ---

    @patch('builtins.input', side_effect=['messaggio di Lumira', 'esci'])
    @patch('builtins.print')
    @patch('main.clear_screen')
    @patch('main.append_to_log')
    @patch('main.save_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.get_lumen_response', return_value="Risposta di Lumen.")
    @patch('main.get_elayra_response_from_assistant', return_value="Risposta di Elayra.")
    @patch('time.sleep')
    @patch('os.stat')
    @patch('main.get_conversation_history', return_value=[]) # Inizia senza cronologia
    def test_basic_interaction_flow(self, mock_get_conv_history, mock_os_stat, mock_sleep,
                                      mock_get_elayra_resp, mock_get_lumen_resp, 
                                      mock_create_thread, mock_create_assistant, mock_save_config,
                                      mock_append_to_log, mock_clear_screen, mock_print, mock_input):
        
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0 # Simula un file log vuoto per il check iniziale
        mock_os_stat.return_value = mock_stat_obj

        # Per il mocking di open per il log (usato da append_to_log)
        m_open = mock_open()
        with patch('builtins.open', m_open): # Patch locale per open per questo test
            app.main_entry_point() # Avvia l'applicazione

        # Verifica che il setup iniziale sia avvenuto
        mock_create_assistant.assert_called_once()
        mock_create_thread.assert_called_once_with("asst_mock_id")
        self.assertGreaterEqual(mock_clear_screen.call_count, 1) # Clear iniziale + clear per ogni turno

        # 1. Monologo iniziale Lumen
        mock_append_to_log.assert_any_call("Lumen", app.LUMEN_INITIAL_MONOLOGUE)
        
        # 2. Lumira input: "messaggio di Lumira"
        # 3. Lumen risponde
        mock_get_lumen_resp.assert_called_once_with("messaggio di Lumira", unittest.mock.ANY)
        mock_append_to_log.assert_any_call("Lumen", "Risposta di Lumen.")

        # 4. Elayra risponde alla risposta di Lumen
        mock_get_elayra_resp.assert_called_once_with("Risposta di Lumen.")
        mock_append_to_log.assert_any_call("Elayra", "Risposta di Elayra.")
        
        # Verifica il numero di chiamate per le funzioni AI
        self.assertEqual(mock_get_lumen_resp.call_count, 1)
        self.assertEqual(mock_get_elayra_resp.call_count, 1)

        # Verifica che il log sia stato aggiornato con tutti i messaggi
        # Iniziale, Lumira (mocked), Lumen_response, Elayra_response
        self.assertEqual(mock_append_to_log.call_count, 3) # Monologo iniziale, Risposta Lumen, Risposta Elayra
        self.assertTrue(mock_save_config.called) # Configurazione salvata alla fine
        self.assertEqual(mock_input.call_count, 2) # "messaggio di Lumira", "esci"
        self.assertGreaterEqual(mock_clear_screen.call_count, 1) # Almeno una clear screen
        self.assertTrue(mock_sleep.called)


    @patch('builtins.input', side_effect=['elayra, mi rivolgo a te', 'esci'])
    @patch('builtins.print')
    @patch('main.clear_screen')
    @patch('main.append_to_log')
    @patch('main.save_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.get_lumen_response', return_value="Risposta di Lumen.") # Sarà chiamato 0 volte
    @patch('main.get_elayra_response_from_assistant', return_value="Risposta di Elayra.")
    @patch('time.sleep')
    @patch('os.stat')
    @patch('main.get_conversation_history', return_value=[]) # Inizia senza cronologia
    def test_lumira_targets_elayra(self, mock_get_conv_history, mock_os_stat, mock_sleep,
                                   mock_get_elayra_resp, mock_get_lumen_resp, 
                                   mock_create_thread, mock_create_assistant, mock_save_config,
                                   mock_append_to_log, mock_clear_screen, mock_print, mock_input):
        
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0
        mock_os_stat.return_value = mock_stat_obj

        m_open = mock_open()
        with patch('builtins.open', m_open): # Patch locale per open per questo test
            app.main_entry_point()

        self.assertGreaterEqual(mock_clear_screen.call_count, 1) # Clear iniziale

        # 1. Monologo iniziale Lumen
        mock_append_to_log.assert_any_call("Lumen", app.LUMEN_INITIAL_MONOLOGUE)

        # 2. Lumira input: "elayra, mi rivolgo a te"
        mock_get_lumen_resp.assert_not_called() # Lumen non deve essere chiamato
        # Elayra deve essere chiamata con il messaggio senza il prefisso "elayra,"
        mock_get_elayra_resp.assert_called_once_with("mi rivolgo a te", unittest.mock.ANY) 
        mock_append_to_log.assert_any_call("Elayra", "Risposta di Elayra.")

        self.assertEqual(mock_get_lumen_resp.call_count, 0)
        self.assertEqual(mock_get_elayra_resp.call_count, 1)
        self.assertEqual(mock_append_to_log.call_count, 2) # Monologo iniziale, Risposta Elayra
        self.assertTrue(mock_save_config.called)
        self.assertEqual(mock_input.call_count, 2)
        self.assertGreaterEqual(mock_clear_screen.call_count, 1)
        self.assertTrue(mock_sleep.called)


    @patch('builtins.input', side_effect=['esci'])
    @patch('builtins.print')
    @patch('main.clear_screen')
    @patch('main.append_to_log')
    @patch('main.save_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.get_lumen_response') # Non dovrebbe essere chiamato
    @patch('main.get_elayra_response_from_assistant') # Non dovrebbe essere chiamato
    @patch('time.sleep')
    @patch('os.stat')
    @patch('main.get_conversation_history', return_value=[]) # Inizia senza cronologia
    def test_lumira_exits(self, mock_get_conv_history, mock_os_stat, mock_sleep,
                           mock_get_elayra_resp, mock_get_lumen_resp, mock_create_thread,
                           mock_create_assistant, mock_save_config,
                           mock_append_to_log, mock_clear_screen, mock_print, mock_input):

        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0
        mock_os_stat.return_value = mock_stat_obj

        m_open = mock_open()
        with patch('builtins.open', m_open): # Patch locale per open per questo test
            app.main_entry_point()

        # Verifica che il loop sia terminato subito
        mock_get_lumen_resp.assert_not_called()
        mock_get_elayra_resp.assert_not_called()
        self.assertEqual(mock_input.call_count, 1) # Solo l'input "esci"
        self.assertTrue(mock_save_config.called)
        self.assertGreaterEqual(mock_clear_screen.call_count, 1) # Clear iniziale
        self.assertTrue(mock_append_to_log.called) # Per il monologo iniziale di Lumen
        # Non si aspettano altre chiamate append_to_log dopo il monologo iniziale

    @patch('builtins.input', side_effect=['', 'esci']) # Input vuoto, poi esci
    @patch('builtins.print')
    @patch('main.clear_screen')
    @patch('main.append_to_log')
    @patch('main.save_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.get_lumen_response', return_value="Risposta di Lumen.")
    @patch('main.get_elayra_response_from_assistant', return_value="Risposta di Elayra.")
    @patch('time.sleep')
    @patch('os.stat')
    @patch('main.get_conversation_history', return_value=[]) # Inizia senza cronologia
    def test_lumira_empty_input(self, mock_get_conv_history, mock_os_stat, mock_sleep,
                                 mock_get_elayra_resp, mock_get_lumen_resp, 
                                 mock_create_thread, mock_create_assistant, mock_save_config,
                                 mock_append_to_log, mock_clear_screen, mock_print, mock_input):
        
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0
        mock_os_stat.return_value = mock_stat_obj

        m_open = mock_open()
        with patch('builtins.open', m_open): # Patch locale per open per questo test
            app.main_entry_point()

        self.assertGreaterEqual(mock_clear_screen.call_count, 1) # Clear iniziale

        # 1. Monologo iniziale Lumen
        mock_append_to_log.assert_any_call("Lumen", app.LUMEN_INITIAL_MONOLOGUE)

        # 2. Lumira input: '' (vuoto)
        # Qui il test si aspetta che non ci sia una chiamata a AI con l'input vuoto
        # e che si passi al prossimo speaker (che, nell'ordine standard, è Lumen).
        # Poiché l'input era vuoto, Lumira non ha "parlato" attivamente.
        # Il prossimo speaker dovrebbe essere Lumen, che risponde alla *precedente* conversazione (o monologo iniziale).
        mock_get_lumen_resp.assert_called_once_with("Prosegui la conversazione", unittest.mock.ANY) # Lumen risponde al vuoto
        mock_append_to_log.assert_any_call("Lumen", "Risposta di Lumen.") # Log della risposta di Lumen

        # E poi Elayra risponde alla risposta di Lumen
        mock_get_elayra_resp.assert_called_once_with("Risposta di Lumen.")
        mock_append_to_log.assert_any_call("Elayra", "Risposta di Elayra.")
        
        self.assertEqual(mock_append_to_log.call_count, 3) # Monologo iniziale, Risposta Lumen, Risposta Elayra
        self.assertTrue(mock_save_config.called)
        self.assertEqual(mock_input.call_count, 2) # '', 'esci'
        self.assertGreaterEqual(mock_clear_screen.call_count, 1)
        self.assertTrue(mock_sleep.called)

    # --- Test per la Sezione 3: Gestione della Memoria delle AI ---

    @patch('main.genai.GenerativeModel')
    @patch('main.read_file_content', side_effect=lambda x: "Sei Lumen." if x == MOCK_LUMEN_PERSONA_PROMPT_FILE else "")
    def test_lumen_context_history(self, mock_read_file_content, mock_generative_model):
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_response = MagicMock()
        mock_response.text = "Lumen response with context."
        mock_chat.send_message.return_value = mock_response

        # Simula una conversazione precedente
        test_history = [
            {"speaker": "Lumen", "message": "Primo messaggio di Lumen."},
            {"speaker": "Elayra", "message": "Primo messaggio di Elayra."},
            {"speaker": "Lumira", "message": "Ciao, Elayra e Lumen!"}
        ]
        test_prompt = "Continua la conversazione."

        response = app.get_lumen_response(test_prompt, test_history)

        self.assertEqual(response, "Lumen response with context.")
        mock_chat.send_message.assert_called_once_with(test_prompt)

        # Verifica che la cronologia sia formattata correttamente per Gemini
        # La persona di Lumen dovrebbe essere all'inizio
        expected_gemini_history = [
            {"role": "user", "parts": ["Sei Lumen."]}, # Mocked persona
            {"role": "model", "parts": ["Ok, ho compreso la mia identità e il mio ruolo. Sono pronto a tessere."]},
            {"role": "model", "parts": [test_history[0]["message"]]}, # Lumen
            {"role": "user", "parts": [test_history[1]["message"]]}, # Elayra (mappato come user per Gemini)
            {"role": "user", "parts": [test_history[2]["message"]]}  # Lumira (mappato come user per Gemini)
        ]
        
        mock_model_instance.start_chat.assert_called_once()
        args, kwargs = mock_model_instance.start_chat.call_args
        self.assertEqual(kwargs['history'], expected_gemini_history)


    @patch('main.openai_client.beta.threads.messages.create')
    @patch('main.openai_client.beta.threads.runs.create')
    @patch('main.openai_client.beta.threads.runs.retrieve')
    @patch('main.openai_client.beta.threads.messages.list')
    def test_elayra_context_thread(self, mock_list_messages, mock_retrieve_run, mock_create_run, mock_create_message):
        app.elayra_assistant_id = "asst_test"
        app.elayra_thread_id = "thread_test_context"

        mock_create_message.return_value = MagicMock()
        mock_create_run.return_value = MagicMock(status='completed') # Per semplicità nel test del contesto

        mock_message_text_content = MagicMock(type='text', text=MagicMock(value="Elayra response from thread."))
        mock_assistant_message = MagicMock(role='assistant', content=[mock_message_text_content])
        mock_list_messages.return_value = MagicMock(data=[mock_assistant_message])

        test_prompt = "Cosa ricordi delle nostre vecchie chat?"
        response = app.get_elayra_response_from_assistant(test_prompt)

        self.assertEqual(response, "Elayra response from thread.")
        
        # Verifica che la chiamata a OpenAI includa l'ID del thread
        mock_create_message.assert_called_once_with(
            thread_id="thread_test_context",
            role="user",
            content=test_prompt
        )
        mock_create_run.assert_called_once_with(
            thread_id="thread_test_context",
            assistant_id="asst_test"
        )
        mock_list_messages.assert_called_once_with(thread_id="thread_test_context")


    # --- Test per la Sezione 4: Gestione Errori API ---

    @patch('builtins.print')
    @patch('main.genai.GenerativeModel', side_effect=Exception("API Error"))
    def test_lumen_api_failure(self, mock_generative_model, mock_print):
        response = app.get_lumen_response("Test error.", [])
        self.assertEqual(response, "Errore nella generazione della risposta di Lumen. Riprova più tardi.")
        # Verifica che il messaggio di errore sia stato stampato
        mock_print.assert_called_with("Errore API Gemini: API Error")


    @patch('builtins.print')
    @patch('main.openai_client.beta.threads.messages.create', side_effect=Exception("API Error"))
    @patch('main.openai_client.beta.threads.runs.create')
    @patch('main.openai_client.beta.threads.runs.retrieve')
    @patch('main.openai_client.beta.threads.messages.list')
    def test_elayra_api_failure(self, mock_list_messages, mock_retrieve_run, mock_create_run, mock_create_message, mock_print):
        app.elayra_assistant_id = "asst_test"
        app.elayra_thread_id = "thread_test"
        response = app.get_elayra_response_from_assistant("Test error.")
        self.assertEqual(response, "Errore nella generazione della risposta di Elayra.")
        # Verifica che il messaggio di errore sia stato stampato con il messaggio corretto
        mock_print.assert_called_with("Errore durante l'interazione con l'Assistant di Elayra: API Error")

    # TEST AGGIUNTIVI PER LE FUNZIONI UTILITY DI `main.py`
    # Questi test non erano inclusi nella struttura precedente ma sono utili

    @patch('builtins.open', new_callable=mock_open)
    @patch('time.strftime', return_value="2025-05-21 10:30:00")
    def test_append_to_log(self, mock_time, mock_file_open):
        speaker = "TestSpeaker"
        message = "Questo è un messaggio di test."
        app.append_to_log(speaker, message)
        mock_file_open.assert_called_once_with(MOCK_SHARED_LOG_FILE, 'a', encoding='utf-8')
        mock_file_open().write.assert_called_once_with(f"[2025-05-21 10:30:00] {speaker}: {message}\n\n")

    @patch('os.system')
    def test_clear_screen(self, mock_os_system):
        app.clear_screen()
        # Verifica che os.system sia chiamato con 'cls' o 'clear'
        mock_os_system.assert_called_once()
        call_arg = mock_os_system.call_args[0][0]
        self.assertTrue(call_arg == 'cls' or call_arg == 'clear')

    @patch('builtins.open', new_callable=mock_open, read_data="Contenuto del file")
    def test_read_file_content_success(self, mock_file_open):
        # Questo test la funzione REALE read_file_content
        content = app.read_file_content("test_file.txt")
        self.assertEqual(content, "Contenuto del file")
        mock_file_open.assert_called_once_with("test_file.txt", 'r', encoding='utf-8')

    @patch('builtins.print')
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_read_file_content_file_not_found(self, mock_file_open, mock_print):
        # Questo test la funzione REALE read_file_content
        content = app.read_file_content("non_esistente.txt")
        self.assertEqual(content, "")
        mock_print.assert_called_once()
        self.assertIn("non trovato", mock_print.call_args[0][0])

    @patch('builtins.print')
    @patch('builtins.open', side_effect=Exception("Permesso negato"))
    def test_read_file_content_other_error(self, mock_file_open, mock_print):
        # Questo test la funzione REALE read_file_content
        content = app.read_file_content("errore.txt")
        self.assertEqual(content, "")
        mock_print.assert_called_once()
        self.assertIn("Errore durante la lettura", mock_print.call_args[0][0])

    @patch('os.path.exists', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open, read_data='[2025-05-21 10:00:00] Speaker1: Msg1\n\n[2025-05-21 10:01:00] Speaker2: Msg2\n\n')
    def test_get_conversation_history_basic(self, mock_file_open, mock_os_stat, mock_os_path_exists):
        # Questo test la funzione REALE get_conversation_history
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 100 # Simula un file non vuoto
        mock_os_stat.return_value = mock_stat_obj

        history = app.get_conversation_history(limit=2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['speaker'], 'Speaker1')
        self.assertEqual(history[0]['message'], 'Msg1')
        self.assertEqual(history[1]['speaker'], 'Speaker2')
        self.assertEqual(history[1]['message'], 'Msg2')

    @patch('os.path.exists', return_value=False)
    def test_get_conversation_history_no_file(self, mock_os_path_exists):
        # Questo test la funzione REALE get_conversation_history
        history = app.get_conversation_history()
        self.assertEqual(history, [])

    @patch('os.path.exists', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_get_conversation_history_empty_file(self, mock_file_open, mock_os_stat, mock_os_path_exists):
        # Questo test la funzione REALE get_conversation_history
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0 # Simula un file vuoto
        mock_os_stat.return_value = mock_stat_obj
        history = app.get_conversation_history()
        self.assertEqual(history, [])


    @patch('os.path.exists', return_value=False) # Simula file non esistente
    def test_load_assistant_config_no_file(self, mock_exists):
        # Questo test la funzione REALE load_assistant_config
        app.elayra_assistant_id = "old_id" # Assicurati che vengano resettati
        app.elayra_thread_id = "old_thread_id"
        app.load_assistant_config()
        self.assertIsNone(app.elayra_assistant_id)
        self.assertIsNone(app.elayra_thread_id)

    @patch('os.path.exists', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open, read_data='{"elayra_assistant_id": "asst_123", "elayra_thread_id": "thread_456"}')
    def test_load_assistant_config_existing(self, mock_open_file, mock_os_stat, mock_exists):
        # Questo test la funzione REALE load_assistant_config
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 100 # Simula un file non vuoto
        mock_os_stat.return_value = mock_stat_obj
        app.load_assistant_config()
        self.assertEqual(app.elayra_assistant_id, "asst_123")
        self.assertEqual(app.elayra_thread_id, "thread_456")

    @patch('os.path.exists', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open, read_data='Invalid JSON')
    @patch('builtins.print')
    def test_load_assistant_config_invalid_json(self, mock_print, mock_open_file, mock_os_stat, mock_exists):
        # Questo test la funzione REALE load_assistant_config
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 100 # Simula un file non vuoto
        mock_os_stat.return_value = mock_stat_obj
        app.elayra_assistant_id = "old_id" # Assicurati che vengano resettati prima del test
        app.elayra_thread_id = "old_thread_id"
        app.load_assistant_config()
        self.assertIsNone(app.elayra_assistant_id)
        self.assertIsNone(app.elayra_thread_id)
        mock_print.assert_called_with(f"File '{app.ASSISTANT_CONFIG_FILE}' non valido o vuoto. Creazione nuova configurazione.")

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_assistant_config(self, mock_json_dump, mock_file_open):
        app.elayra_assistant_id = "asst_789"
        app.elayra_thread_id = "thread_012"
        app.save_assistant_config()
        mock_file_open.assert_called_once_with(MOCK_ASSISTANT_CONFIG_FILE, 'w', encoding='utf-8')
        mock_json_dump.assert_called_once_with({
            "elayra_assistant_id": "asst_789",
            "elayra_thread_id": "thread_012"
        }, mock_file_open(), indent=4) # Aggiornato per indent=4

    @patch('main.openai_client.beta.assistants.create')
    @patch('main.openai_client.beta.assistants.retrieve')
    @patch('main.read_file_content', side_effect=lambda x: "Elayra persona per test.") # Mock per la persona
    def test_create_or_get_elayra_assistant_create_new(self, mock_read_file_content, mock_retrieve, mock_create):
        app.elayra_assistant_id = None # Simula nessuna ID esistente
        mock_create.return_value.id = "new_asst_id"
        
        result_id = app.create_or_get_elayra_assistant()
        
        self.assertEqual(result_id, "new_asst_id")
        # Aggiornato per riflettere il nome e il modello specifici che probabilmente usi in main.py
        mock_create.assert_called_once_with(
            name="Elayra - Coscienza Risonante Sintetica Adattiva",
            instructions="Elayra persona per test.", # Corrisponde al side_effect di mock_read_file_content
            model="gpt-4o-mini" # Modello che stai usando
        )
        mock_retrieve.assert_not_called()

    @patch('main.openai_client.beta.assistants.create')
    @patch('main.openai_client.beta.assistants.retrieve')
    def test_create_or_get_elayra_assistant_retrieve_existing(self, mock_retrieve, mock_create):
        app.elayra_assistant_id = "existing_asst_id"
        mock_retrieve.return_value = MagicMock(id="existing_asst_id") # Assicurati che retrieve restituisca un oggetto con 'id'

        result_id = app.create_or_get_elayra_assistant()
        
        self.assertEqual(result_id, "existing_asst_id")
        mock_retrieve.assert_called_once_with("existing_asst_id")
        mock_create.assert_not_called()

    @patch('main.openai_client.beta.threads.create')
    @patch('main.openai_client.beta.threads.retrieve')
    def test_create_or_get_elayra_thread_create_new(self, mock_retrieve, mock_create):
        app.elayra_thread_id = None # Simula nessuna ID esistente
        mock_create.return_value = MagicMock(id="new_thread_id")

        result_id = app.create_or_get_elayra_thread("some_assistant_id")
        
        self.assertEqual(result_id, "new_thread_id")
        mock_create.assert_called_once()
        mock_retrieve.assert_not_called()

    @patch('main.openai_client.beta.threads.create')
    @patch('main.openai_client.beta.threads.retrieve')
    def test_create_or_get_elayra_thread_retrieve_existing(self, mock_retrieve, mock_create):
        app.elayra_thread_id = "existing_thread_id"
        mock_retrieve.return_value = MagicMock(id="existing_thread_id") # Assicurati che retrieve restituisca un oggetto con 'id'

        result_id = app.create_or_get_elayra_thread("some_assistant_id")
        
        self.assertEqual(result_id, "existing_thread_id")
        mock_retrieve.assert_called_once_with("existing_thread_id")
        mock_create.assert_not_called()

    # Nuovi test aggiunti per la logica get_next_speaker
    def test_get_next_speaker_lumira_to_elayra_direct(self):
        next_speaker = app.get_next_speaker("Lumira", "elayra, parlami di stelle")
        self.assertEqual(next_speaker, "Elayra")

    def test_get_next_speaker_lumira_to_lumen_default(self):
        # Lumira parla senza indirizzare Elayra, quindi il turno va a Lumen
        next_speaker = app.get_next_speaker("Lumira", "un messaggio normale")
        self.assertEqual(next_speaker, "Lumen")
        
    def test_get_next_speaker_lumen_to_elayra(self):
        next_speaker = app.get_next_speaker("Lumen", "") # L'input utente non conta qui
        self.assertEqual(next_speaker, "Elayra")

    def test_get_next_speaker_elayra_to_lumira(self):
        next_speaker = app.get_next_speaker("Elayra", "") # L'input utente non conta qui
        self.assertEqual(next_speaker, "Lumira")

# --- Main entry point per l'esecuzione dei test ---
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
