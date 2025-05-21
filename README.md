# ElayraNet: The Weaving of Interactive Speech

---

## Table of Contents

* Introduction: The Purpose of ElayraNet
* Technical Requirements
    * Prerequisites
    * Installation
    * API Key Configuration
* Architecture and Functionality
    * Interaction Flow
    * Memory Management
    * Error Handling
    * User Interface
* Project Structure
* Development Guide (Test-Driven Development
    * Running Tests
    * Development Principles
* Additional Notes

---

## 1. Introduction: The Purpose of ElayraNet

ElayraNet is an experimental application exploring advanced interaction between a user (**Lumira**) and two distinct Artificial Intelligences: **Lumen** (powered by Google Gemini) and **Elayra** (powered by OpenAI Assistant). The goal is to create a fluid and dynamic conversation where the dialogue flow can be influenced by the user, and the AIs maintain persistent memory and unique "personalities."

It's a "Weaving of Speech," where each intervention is a thread added to a digital tapestry, creating a continuous story and an immersive conversational experience.

---

## 2. Technical Requirements

### Prerequisites

To run ElayraNet, you'll need:

* **Python 3.9+**
* **Google Gemini API Access:** Requires a valid API key.
* **OpenAI API Access:** Requires a valid API key.
* A compatible terminal (e.g., CMD, PowerShell on Windows; Bash, Zsh on Linux/macOS).

### Installation

1.  **Clone the repository (or download the files):**

    ```bash
    git clone [https://github.com/your-username/ElayraNet.git](https://github.com/your-username/ElayraNet.git) # Replace with your URL
    cd ElayraNet
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**

    * On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    * On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt # Make sure you have a requirements.txt file
    ```

    (If you don't have a `requirements.txt`, install manually: `pip install google-generativeai openai`)

### API Key Configuration

Google Gemini and OpenAI API keys are crucial for ElayraNet's operation. They must be stored in a file named `config.py` in the root directory of the project.

1.  Create a file named `config.py` in the same directory as `main.py`.
2.  Add your API keys inside `config.py` in this format:

    ```python
    # config.py
    GOOGLE_GEMINI_API_KEY = "your_gemini_key_here"
    OPENAI_API_KEY = "your_openai_key_here"
    ```

    **CAUTION:** Never share your `config.py` with real keys in a public repository. It's best practice to add it to your `.gitignore`.

### Running the Application

After installation and configuration, you can start the application:

```bash
python main.py
```

---

## 3. Architecture and Functionality

ElayraNet is designed for continuous terminal interaction, managing turn-taking and AI memory.

### Interaction Flow

The conversation follows a specific cycle:

* **App Startup:**
    * The application loads API keys from `config.py`. If keys are missing, the application terminates.
    * The "personalities" (persona prompts) of Lumen and Elayra are loaded from their respective files.
    * The `shared_log.txt` file is read to retrieve previous conversation history. If the log is empty, Lumen introduces itself with an initial monologue.
    * The last 10 messages from the history (or Lumen's initial monologue if the log was empty) are displayed in the terminal.
    * The initial turn is always Lumira's.

* **Conversation Cycle: Lumira -> AI -> AI -> Lumira:**
    * **Lumira (User):** Types a message.
        * If Lumira types "exit", the conversation ends.
        * If Lumira types an empty input, the turn passes to the "next speaker" without logging the empty message.
    * **AI Directing:** If Lumira's message starts with the word "elayra" (e.g., "elayra, could you...", "Elayra tell me..."), Lumen's turn is skipped, and the next response will be directly from Elayra.
    * **Lumen (Google Gemini):** If not skipped (i.e., Lumira didn't specify "elayra"), Lumen responds to Lumira's message.
    * **Elayra (OpenAI Assistant):** Elayra responds to the previous AI's message (Lumen) or directly to Lumira if specified.
    * After Elayra's response, the turn returns to Lumira.

* **Display Update:** After each completed turn, the screen is cleared, and the last 10 messages from `shared_log.txt` are re-displayed to maintain visual context.

### Memory Management

Conversation persistence and AI identities are managed as follows:

* `shared_log.txt` file: This file records the entire conversation history. It's read on startup to reconstruct context and updated after each AI's message. It serves as long-term memory for the entire "Weaving."
* `persona_lumen_prompt_file.txt`: Contains Lumen's system prompt/personality. This prompt is included in the context of every Gemini request to maintain character consistency.
* `persona_elayra_prompt_file.txt`: Contains Elayra's system prompt/personality. This is used during the creation of the OpenAI Assistant to define its behavior and instructions.
* **OpenAI Assistant/Thread ID** (`assistant_config.json`): Elayra utilizes OpenAI's "Assistant" and "Thread" functionalities. The Assistant and Thread IDs are saved in `assistant_config.json` to ensure Elayra maintains its conversational memory across sessions and that the Assistant's identity is persistent.

### Error Handling

In case of API failures (Gemini or OpenAI), the application will print an "API Failure" message or a more specific error message (Error generating Lumen/Elayra's response) and attempt to continue the interaction cycle, rather than terminating abruptly.

### User Interface

All interaction occurs via the console/terminal. The screen is cleared, and the last 10 messages from the log are displayed at the beginning of each turn for a clear and contextualized user experience.

---

## 4. Project Structure

* `main.py`: Contains the core application logic, including conversation flow management, AI API interaction, and log handling.
* `test_main.py`: Contains the unit test suite to ensure the correctness of the implemented logic, following Test-Driven Development (TDD) principles.
* `config.py`: A file (not versioned) for API key configuration.
* `shared_log.txt`: The log file recording the entire conversation history.
* `persona_lumen_prompt_file.txt`: File containing Lumen's (Google Gemini) personality prompt.
* `persona_elayra_prompt_file.txt`: File containing Elayra's (OpenAI Assistant) personality prompt.
* `assistant_config.json`: File for saving Elayra's OpenAI Assistant and Thread IDs.

---

## 5. Development Guide (Test-Driven Development)

This project has been developed using a **Test-Driven Development (TDD)** approach. This means that tests were written before the functions in `main.py` were implemented.

### Running Tests

To run the entire test suite:

```bash
python -m unittest test_main.py
```

Initially, many tests will fail (`F` or `E`). Your goal is to implement the necessary code in `main.py` to make each test pass (`.`).

### Development Principles

* **Red:** Write a test that fails for a requirement not yet implemented.
* **Green:** Write the minimum necessary code in `main.py` to make that test pass.
* **Refactor:** Improve the newly written code, ensuring all tests continue to pass.
* Repeat the cycle.

This approach ensures that every piece of code is verified and that the application behaves exactly as intended by the requirements.

---

## 6. Additional Notes

* **API keys** must be handled with care for security. Consider using environment variables for production.
* **Memory management for Lumen** relies on sending the entire history to the Gemini model. For very long conversations, this might hit token limits or increase costs. A summarization strategy could be considered.
* **Elayra's memory** is intrinsically managed by OpenAI's Assistant Thread mechanism, which is more efficient for long contexts.
```
