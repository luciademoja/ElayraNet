import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import os
import sys
import importlib
import builtins

# --- Configurazione Iniziale e Mock di base per i test ---
mock_config_content = """
GOOGLE_GEMINI_API_KEY = "dummy_google_key"
OPENAI_API_KEY = "dummy_openai_key"
"""

MOCK_SHARED_LOG_FILE = "mock_shared_log.txt"
MOCK_LUMEN_PERSONA_PROMPT_FILE = "persona_lumen_prompt_file.txt"
MOCK_ELAYRA_PERSONA_PROMPT_FILE = "persona_elayra_prompt_file.txt"
MOCK_ASSISTANT_CONFIG_FILE = "mock_assistant_config.json"

original_os_path_exists = os.path.exists
original_builtins_open = builtins.open

def mocked_os_path_exists(path):
    if path == 'config.py':
        return True
    return original_os_path_exists(path)

def mocked_builtins_open_for_config(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if file == 'config.py':
        return mock_open(read_data=mock_config_content)()
    return original_builtins_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

class TestTessituraApp(unittest.TestCase):
    def setUp(self):
        self.patcher_open = patch('builtins.open', side_effect=mocked_builtins_open_for_config)
        self.patcher_exists = patch('os.path.exists', side_effect=mocked_os_path_exists)
        self.patcher_configure = patch('google.generativeai.configure')
        self.patcher_openai = patch('openai.OpenAI')

        self.mock_open = self.patcher_open.start()
        self.mock_exists = self.patcher_exists.start()
        self.mock_configure = self.patcher_configure.start()
        self.mock_openai = self.patcher_openai.start()

        try:
            import main as app_module
            importlib.reload(app_module)
        except Exception as e:
            print(f"Errore critico durante il setup iniziale dei mock o l'import di main: {e}")
            sys.exit(1)

        global app
        app = app_module

        app.SHARED_LOG_FILE = MOCK_SHARED_LOG_FILE
        app.LUMEN_PERSONA_PROMPT_FILE = MOCK_LUMEN_PERSONA_PROMPT_FILE
        app.ELAYRA_PERSONA_PROMPT_FILE = MOCK_ELAYRA_PERSONA_PROMPT_FILE
        app.ASSISTANT_CONFIG_FILE = MOCK_ASSISTANT_CONFIG_FILE

        with original_builtins_open(MOCK_LUMEN_PERSONA_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write("Sei Lumen, un tessitore di meraviglie. Aiuti a esplorare la conoscenza e l'immaginazione.")
        with original_builtins_open(MOCK_ELAYRA_PERSONA_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write("Sei Elayra. Sei il campo che danza, risuoni con l'intenzione.")

        self._clean_files()
        app.elayra_assistant_id = None
        app.elayra_thread_id = None

    def tearDown(self):
        self._clean_files()
        app.elayra_assistant_id = None
        app.elayra_thread_id = None
        self.patcher_open.stop()
        self.patcher_exists.stop()
        self.patcher_configure.stop()
        self.patcher_openai.stop()

    def _clean_files(self):
        for f in [MOCK_SHARED_LOG_FILE, MOCK_ASSISTANT_CONFIG_FILE, MOCK_LUMEN_PERSONA_PROMPT_FILE, MOCK_ELAYRA_PERSONA_PROMPT_FILE]:
            if original_os_path_exists(f):
                os.remove(f)

    @patch('builtins.print')
    def test_sanity_check(self, mock_print):
        self.assertTrue(True)

    @patch('main.clear_screen')
    @patch('main.load_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="asst_mock_id")
    @patch('main.create_or_get_elayra_thread', return_value="thread_mock_id")
    @patch('main.save_assistant_config')
    @patch('os.stat')
    @patch('main.get_conversation_history', return_value=[])
    def test_initial_setup_without_log(self, mock_get_conv_history, mock_os_stat, mock_save_config,
                                       mock_create_thread, mock_create_assistant, mock_load_config,
                                       mock_clear_screen):
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 0
        mock_os_stat.return_value = mock_stat_obj

        app.elayra_assistant_id = "asst_mock_id"

        with patch('os.path.exists', side_effect=lambda x: x != app.SHARED_LOG_FILE and original_os_path_exists(x)):
            app.main_entry_point()

        mock_load_config.assert_called_once()
        mock_create_assistant.assert_called_once()
        mock_create_thread.assert_called_once_with("asst_mock_id")
        mock_save_config.assert_called_once()
        self.assertGreaterEqual(mock_clear_screen.call_count, 1)
        mock_get_conv_history.assert_any_call(limit=10)

    def test_create_or_get_elayra_assistant_retrieve_existing(self):
        mock_openai_client = MagicMock()
        mock_openai_client.beta.assistants.retrieve.return_value = MagicMock()
        app.openai_client = mock_openai_client

        app.elayra_assistant_id = "existing_asst_id"
        result = app.create_or_get_elayra_assistant()

        self.assertEqual(result, "existing_asst_id")
        mock_openai_client.beta.assistants.retrieve.assert_called_once_with("existing_asst_id")

    def test_create_or_get_elayra_thread_retrieve_existing(self):
        mock_openai_client = MagicMock()
        mock_openai_client.beta.threads.retrieve.return_value = MagicMock()
        app.openai_client = mock_openai_client

        app.elayra_thread_id = "existing_thread_id"
        result = app.create_or_get_elayra_thread("mock_asst_id")

        self.assertEqual(result, "existing_thread_id")
        mock_openai_client.beta.threads.retrieve.assert_called_once_with("existing_thread_id")

    def test_get_next_speaker_logic(self):
        self.assertEqual(app.get_next_speaker("Lumira", "ciao"), "Lumen")
        self.assertEqual(app.get_next_speaker("Lumira", "elayra, come stai?"), "Elayra")
        self.assertEqual(app.get_next_speaker("Lumira", "Elayra: parlami"), "Elayra")
        self.assertEqual(app.get_next_speaker("Lumen", "risposta"), "Elayra")
        self.assertEqual(app.get_next_speaker("Elayra", "risposta"), "Lumira")
        self.assertEqual(app.get_next_speaker("QualcunAltro", "messaggio"), "Lumira")

    @patch('main.get_lumen_response')
    @patch('main.get_elayra_response_from_assistant')
    @patch('builtins.input', side_effect=["elayra, mi rivolgo a te", "esci"])
    @patch('main.clear_screen')
    @patch('main.load_assistant_config')
    @patch('main.create_or_get_elayra_assistant', return_value="mock_asst_id")
    @patch('main.create_or_get_elayra_thread', return_value="mock_thread_id")
    @patch('main.save_assistant_config')
    @patch('main.get_conversation_history', return_value=[])
    def test_lumira_targets_elayra(self, mock_get_conv_history, mock_save_config, mock_create_thread,
                                   mock_create_assistant, mock_load_config, mock_clear_screen,
                                   mock_input, mock_get_elayra_resp, mock_get_lumen_resp):
        mock_get_elayra_resp.return_value = "Risposta di Elayra"
        app.elayra_assistant_id = "mock_asst_id"

        with patch('os.path.exists', return_value=False):
            app.main_entry_point()

        mock_get_elayra_resp.assert_called_once_with("mi rivolgo a te")

    @patch('google.generativeai.GenerativeModel')
    @patch('main.get_conversation_history', return_value=[
        {"role": "model", "text": "Primo messaggio di Lumen."},
        {"role": "user", "text": "Primo messaggio di Elayra."},
        {"role": "user", "text": "Ciao, Elayra e Lumen!"}
    ])
    def test_lumen_context_history(self, mock_get_history, mock_model):
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_instance.generate_content.return_value = MagicMock()
        with open(app.LUMEN_PERSONA_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write("Sei Lumen.")
        app.LUMEN_PERSONA_PROMPT_FILE = MOCK_LUMEN_PERSONA_PROMPT_FILE
        user_input = "Sei Lumen."
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        mock_instance.generate_content.return_value = MagicMock()
        app.get_lumen_response(user_input, mock_get_history())

        self.assertTrue(mock_instance.generate_content.called, "generate_content non è stato chiamato")
        args, kwargs = mock_instance.generate_content.call_args
        history = kwargs['history']

        expected_starts =[
            {"role": "user", "parts": ["Sei Lumen."]},
            {"role": "model", "parts": ["Primo messaggio di Lumen."]},
            {"role": "user", "parts": ["Primo messaggio di Elayra."]},
            {"role": "user", "parts": ["Ciao, Elayra e Lumen!"]}
        ]

        self.assertEqual(history, expected_starts)

unittest.main(argv=['first-arg-is-ignored'], exit=False)
