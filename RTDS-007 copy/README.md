# Gemini-Powered OpenStack AI Agent

An AI-driven assistant that enables **natural language control** of your **OpenStack infrastructure** using **Google Gemini**. This project empowers developers and cloud admins to interact with OpenStack through conversational commands, reducing the complexity of direct API or CLI usage.

# [Demo](https://drive.google.com/drive/folders/1-i7_EgWivs9o_x47rCEhc3jaIqW0Yeuh?usp=drive_link)


# Project Structure

```bash
AIML-007/
├── apis/
│   └── main.py 
│   └── routes.py
    └── schemas.py
├── core/
│   ├── openstack_api.py
├── agent.py
├── cli.py 
├── requirements.txt
└── README.md
```


## Table of Contents

- [Introduction](#-introduction)
- [Features](#-features)
- [Architecture](#-architecture)
- [Setup](#-setup)
- [How It Works](#-how-it-works)
- [Usage](#-usage)
- [Examples](#-examples)
- [Extending](#-extending)
- [Security](#-security)
- [License](#-license)

---

## Introduction

Cloud infrastructure can be complex to navigate. This project bridges that gap by allowing users to manage OpenStack with simple prompts like:

> "Create a server Test-int with volume 15 Gb and Ubuntu 22.04"

With the help of Google Gemini's **function calling** feature and OpenStack's SDK, this tool executes those instructions for you automatically.

---

##  Features

- Natural Language Interface using Gemini Pro
- Gemini Tools API with Function Calling
- Real-time Execution of OpenStack Operations
- Modular and Easily Extensible
- Secure API Integration

---

## Architecture

```plaintext
User Prompt
   │
   ▼
Gemini API (LLM)
   │
   ▼
Function Tool Selection (core logic)
   │
   ▼
OpenStack SDK / HTTP API
   │
   ▼
Execution & Response
```

---

# Run Locally
- This project requires python 3.9

- Clone the project

    ```bash
    https://github.com/AyanGairola/RTDS-007.git
    ```
    or
    ```bash
    git@github.com:AyanGairola/RTDS-007.git
    ```


- Create a new Environment

    - using Anaconda

    ```bash
    conda create venv
    conda activate venv
    ```
    Or

    - using venv

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

- Install Dependencies
    ```bash
    pip install -r requirements.txt
    ```
- Add Your Credentials in .env file
    ```bash
    OS_AUTH_URL=""
    OS_USERNAME=""
    OS_PASSWORD=""
    OS_PROJECT_NAME=""
    OS_PROJECT_ID=""
    OS_USER_DOMAIN_NAME=""
    OS_PROJECT_DOMAIN_NAME=""
    OS_INTERFACE=""
    OS_REGION_NAME=""
    GOOGLE_API_KEY = ""
    ```

- To run agentic simulation
    ```bash
    python agent.py
    ```
- To run cli simulation
    ```bash
    python cli.py
    ```

Sample Interaction:

```
User: "List all servers in the project"
Gemini → OpenStack: list_servers()
Output: { 'vm1': 'ACTIVE', 'vm2': 'SHUTOFF' }
```

---

##  Examples

### Create a Server

**Prompt:**  
> "create an S.4 VM named dev-box-2 using Ubuntu-24.04 on External_Net with volume 10"

**Mapped Function Call:**

```json
 Configuration:
   - Name: dev-box
   - Flavor: dev-box-2
   - Image: Ubuntu-24.04 (default)
   - Network: External_Net
   - Volume_size: 10 (default)
```

---

### 🔹 Resize the flovor

**Prompt:**  
> "Resize the instance <id> to C.4"

---

##  Extending

To add more functions, update the `tools` list in `agent.py`:

```python
{
  "function_declaration": {
    "name": "delete_network",
    "description": "Delete a network by ID",
    "parameters": {
      "type": "object",
      "properties": {
        "network_id": { "type": "string" }
      },
      "required": ["network_id"]
    }
  }
}
```

Map it to a real implementation in your function handler.

---

## Security

- Keep your API keys safe using `.env` or secret managers.
- Restrict Gemini’s API scope to relevant permissions.
- Avoid exposing sensitive logs publicly.

---
