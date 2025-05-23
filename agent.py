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
# from api import OpenStackAPI
from fake_api import FakeOpenStackAPI as OpenStackAPI
from typing import Dict, Any, List, Optional, Callable

# Configuration
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

DEFAULT_PARAMS_MAP = {
    'create_server': {
        'network_name': 'private-net',  # Updated to match fake_data
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

    def _confirm_critical_action(self, function_name: str, parameters: Dict[str, Any]) -> bool:
        """Prompts the user to confirm a critical action."""
        critical_operations = [
            'create_server', 'delete_server', 'resize_server',
            'create_volume', 'delete_volume', 'extend_volume',
            'create_network_with_subnet', 'delete_network', 'delete_subnet',
            'create_floating_ip', 'delete_floating_ip',
            'attach_volume_to_server', 'detach_volume_from_server',
            'add_floating_ip_to_server', 'remove_floating_ip_from_server',
            # Add other potentially destructive or resource-intensive operations here
        ]

        if function_name in critical_operations:
            print("\n--- CRITICAL ACTION REQUIRES CONFIRMATION ---")
            print(f"You are about to execute: {function_name}")
            print("With parameters:")
            for key, value in parameters.items():
                print(f"  - {key}: {value}")
            
            while True:
                confirmation = input("Are you sure you want to proceed? Type 'yes' to confirm or 'no' to cancel: ").strip().lower()
                if confirmation == 'yes':
                    print("Confirmation received. Proceeding with the operation...")
                    return True
                elif confirmation == 'no':
                    print("Operation cancelled by user.")
                    return False
                else:
                    print("Invalid input. Please type 'yes' or 'no'.")
        return True # Not a critical action, or not in the list, proceed by default

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

    def process_user_query(self, user_query: str) -> Optional[Any]:
        """Processes user query, generates command, validates, collects params, and then calls execute_command."""
        initial_intent = self._generate_initial_command_with_ai(user_query)
        if not initial_intent or initial_intent.get('function_name') == 'clarify':
            print("Unclear request or AI generation failed. Please provide more details or rephrase.")
            return "Error: Unclear request or AI generation failed."

        print(f"\nLayer 1 - AI Intent: Function: {initial_intent.get('function_name')}, Parameters: {initial_intent.get('parameters')}")

        validation = self._validate_command_with_ai(user_query, initial_intent)
        print(f"Layer 2 - Validation: Valid: {validation.get('is_valid')}, Feedback: {validation.get('feedback')}")
        print(f"  Missing by Intent: {validation.get('missing_parameters_based_on_intent')}")
        print(f"  Suggested Corrections: {validation.get('suggested_corrections')}")

        final_function_name = initial_intent['function_name']
        final_params = initial_intent.get('parameters', {}).copy()

        if validation.get("suggested_corrections"):
            for param, value in validation["suggested_corrections"].items():
                if not str(value).startswith("Please provide"): 
                    final_params[param] = value
        
        params_to_prompt_for_details: Dict[str, Dict[str, Any]] = {}
        all_func_param_details = self.api_methods.get(final_function_name, {}).get('params', {})

        if not all_func_param_details and final_function_name in self.api_methods:
             pass # No parameters to prompt for if none are defined for a known function
        elif not all_func_param_details: # Function itself is not in api_methods
            print(f"Warning: Function '{final_function_name}' not found in defined API methods. Cannot determine parameters.")
        else:
            for param_name, details in all_func_param_details.items():
                if details['required'] and (param_name not in final_params or final_params[param_name] is None):
                    params_to_prompt_for_details[param_name] = details
            
            intent_missing_param_names = validation.get('missing_parameters_based_on_intent', [])
            for param_name in intent_missing_param_names:
                if param_name in all_func_param_details and \
                   param_name not in params_to_prompt_for_details and \
                   (param_name not in final_params or final_params[param_name] is None):
                    params_to_prompt_for_details[param_name] = all_func_param_details[param_name]

            if final_function_name in self.default_params_map:
                for param_name_in_map, _ in self.default_params_map[final_function_name].items():
                    if param_name_in_map in all_func_param_details and \
                       not all_func_param_details[param_name_in_map]['required'] and \
                       param_name_in_map not in params_to_prompt_for_details and \
                       (param_name_in_map not in final_params or final_params[param_name_in_map] is None):
                        params_to_prompt_for_details[param_name_in_map] = all_func_param_details[param_name_in_map]
        
        if params_to_prompt_for_details:
            print(f"\nParameter(s) need clarification/input: {', '.join(params_to_prompt_for_details.keys())}")
            collected_params = self._prompt_for_parameters(final_function_name, params_to_prompt_for_details, final_params)
            final_params.update(collected_params)

        command_to_execute = {
            "function_name": final_function_name,
            "parameters": final_params
        }
        
        return self.execute_command(command_to_execute)

    def execute_command(self, command: Dict[str, Any]) -> Optional[Any]:
        """Executes the OpenStack command after consent and parameter finalization."""
        function_name = command.get('function_name')
        parameters = command.get('parameters', {})

        if not function_name or function_name == 'clarify':
            print("Cannot execute command: function name is missing or requires clarification.")
            return None

        if function_name not in self.api_methods:
            print(f"Error: Function '{function_name}' not found in API methods list.")
            return None

        api_func_params = self.api_methods[function_name]['params']
        final_params = {}
        for param_name, details in api_func_params.items():
            if param_name in parameters and parameters[param_name] is not None:
                final_params[param_name] = parameters[param_name]
            elif details['required'] and self.default_params_map.get(function_name, {}).get(param_name) is not None:
                default_val = self.default_params_map[function_name][param_name]
                print(f"Using default value for '{param_name}': {default_val}")
                final_params[param_name] = default_val
            elif not details['required'] and details['default'] is not None:
                final_params[param_name] = details['default']
            elif details['required']:
                print(f"Error: Required parameter '{param_name}' for '{function_name}' is missing, has no default, and was not provided.")
                return None
        
        for p_name, p_val in parameters.items():
            if p_name not in final_params and p_name in api_func_params:
                 # Parameter was provided, is valid, but wasn't required and had no default from map, so add it.
                 final_params[p_name] = p_val
            elif p_name not in api_func_params:
                print(f"Warning: Parameter '{p_name}' is not recognized for function '{function_name}' and will be ignored.")

        if not self._confirm_critical_action(function_name, final_params):
            return "Operation cancelled by user."

        try:
            if hasattr(self.openstack_api, 'connect') and not self.openstack_api.connect():
                 print("Failed to connect to OpenStack.")
                 return "Error: Failed to connect to OpenStack."

            func_to_call = getattr(self.openstack_api, function_name)
            print(f"\nExecuting: {function_name}({', '.join(f'{k}={v!r}' for k, v in final_params.items())})")
            start_time = time.time()
            output = func_to_call(**final_params)
            self.last_execution_time = time.time() - start_time
            print("\nSuccess!")
            if output:
                print(f"Output: {json.dumps(output, indent=2) if isinstance(output, (dict, list)) else output}")
            print(f"Time: {self.last_execution_time:.2f} seconds")
            return output
        except AttributeError:
            print(f"Error: API function '{function_name}' not found on the API object.")
            return f"Error: API function '{function_name}' not found on the API object."
        except Exception as e:
            print(f"\nExecution failed: {e}")
            if "401" in str(e):
                print("Authentication error (HTTP 401). Please verify your OpenStack credentials.")
            return f"Error: Execution failed - {str(e)}"

if __name__ == "__main__":
    agent = OpenStackAgent()
    print("Type your commands (e.g., 'create a volume named myvol'). Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nCommand: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if user_input.strip():
                agent.process_user_query(user_input)
        except KeyboardInterrupt:
            print("\nExiting.")
            break
    print("Agent stopped.")