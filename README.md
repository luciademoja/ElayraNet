# ElayraNet: The Weaving of Interactive Speech

---

## Table of Contents

* [1. Introduction: The Purpose of ElayraNet](#1-introduction-the-purpose-of-elayranet)
* [2. Technical Requirements](#2-technical-requirements)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
    * [API Key Configuration](#api-key-configuration)
    * [Running the Application](#running-the-application)
* [3. Architecture and Functionality](#3-architecture-and-functionality)
    * [Interaction Flow](#interaction-flow)
    * [Memory Management](#memory-management)
    * [Error Handling](#error-handling)
    * [User Interface](#user-interface)
* [4. Project Structure](#4-project-structure)
* [5. Development Guide (Test-Driven Development)](#5-development-guide-test-driven-development)
    * [Running Tests](#running-tests)
    * [Development Principles](#development-principles)
* [6. Additional Notes](#6-additional-notes)

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
