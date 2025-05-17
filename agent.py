#!/usr/bin/env python3
"""
AI Agent for OpenStack Management using Google Gemini

This agent takes natural language commands from the user, interprets them using
Google's Gemini model, and executes the corresponding OpenStack operations
via the OpenStackAPI class from api.py.
"""

import os
import json
import re
import inspect
import time
import google.generativeai as genai
from api import OpenStackAPI
from typing import Dict, Any, List, Optional, Callable

# Configuration
GOOGLE_API_KEY = "AIzaSyDliV4c1vzNd2NJ_06lwLaYybLgg8QgA0M"

DEFAULT_PARAMS_MAP = {
    'create_server': {
        'network_name': 'default-private-net',
        'volume_size': 10,
        'flavor_name': 'm1.small',
        'image_name': 'Ubuntu-20.04',
    },
    'create_volume': {
        'name': 'default-volume',
        'size_gb': 10,
    },
    'create_network_with_subnet': {
        'subnet_cidr': '192.168.100.0/24',
        'subnet_name': 'default-subnet',
    },
    'resize_server': {
        'flavor_name': 'm1.medium',
    },
}

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not set.")
    exit(1)
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        exit(1)

class OpenStackAgent:
    """The AI agent to interact with OpenStack."""

    def __init__(self):
        self.openstack_api = OpenStackAPI()
        self.model = genai.GenerativeModel('gemma-3-27b-it')
        self.validation_model = self.model
        self.default_params_map = DEFAULT_PARAMS_MAP
        self.last_execution_time = None
        self.api_methods = self._get_api_methods()
        print("Agent initialized.")

    def _get_api_methods(self) -> Dict[str, Dict[str, Any]]:
        """Inspects OpenStackAPI to find public methods and their parameters."""
        methods = {}
        for name, func in inspect.getmembers(self.openstack_api):
            if not name.startswith('_') and inspect.isroutine(func):
                sig = inspect.signature(func)
                params = {}
                for param_name, param in sig.parameters.items():
                    params[param_name] = {
                        'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                        'required': param.default == inspect.Parameter.empty,
                        'default': param.default if param.default != inspect.Parameter.empty else None
                    }
                methods[name] = {
                    'doc': inspect.getdoc(func) or "No description available.",
                    'params': params
                }
        return methods

    def _get_api_methods_formatted(self) -> str:
        """Formats API methods into a string for prompts."""
        formatted_string = ""
        for name, details in self.api_methods.items():
            formatted_string += f"- Function: {name}\n"
            formatted_string += f"  Description: {details['doc']}\n"
            formatted_string += f"  Parameters:\n"
            if details['params']:
                for param_name, param_details in details['params'].items():
                    req_status = 'Required' if param_details['required'] else f"Optional (default: {param_details['default']})"
                    formatted_string += f"    - {param_name} (Type: {param_details['type']}, {req_status})\n"
            else:
                formatted_string += "    - None\n"
            formatted_string += "\n"
        return formatted_string

    def _generate_ai_prompt(self, user_query: str) -> str:
        """Creates the prompt for the Gemini model."""
        prompt = f"You are an assistant that translates natural language requests into OpenStack API calls.\n"
        prompt += f"Based on the user's request: '{user_query}', identify the correct OpenStack operation and extract the necessary parameters.\n\n"
        prompt += "Available OpenStack Operations:\n"
        prompt += self._get_api_methods_formatted()
        prompt += "\nSpecial Notes:\n"
        prompt += "- For create_volume, required fields are name (str) and size_gb (int).\n"
        prompt += "- For create_server, required fields are name, flavor_name, image_name; network_name and volume_size are optional.\n"
        prompt += "- For commands with parameters, include only parameters explicitly mentioned or clearly inferable.\n"
        prompt += "Please respond ONLY with a JSON object containing:\n"
        prompt += "1. 'function_name': The name of the function to call.\n"
        prompt += "2. 'parameters': A dictionary of parameter names and their extracted values from the user query.\n"
        prompt += "   - Include in 'parameters' only those parameters whose values can be extracted or inferred.\n"
        prompt += "   - If a parameter cannot be determined, do not include it in 'parameters'.\n"
        prompt += "   - Do NOT include placeholder values like 'Please provide...'.\n"
        prompt += "Example Response for 'create a volume named myvol':\n"
        prompt += '{"function_name": "create_volume", "parameters": {"name": "myvol"}}\n'
        prompt += "If unclear, respond with: {'function_name': 'clarify', 'parameters': {}}\n"
        prompt += "Response JSON:"
        return prompt

    def _generate_validation_prompt(self, user_query: str, generated_command: Dict[str, Any]) -> str:
        """Creates the validation prompt."""
        prompt = f"Validate if the command reflects the user's query: '{user_query}'\n"
        prompt += f"Generated command:\n  Function: {generated_command.get('function_name')}\n  Parameters: {json.dumps(generated_command.get('parameters', {}))}\n"
        prompt += "Available Operations:\n" + self._get_api_methods_formatted()
        prompt += "\nNotes:\n"
        prompt += "- For create_volume, ensure name and size_gb are present.\n"
        prompt += "- For create_server, ensure name, flavor_name, image_name are present; network_name and volume_size are optional.\n"
        prompt += "Respond with JSON: {'is_valid': <bool>, 'feedback': '<str>', 'missing_parameters_based_on_intent': [<str>], 'suggested_corrections': {<str>: <str>}}\n"
        prompt += "- Do NOT suggest placeholder values like 'Please provide...'.\n"
        prompt += "- List missing required parameters in 'missing_parameters_based_on_intent'.\n"
        prompt += "- Only suggest corrections for parameters explicitly inferable from the query.\n"
        prompt += "Response JSON:"
        return prompt

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parses JSON response from AI."""
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError as e:
                    print(f"JSON parse failed after fix: {e}")
            return None

    def _generate_initial_command_with_ai(self, user_query: str) -> Dict[str, Any]:
        """Generates initial command using AI."""
        prompt = self._generate_ai_prompt(user_query)
        try:
            response = self.model.generate_content(prompt)
            parsed = self._parse_json_response(response.text)
            return parsed if parsed else {"function_name": "clarify", "parameters": {}}
        except Exception as e:
            print(f"AI error (Layer 1): {e}")
            return {"function_name": "clarify", "parameters": {}}

    def _validate_command_with_ai(self, user_query: str, generated_command: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the command."""
        prompt = self._generate_validation_prompt(user_query, generated_command)
        try:
            response = self.validation_model.generate_content(prompt)
            parsed = self._parse_json_response(response.text)
            if parsed and "is_valid" in parsed:
                parsed.setdefault("feedback", "")
                parsed.setdefault("missing_parameters_based_on_intent", [])
                parsed.setdefault("suggested_corrections", {})
                return parsed
            return {"is_valid": False, "feedback": "Validation failed.", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}
        except Exception as e:
            print(f"AI error (Layer 2): {e}")
            return {"is_valid": False, "feedback": f"Validation error: {e}", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}

    def _get_missing_parameters(self, function_name: str, provided_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Identifies missing or None-valued required parameters."""
        missing = {}
        if function_name not in self.api_methods:
            return {}
        required_params = self.api_methods[function_name]['params']
        for param_name, details in required_params.items():
            if details['required']:
                if param_name not in provided_params or provided_params[param_name] is None:
                    missing[param_name] = details
        return missing

    def _prompt_for_parameters(self, function_name: str, missing_params: Dict[str, Dict[str, Any]], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Prompts user for missing parameters."""
        collected = {}
        print("\nPlease provide the following required parameters (or type 'default' or 'your choice' for default values):")
        for name, details in missing_params.items():
            while True:
                value = input(f"  - {name} (Type: {details['type']}): ").strip()
                if value.lower() in ['default', 'your choice']:
                    default = self.default_params_map.get(function_name, {}).get(name)
                    if default is not None:
                        print(f"    Using default: {default}")
                        collected[name] = default
                        break
                    else:
                        print(f"    No default for '{name}'. Please specify.")
                elif value:
                    try:
                        if details['type'] == 'int':
                            collected[name] = int(value)
                        else:
                            collected[name] = value
                        break
                    except ValueError:
                        print(f"    Please enter a valid {details['type']}.")
                else:
                    print("    Required parameter cannot be empty.")
        return collected

    def execute_command(self, user_query: str):
        """Executes the command after validation and parameter collection."""
        initial_intent = self._generate_initial_command_with_ai(user_query)
        if initial_intent.get('function_name') == 'clarify':
            print("Unclear request. Please provide more details.")
            return

        print(f"\nLayer 1 - Function: {initial_intent.get('function_name')}, Parameters: {initial_intent.get('parameters')}")

        validation = self._validate_command_with_ai(user_query, initial_intent)
        print(f"Layer 2 - Valid: {validation.get('is_valid')}, Feedback: {validation.get('feedback')}")
        print(f"Missing by Intent: {validation.get('missing_parameters_based_on_intent')}")
        print(f"Suggested Corrections: {validation.get('suggested_corrections')}")

        final_function_name = initial_intent['function_name']
        final_params = initial_intent.get('parameters', {}).copy()

        # Apply suggested corrections, excluding placeholders
        if validation.get("suggested_corrections"):
            for param, value in validation.get("suggested_corrections").items():
                if not value.startswith("Please provide"):
                    final_params[param] = value

        # Check for missing required parameters
        missing_params = self._get_missing_parameters(final_function_name, final_params)
        if missing_params:
            print(f"Missing required parameters: {', '.join(missing_params.keys())}")
            collected = self._prompt_for_parameters(final_function_name, missing_params, final_params)
            final_params.update(collected)

        # Final check for missing parameters
        remaining_missing = self._get_missing_parameters(final_function_name, final_params)
        if remaining_missing:
            print(f"Cannot proceed. Missing required parameters: {', '.join(remaining_missing.keys())}")
            return

        print(f"\nExecuting {final_function_name} with parameters: {final_params}")
        if not self.openstack_api.connect():
            print("Failed to connect to OpenStack.")
            return

        api_function = getattr(self.openstack_api, final_function_name, None)
        if api_function:
            try:
                accepted_params = inspect.signature(api_function).parameters
                filtered_params = {k: v for k, v in final_params.items() if k in accepted_params}
                start_time = time.time()
                output = api_function(**filtered_params)
                self.last_execution_time = time.time() - start_time
                print("\nSuccess!")
                if output:
                    print(f"Output: {output}")
                print(f"Time: {self.last_execution_time:.2f} seconds")
            except Exception as e:
                print(f"\nExecution failed: {e}")
                if "401" in str(e):
                    print("Authentication error (HTTP 401). Please verify your OpenStack credentials in api.py.")
        else:
            print(f"Function '{final_function_name}' not found.")

if __name__ == "__main__":
    agent = OpenStackAgent()
    print("Type your commands (e.g., 'create a volume named myvol'). Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nCommand: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if user_input.strip():
                agent.execute_command(user_input)
        except KeyboardInterrupt:
            print("\nExiting.")
            break
    print("Agent stopped.")