#!/usr/bin/env python3
"""
Main runner for the OpenStack AI Agent Chatbot Assistant.
Supports an advanced CLI with full chatbot capabilities and a placeholder for Web UI.
"""

import argparse
import sys
import json
import re
import os
from collections import deque
from datetime import datetime
import logging
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.text import Text
    from rich.status import Status
    from rich.pretty import Pretty
    from rich.table import Table
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    class console:
        @staticmethod
        def print(*args, **kwargs):
            print(*args)
    class Prompt:
        @staticmethod
        def ask(prompt_text, default=None):
            return input(prompt_text + (f" [{default}]" if default else "") + ": ")
    class Confirm:
        @staticmethod
        def ask(prompt_text, default=False):
            return input(prompt_text + (" [y/N]" if not default else " [Y/n]") + ": ").lower() in ('y', 'yes')
    class Panel:
        def __init__(self, content, title="", border_style="", expand=False, subtitle=""):
            print(f"--- {title} ---")
            print(content.text if isinstance(content, Text) else str(content))
            if subtitle:
                print(f"({subtitle})")
            print("---------------")
    class Text:
        def __init__(self, text_content, style=None, overflow=None):
            self.text = str(text_content)
        @staticmethod
        def assemble(*args):
            return Text("".join(part[0] if isinstance(part, tuple) else str(part) for part in args))
        def __str__(self):
            return self.text
    class Pretty:
        def __init__(self, obj, expand_all=None):
            try:
                self.formatted_text = json.dumps(obj, indent=2)
            except ValueError:
                self.formatted_text = str(obj)
        def __str__(self):
            return self.formatted_text
    class Table:
        def __init__(self, title=None):
            self.title = title
            self.rows = []
            self.columns = []
        def add_column(self, header, style=None):
            self.columns.append(header)
        def add_row(self, *args):
            self.rows.append(args)
        def __str__(self):
            output = f"{self.title}\n" if self.title else ""
            output += " | ".join(self.columns) + "\n"
            output += "-" * (len(output) - 1) + "\n"
            for row in self.rows:
                output += " | ".join(str(cell) for cell in row) + "\n"
            return output

import requests
from agent import OpenStackAgent
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configuration and context management
class ChatbotConfig:
    def __init__(self):
        self.verbose = False
        self.output_format = "pretty"  # Options: pretty, json, raw
        self.language = "en"
        self.load_config()

    def load_config(self):
        config_file = "chatbot_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.verbose = config.get("verbose", False)
                self.output_format = config.get("output_format", "pretty")
                self.language = config.get("language", "en")

    def save_config(self):
        config = {
            "verbose": self.verbose,
            "output_format": self.output_format,
            "language": self.language
        }
        with open("chatbot_config.json", 'w') as f:
            json.dump(config, f, indent=2)

class ConversationContext:
    def __init__(self, max_history=10):
        self.history = deque(maxlen=max_history)
        self.current_context = None

    def add_to_history(self, command, output):
        self.history.append({"command": command, "output": output, "timestamp": datetime.now().isoformat()})

    def get_history(self):
        return list(self.history)

    def set_current_context(self, context):
        self.current_context = context

    def get_current_context(self):
        return self.current_context

# Setup logging
logging.basicConfig(filename="chatbot.log", level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Enhanced help with examples and settings
def display_help(config):
    help_text = Text.assemble(
        ("Welcome to the OpenStack AI Chatbot Assistant!\n\n", "bold white"),
        ("Basic Commands:\n", "bold purple"),
        ("- list all servers: ", "italic magenta"), ("Lists all servers.\n", "white"),
        ("- create a new server named [name]: ", "italic magenta"), ("Creates a server.\n", "white"),
        ("- delete server with ID [ID]: ", "italic magenta"), ("Deletes a server.\n", "white"),
        ("- show details of server with ID [ID]: ", "italic magenta"), ("Shows server details.\n", "white"),
        ("\nAdvanced Commands:\n", "bold purple"),
        ("- set verbose on/off: ", "italic blue"), ("Toggles verbose mode.\n", "white"),
        ("- set output format [pretty/json/raw]: ", "italic blue"), ("Changes output style.\n", "white"),
        ("- history: ", "italic blue"), ("Shows command history.\n", "white"),
        ("- tutorial: ", "italic blue"), ("Starts an interactive tutorial.\n", "white"),
        ("\nExamples:\n", "bold purple"),
        ("- 'list all servers' then 'show details of the first one'\n", "white"),
        ("- 'create a new server named test-vm with flavor m1.small'\n", "white"),
        ("\nTips:\n", "italic yellow"),
        ("- Use 'it' or 'that' to refer to the last output.\n", "white"),
        ("- Current settings: Verbose=", "white"), (str(config.verbose), "bold green" if config.verbose else "bold red"),
        (", Format=", "white"), (config.output_format, "bold cyan"), ("\n", "white")
    )
    console.print(Panel(help_text, title="[bold purple]Chatbot Help[/bold purple]", border_style="purple"))

# Interactive tutorial
def run_tutorial(agent, context, config):
    console.print(Panel(Text("Starting interactive tutorial...", style="bold cyan"), title="Tutorial", border_style="cyan"))
    steps = [
        ("Let's list all servers. Type: 'list all servers'", lambda x: "list all" in x.lower() and "servers" in x.lower()),
        ("Great! Now, refer to the last output. Try: 'show details of the first one'", 
         lambda x: "show details" in x.lower() and ("first" in x.lower() or "it" in x.lower())),
        ("Nice! Let's create a server. Type: 'create a new server named tutorial-vm'", 
         lambda x: "create" in x.lower() and "server" in x.lower() and "tutorial-vm" in x.lower())
    ]
    for step, validator in steps:
        while True:
            user_input = Prompt.ask(f"\n[bold blue]{step}[/bold blue]")
            if validator(user_input):
                try:
                    output = agent.execute_command(user_input)
                    context.add_to_history(user_input, output)
                    context.set_current_context(output if isinstance(output, list) else [output])
                    console.print(Panel(Pretty(output), title="Step Output", border_style="green"))
                    break
                except Exception as e:
                    console.print(Text(f"Error: {e}. Try again!", style="red"))
            else:
                console.print(Text("That’s not quite right. Try again!", style="yellow"))

# Parse follow-up queries
def parse_follow_up(user_input, context):
    if not context or not isinstance(context, list):
        return None
    if "first" in user_input:
        return context[0].get("id") if context and isinstance(context[0], dict) else context[0]
    elif "second" in user_input and len(context) > 1:
        return context[1].get("id") if isinstance(context[1], dict) else context[1]
    elif "last" in user_input:
        return context[-1].get("id") if isinstance(context[-1], dict) else context[-1]
    elif re.search(r"(server|network)\s+with\s+ID\s+(\w+)", user_input):
        return re.search(r"(server|network)\s+with\s+ID\s+(\w+)", user_input).group(2)
    return None

def format_output(output, config):
    if output is None:
        return Text("Command executed successfully. No output.", style="italic green")
    elif config.output_format == "json":
        return Pretty(json.dumps(output, indent=2))
    elif config.output_format == "raw":
        return Text(str(output))
    else:  # pretty
        if isinstance(output, list) and output and isinstance(output[0], dict):
            table = Table(title="Results")
            keys = output[0].keys()
            for key in keys:
                table.add_column(key.capitalize(), style="blue")
            for item in output:
                table.add_row(*[str(item.get(k, "")) for k in keys])
            return table
        return Pretty(output, expand_all=True)

def run_cli(remote_url=None):
    welcome_ascii = (
        "╭────────────── OpenStack AI Agent ───────────────╮\n"
        "│ Welcome to the OpenStack AI Agent v1.0          │\n"
        "│                                                 │\n"
        "│ Interact with OpenStack using natural language. │\n"
        "│ Try commands like:                              │\n"
        "│ - 'list all servers'                            │\n"
        "│ - 'create a new server named my-vm'             │\n"
        "│ - 'show details of server with ID 1234'         │\n"
        "│                                                 │\n"
        "│ Type 'help' for commands or 'exit' to quit.     │\n"
        "╰─────────────────────────────────────────────────╯\n"
        "   🚀 Powered by Developers, for Developers! 🚀    "
    )
    if RICH_AVAILABLE:
        console.print(Panel(Text(welcome_ascii, style="bold cyan"), title="", border_style="cyan", expand=False))
    else:
        print(welcome_ascii)

    config = ChatbotConfig()
    context = ConversationContext()
    agent = None
    if not remote_url:
        agent = OpenStackAgent()

    while True:
        try:
            user_input = Prompt.ask("\n[bold purple]➜ Command[/bold purple]", default="help")
            user_input = user_input.strip()

            if user_input.lower() in ["exit", "quit"]:
                console.print(Panel(Text("Goodbye!", style="yellow"), title="Session Ended", border_style="yellow"))
                break

            if user_input.lower() == "help":
                display_help(config)
                continue

            if user_input.lower() == "tutorial":
                run_tutorial(agent, context, config)
                continue

            if user_input.lower() == "history":
                history = context.get_history()
                table = Table(title="Command History")
                table.add_column("Timestamp", style="dim cyan")
                table.add_column("Command", style="bold magenta")
                table.add_column("Output Preview", style="white")
                for entry in history:
                    output_prev = str(entry["output"])[:50] + "..." if len(str(entry["output"])) > 50 else str(entry["output"])
                    table.add_row(entry["timestamp"], entry["command"], output_prev)
                console.print(table)
                continue

            if user_input.lower().startswith("set verbose"):
                config.verbose = "on" in user_input.lower()
                config.save_config()
                console.print(Text(f"Verbose mode {'enabled' if config.verbose else 'disabled'}.", style="green"))
                continue
            elif user_input.lower().startswith("set output format"):
                fmt = re.search(r"format\s+(pretty|json|raw)", user_input.lower())
                if fmt:
                    config.output_format = fmt.group(1)
                    config.save_config()
                    console.print(Text(f"Output format set to {config.output_format}.", style="green"))
                else:
                    console.print(Text("Invalid format. Use: pretty, json, raw.", style="red"))
                continue

            if "it" in user_input or "that" in user_input or "first" in user_input or "second" in user_input or "last" in user_input:
                last_context = context.get_current_context()
                if last_context:
                    target = parse_follow_up(user_input, last_context)
                    if target:
                        user_input = re.sub(r"\b(it|that|first|second|last)\b", target, user_input)
                    else:
                        console.print(Panel(Text("Cannot resolve reference.", style="red"), title="Error"))
                        continue
                else:
                    console.print(Panel(Text("No prior context available.", style="red"), title="Error"))
                    continue

            with console.status(f"[yellow]Processing: '{user_input}'[/yellow]", spinner="dots") as status:
                if remote_url:
                    try:
                        payload = {'command': user_input}
                        response = requests.post(f"{remote_url.rstrip('/')}/command", json=payload, timeout=30)
                        response.raise_for_status()
                        json_response = response.json()
                        if 'result' in json_response:
                            command_output = json_response['result']
                        elif 'error' in json_response:
                            raise Exception(json_response['error'])
                        else:
                            raise Exception("Invalid response format from remote API.")
                        
                        context.add_to_history(user_input, command_output)
                        context.set_current_context(command_output if isinstance(command_output, list) else [command_output])
                        output_display = format_output(command_output, config)
                        console.print(Panel(output_display, title="[green]Remote Success[/green]", border_style="green", 
                                            subtitle=f"Remote Command: '{user_input}'"))
                        logging.info(f"Remote Command: {user_input} | Success")
                    except requests.exceptions.RequestException as e:
                        error_msg = f"Network error connecting to remote API: {e}"
                        console.print(Panel(Text(f"Error: {error_msg}", style="red"), 
                                            title="[red]Remote API Error[/red]", border_style="red"))
                        logging.error(f"Remote Command: {user_input} | Error: {error_msg}")
                    except Exception as e:
                        error_msg = str(e) or "Unknown error from remote API."
                        console.print(Panel(Text(f"Error: {error_msg}", style="red"), 
                                            title="[red]Remote API Error[/red]", border_style="red"))
                        logging.error(f"Remote Command: {user_input} | Error: {error_msg}")
                    continue

                # Local processing
                try:
                    status.stop()
                    command_output = agent.execute_command(user_input)
                    status.start()
                    context.add_to_history(user_input, command_output)
                    context.set_current_context(command_output if isinstance(command_output, list) else [command_output])
                    output_display = format_output(command_output, config)
                    console.print(Panel(output_display, title="[green]Success[/green]", border_style="green", 
                                        subtitle=f"Command: '{user_input}'"))
                    if config.verbose:
                        console.print(Text(f"Verbose: Processed in {agent.last_execution_time:.2f}s", style="dim cyan"))
                    logging.info(f"Command: {user_input} | Success")
                except Exception as e:
                    error_msg = str(e) or "Unknown error."
                    suggestion = "Try 'help' or rephrase." if "not found" not in error_msg.lower() else "Check ID/name."
                    console.print(Panel(Text(f"Error: {error_msg}\nSuggestion: {suggestion}", style="red"), 
                                        title="[red]Error[/red]", border_style="red"))
                    logging.error(f"Command: {user_input} | Error: {error_msg}")

        except KeyboardInterrupt:
            console.print(Panel(Text("Interrupted. Exiting...", style="yellow"), title="Interrupted"))
            break
        except Exception as e:
            console.print(Panel(Text(f"Fatal error: {e}", style="red"), title="CLI Error"))
            logging.critical(f"Fatal error: {e}")

def run_web():
    app = Flask(__name__)
    CORS(app)
    agent = OpenStackAgent()

    @app.route('/command', methods=['POST'])
    def handle_command():
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'error': 'Missing command in request body'}), 400
        
        user_command = data['command']
        
        try:
            command_output = agent.execute_command(user_command, is_web=True)
            if isinstance(command_output, dict) and 'status' in command_output:
                if command_output['status'] == 'success':
                    return jsonify({'result': command_output.get('result')})
                elif command_output['status'] == 'missing_parameters':
                    return jsonify(command_output), 400
                elif command_output['status'] == 'clarification_needed':
                    return jsonify(command_output), 400
                else:
                    error_msg = command_output.get('message', 'An unknown error occurred in the agent.')
                    logging.error(f"API Command: {user_command} | Agent Error: {error_msg}")
                    return jsonify({'error': error_msg}), 500
            else:
                error_msg = "Unexpected response format from agent."
                logging.error(f"API Command: {user_command} | Unexpected Agent Response: {command_output}")
                return jsonify({'error': error_msg}), 500

        except Exception as e:
            error_msg = str(e) or "Unknown error processing command."
            logging.error(f"API Command: {user_command} | Error: {error_msg}")
            return jsonify({'error': error_msg}), 500

    console.print(Panel(Text("Starting Flask web server for OpenStack AI Agent...", style="bold blue"), title="Web Server Mode", border_style="blue"))
    console.print(Text("API Endpoint available at ", style="green"), Text("/command", style="bold green"), Text(" (POST)", style="green"))
    console.print(Text("Example usage with curl:", style="yellow"))
    console.print(Text("curl -X POST -H \"Content-Type: application/json\" -d '{\"command\": \"list all servers\"}' http://localhost:5000/command", style="italic yellow"))
    app.run(host='0.0.0.0', port=5000, debug=False)

def main():
    parser = argparse.ArgumentParser(description="OpenStack AI Chatbot Assistant")
    parser.add_argument("mode", choices=["cli", "web"], default="cli", nargs="?", help="Run in CLI or web mode (local agent or server).")
    parser.add_argument("--remote-url", type=str, default=None, help="URL of the remote OpenStack AI Agent API to connect the CLI to (e.g., http://your-ngrok-url).")
    args = parser.parse_args()
    if args.remote_url:
        run_cli(remote_url=args.remote_url)
    elif args.mode == "cli":
        run_cli()
    elif args.mode == "web":
        run_web()
    else:
        print("Invalid mode or arguments. Use --help for options.")
        sys.exit(1)

if __name__ == "__main__":
    main()