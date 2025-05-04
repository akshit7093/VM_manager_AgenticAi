#!/usr/bin/env python3
"""
AI Agent for OpenStack Management using Google Gemini

This agent takes natural language commands from the user, interprets them using
Google's Gemini model, and executes the corresponding OpenStack operations
via the OpenStackAPI class from api.py.
"""

import os
import json
import inspect
import google.generativeai as genai
from api import OpenStackAPI  # Import the OpenStack API class
from typing import Dict, Any, List, Optional, Callable

# --- Configuration ---
# IMPORTANT: Set your Google API Key as an environment variable
# export GOOGLE_API_KEY="YOUR_API_KEY"
GOOGLE_API_KEY = "AIzaSyChSRoo-5yi4ksr7DiKFXXutMsPEGxlYJA"

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    print("Please set your Google API Key to use the agent.")
    # exit(1) # Exit if you want to enforce key presence
    # For development, you might allow proceeding without a key, but AI calls will fail
    print("Warning: Proceeding without Google API Key. AI functionality will be disabled.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        GOOGLE_API_KEY = None # Disable AI if configuration fails

# --- Agent Logic ---

class OpenStackAgent:
    """The AI agent to interact with OpenStack."""

    def __init__(self):
        """Initialize the agent and the OpenStack API connection."""
        self.openstack_api = OpenStackAPI()
        self.model = None
        if GOOGLE_API_KEY:
            try:
                # Initialize the Gemini model
                # Use a model suitable for function calling/structured output if available
                # Or use a general text model and parse the output
                self.model = genai.GenerativeModel('gemma-3-1b-it')
                print("Google Gemini model initialized.")
            except Exception as e:
                print(f"Error initializing Gemini model: {e}")
                self.model = None
        else:
            print("Google AI model not initialized due to missing API key.")

        # Dynamically get available methods from OpenStackAPI
        self.api_methods = self._get_api_methods()

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

    def _generate_ai_prompt(self, user_query: str) -> str:
        """Creates the prompt for the Gemini model."""
        prompt = f"You are an assistant that translates natural language requests into OpenStack API calls.\n"
        prompt += f"Based on the user's request: '{user_query}', identify the correct OpenStack operation and extract the necessary parameters.\n\n"
        prompt += "Available OpenStack Operations:\n"
        for name, details in self.api_methods.items():
            prompt += f"- Function: {name}\n"
            prompt += f"  Description: {details['doc']}\n"
            prompt += f"  Parameters:\n"
            if details['params']:
                for param_name, param_details in details['params'].items():
                    req_status = 'Required' if param_details['required'] else f"Optional (default: {param_details['default']})"
                    prompt += f"    - {param_name} (Type: {param_details['type']}, {req_status})\n"
            else:
                prompt += "    - None\n"
            prompt += "\n"

        # Add specific guidance for server creation
        if 'create_server' in self.api_methods:
            prompt += "\nSpecial Notes for Server Creation:\n"
            prompt += "- When creating a server, you MUST specify a valid network name from available networks.\n"
            prompt += "- You can get available networks by calling list_networks() first if needed.\n"
            prompt += "- The default network 'default' may not exist in all environments.\n"

        prompt += "Please respond ONLY with a JSON object containing:"
        prompt += "1. 'function_name': The name of the function to call (must be one of the available functions)."
        prompt += "2. 'parameters': A dictionary of parameter names and their extracted values from the user query."
        prompt += "Example Response: {\"function_name\": \"create_server\", \"parameters\": {\"name\": \"my-vm\", \"image_name\": \"Ubuntu-24.04\", \"flavor_name\": \"S.4\", \"network_name\": \"my-network\"}}\n"
        prompt += "If the user query is unclear or doesn't match any function, respond with: {\"function_name\": \"clarify\", \"parameters\": {}}\n"
        prompt += "User Query: " + user_query + "\n"
        prompt += "Response JSON:"
        return prompt

    def _parse_user_query_with_ai(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Uses Gemini to parse the user query and returns the structured intent."""
        if not self.model:
            print("AI model not available. Cannot parse query.")
            # Basic keyword matching as fallback?
            if "list servers" in user_query.lower(): return {"function_name": "list_servers", "parameters": {}}
            if "list images" in user_query.lower(): return {"function_name": "list_images", "parameters": {}}
            # Add more basic fallbacks if needed
            return {"function_name": "clarify", "parameters": {}}

        prompt = self._generate_ai_prompt(user_query)
        print("\n--- Sending Prompt to Gemini ---")
        # print(prompt) # Uncomment to debug the prompt
        print("--- End Prompt ---\n")

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            print(f"Gemini Raw Response: {response_text}")
            
            # Fix common JSON formatting issues
            try:
                # Attempt to parse directly first
                parsed_response = json.loads(response_text)
                return parsed_response
            except json.JSONDecodeError as e:
                print(f"Initial JSON parse failed, attempting fixes: {e}")
                
                # Try common fixes for malformed JSON
                try:
                    # Fix empty parameters object
                    if '"none":}' in response_text:
                        response_text = response_text.replace('"none":}', '"none": null}')
                    # Fix unterminated strings
                    if '"parameters": {' in response_text and not response_text.endswith('}}'):
                        response_text = response_text.rstrip() + '}}'
                    
                    parsed_response = json.loads(response_text)
                    return parsed_response
                except json.JSONDecodeError as e:
                    print(f"Failed to parse even after fixes: {e}")
                    return {"function_name": "clarify", "parameters": {}}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from AI: {e}")
            print(f"Raw response was: {response.text}")
            return {"function_name": "clarify", "parameters": {}}
        except Exception as e:
            print(f"Error interacting with Google AI: {e}")
            return {"function_name": "clarify", "parameters": {}}

    def _get_missing_parameters(self, function_name: str, provided_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Identifies required parameters missing from the provided set."""
        missing = {}
        if function_name not in self.api_methods:
            return {}
        
        required_params = self.api_methods[function_name]['params']
        for param_name, details in required_params.items():
            if details['required'] and param_name not in provided_params:
                missing[param_name] = details
                
        return missing
        
    def _prompt_for_parameters(self, missing_params: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Interactively prompts user for missing parameter values."""
        collected_params = {}
        for param_name, details in missing_params.items():
            while True:
                prompt = f"Please enter {param_name} ({details.get('type', 'string')}): "
                value = input(prompt).strip()
                if value:
                    collected_params[param_name] = value
                    break
                print(f"Error: {param_name} is required.")
        return collected_params

    def _prompt_for_parameters(self, missing_params: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Prompts the user to provide values for missing parameters."""
        collected_params = {}
        print("\nPlease provide the following information:")
        for name, details in missing_params.items():
            while True:
                value = input(f"  - {name} (Type: {details['type']}): ")
                # Basic type validation could be added here if needed
                if value: # Ensure some input is given
                    collected_params[name] = value
                    break
                else:
                    print("  Input cannot be empty.")
        return collected_params

    def execute_command(self, user_query: str):
        """Parses the user query and executes the corresponding OpenStack command."""
        parsed_intent = self._parse_user_query_with_ai(user_query)

        if not parsed_intent or parsed_intent['function_name'] == 'clarify':
            print("Could not understand the request or required clarification. Please try again with more details.")
            return

        function_name = parsed_intent['function_name']
        provided_params = parsed_intent.get('parameters', {})
        
        # Special validation for volume creation
        if function_name == 'create_volume' and 'size_gb' not in provided_params:
            print("Error: Volume creation requires 'size_gb' parameter. Please specify volume size.")
            return

        if function_name not in self.api_methods:
            print(f"Error: The identified function '{function_name}' is not a valid OpenStack operation.")
            print("Available functions are:", list(self.api_methods.keys()))
            return

        # Check for missing required parameters
        missing_params = self._get_missing_parameters(function_name, provided_params)
        if missing_params:
            print(f"Missing required parameters for '{function_name}': {list(missing_params.keys())}")
            
            # For server creation, suggest listing available networks if network_name is missing
            if function_name == 'create_server' and 'network_name' in missing_params:
                print("\nTip: You can see available networks by running 'list networks' first.")
                
            additional_params = self._prompt_for_parameters(missing_params)
            provided_params.update(additional_params)
            # Re-check if still missing (user might have entered empty strings)
            if self._get_missing_parameters(function_name, provided_params):
                 print("Error: Still missing required parameters after prompting. Aborting.")
                 return

        # Get the actual function object from OpenStackAPI
        func_to_call: Optional[Callable] = getattr(self.openstack_api, function_name, None)

        if not func_to_call or not callable(func_to_call):
            print(f"Internal Error: Could not find callable method '{function_name}' in OpenStackAPI.")
            return

        # Special validation for create_server - check network exists
        if function_name == 'create_server' and 'network_name' in provided_params:
            networks = self.openstack_api.list_networks()
            network_names = [n['name'] for n in networks]
            if provided_params['network_name'] not in network_names:
                print(f"Error: Network '{provided_params['network_name']}' not found. Available networks: {network_names}")
                return
                
        # Special validation for volume creation - check size_gb exists
        if function_name == 'create_volume':
            if 'size_gb' not in provided_params:
                print("Error: Volume creation requires 'size_gb' parameter. Please specify volume size.")
                return
            # Ensure size_gb is properly passed to the function
            if isinstance(provided_params['size_gb'], str):
                try:
                    provided_params['size_gb'] = int(provided_params['size_gb'])
                except ValueError:
                    print("Error: 'size_gb' must be a numeric value")
                    return

        # Prepare arguments for the function call, ensuring correct types if possible
        # Basic type conversion (more robust needed for production)
        final_args = {}
        sig = inspect.signature(func_to_call)
        for name, value in provided_params.items():
            if name in sig.parameters:
                param_type = sig.parameters[name].annotation
                try:
                    if param_type == int and value is not None:
                        # Special handling for volume_size to strip non-numeric characters
                        if name == 'volume_size':
                            value = ''.join(filter(str.isdigit, str(value)))
                            if not value:
                                raise ValueError("Volume size must contain numeric value")
                            try:
                                final_args[name] = int(value)
                            except ValueError:
                                raise ValueError(f"Invalid volume size format: '{value}'. Must be a numeric value (e.g. '10')")
                    elif param_type == bool and value is not None:
                        final_args[name] = str(value).lower() in ['true', '1', 'yes']
                    # Add more type conversions as needed (float, etc.)
                    else:
                        final_args[name] = value # Assume string or correct type
                except ValueError:
                    print(f"Warning: Could not convert parameter '{name}' value '{value}' to expected type {param_type}. Using original value.")
                    final_args[name] = value
            else:
                 print(f"Warning: Parameter '{name}' provided but not expected by function '{function_name}'. Ignoring.")


        print(f"\n--- Executing {function_name} --- ")
        print(f"Parameters: {final_args}")
        try:
            # Ensure connection before calling
            if not self.openstack_api._ensure_connection():
                print("Failed to connect to OpenStack. Cannot execute command.")
                return

            result = func_to_call(**final_args)
            print("\n--- Execution Result ---")
            if isinstance(result, (list, dict)):
                print(json.dumps(result, indent=2, default=str)) # Pretty print JSON-like results
            elif result is None:
                 print("Operation may have failed or returned no specific output.")
            else:
                print(result)
            print("--- End Result ---")

        except Exception as e:
            print(f"\n--- Error during execution of {function_name} ---")
            print(f"Error: {e}")
            print("--- End Error ---")

# --- Main Interaction Loop ---

if __name__ == "__main__":
    agent = OpenStackAgent()
    print("\nOpenStack AI Agent Initialized.")
    print("Type your OpenStack commands in natural language (e.g., 'list my servers', 'create a vm named webserver using Ubuntu-24.04 and S.4 flavor').")
    print("Type 'exit' or 'quit' to stop.")

    while True:
        try:
            user_input = input("\nYour command: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue
            
            agent.execute_command(user_input)

        except KeyboardInterrupt:
            print("\nExiting agent.")
            break
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")

    print("\nAgent stopped.")