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
import google.generativeai as genai
from api import OpenStackAPI  # Import the OpenStack API class
from typing import Dict, Any, List, Optional, Callable
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
# IMPORTANT: Set your Google API Key as an environment variable
# export GOOGLE_API_KEY="YOUR_API_KEY"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Default parameters for certain operations if user inputs 'default'
DEFAULT_PARAMS_MAP = {
    'create_server': {
        'network_name': 'default-private-net', # Example, user might need to adjust
        # Add other defaults as needed, e.g., image_name, flavor_name if very common
    },
    'create_volume': {
        # 'size_gb': 10 # Example
    },
    # Add other functions and their defaultable parameters
}

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
        self.validation_model = None # Can be the same as self.model or a different one
        self.default_params_map = DEFAULT_PARAMS_MAP

        if GOOGLE_API_KEY:
            try:
                # Initialize the Gemini model
                self.model = genai.GenerativeModel('gemma-3-27b-it') # As per user's existing code
                self.validation_model = self.model # Re-use the same model for validation
                print("Google Gemini model (for generation and validation) initialized.")
            except Exception as e:
                print(f"Error initializing Gemini model: {e}")
                self.model = None
                self.validation_model = None
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
        """Creates the prompt for the Gemini model for initial command generation."""
        prompt = f"You are an assistant that translates natural language requests into OpenStack API calls.\n"
        prompt += f"Based on the user's request: '{user_query}', identify the correct OpenStack operation and extract the necessary parameters.\n\n"
        prompt += "Available OpenStack Operations:\n"
        prompt += self._get_api_methods_formatted()

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

    def _generate_validation_prompt(self, user_query: str, generated_command: Dict[str, Any]) -> str:
        """Creates the prompt for the AI model to validate a generated command."""
        prompt = f"You are an AI assistant that validates if a generated OpenStack command accurately reflects a user's original query and intent.\n\n"
        prompt += f"Original user query: '{user_query}'\n\n"
        prompt += f"Generated command by another AI:\n"
        prompt += f"  Function: {generated_command.get('function_name', 'N/A')}\n"
        prompt += f"  Parameters: {json.dumps(generated_command.get('parameters', {}))}\n\n"
        prompt += "Available OpenStack Operations (for context on parameters and functions):\n"
        prompt += self._get_api_methods_formatted()
        prompt += "\nTask:\n"
        prompt += "1. Assess if the 'Function' and 'Parameters' accurately reflect the 'Original user query' and its intent.\n"
        prompt += "2. Identify if any critical parameters are implied by the query's intent but are missing from the 'Parameters' (even if not strictly 'required' by the function signature but good for fulfilling the user's goal).\n"
        prompt += "3. Determine if the parameter values seem plausible for the user's query.\n\n"
        prompt += "Please respond ONLY with a JSON object containing:\n"
        prompt += "{\n"
        prompt += '  "is_valid": <boolean>, // True if the command is a good reflection of the user query, False otherwise.\n'
        prompt += '  "feedback": "<string>", // Explanation if not valid, or suggestions for improvement. Empty if valid.\n'
        prompt += '  "missing_parameters_based_on_intent": ["<param1>", "<param2>"], // List of parameter names implied by query intent but missing from generated command.\n'
        prompt += '  "suggested_corrections": {"<parameter_name>": "<new_value>"} // Dictionary of suggested parameter corrections if values seem off or could be inferred better.\n'
        prompt += "}\n"
        prompt += "Example (if user query was 'Create a small web server with Ubuntu and 20GB disk' and generated command missed volume_size for create_server):\n"
        prompt += "{\n"
        prompt += '  "is_valid": false,\n'
        prompt += '  "feedback": "The user specified a 20GB disk, which implies \'volume_size\' parameter is needed for create_server to boot from a new volume of that size, but it\'s missing.",\n'
        prompt += '  "missing_parameters_based_on_intent": ["volume_size"],\n'
        prompt += '  "suggested_corrections": {"volume_size": 20}\n'
        prompt += "}\n\n"
        prompt += "Response JSON:"
        return prompt

    def _parse_json_response(self, response_text: str, context: str) -> Optional[Dict[str, Any]]:
        """Helper to parse JSON response from AI, with common fixes."""
        try:
            # Attempt to parse directly first
            return json.loads(response_text)
        except json.JSONDecodeError as e_initial:
            print(f"Initial JSON parse failed for {context}, attempting fixes: {e_initial}")
            
            # Stage 1: Extract content, potentially from markdown.
            # Use original response_text for extraction.
            text_after_markdown_extraction = response_text # Default if no markdown found
            
            # Ensure re is imported. (import re should be at the top of the file)
            match_json_block = re.search(r"```json\s*\n?(.*?)\n?\s*```", response_text, re.DOTALL)
            if match_json_block:
                text_after_markdown_extraction = match_json_block.group(1)
            else:
                match_generic_block = re.search(r"```\s*\n?(.*?)\n?\s*```", response_text, re.DOTALL)
                if match_generic_block:
                    text_after_markdown_extraction = match_generic_block.group(1)
            
            current_text_to_fix = text_after_markdown_extraction.strip()

            # Stage 2: Apply other specific fixes to 'current_text_to_fix'.
            # Fix 1: "parameters": "none"
            if '"parameters": "none"' in current_text_to_fix:
                current_text_to_fix = current_text_to_fix.replace('"parameters": "none"', '"parameters": {}')
            
            # Fix 2: Brace balancing (refined to be closer to original intent)
            if ('"parameters": {' in current_text_to_fix and
                current_text_to_fix.count('{') > current_text_to_fix.count('}')):
                braces_to_add = current_text_to_fix.count('{') - current_text_to_fix.count('}')
                current_text_to_fix = current_text_to_fix.rstrip() + '}' * braces_to_add
            
            # Stage 3: Attempt to parse the fixed text.
            try:
                return json.loads(current_text_to_fix)
            except json.JSONDecodeError as e_fix:
                print(f"Failed to parse JSON for {context} even after fixes: {e_fix}")
                print(f"Original problematic text for {context}: {response_text}")
                print(f"Attempted fixed text for {context} (after markdown strip and other fixes): {current_text_to_fix}") 
                return None

    def _generate_initial_command_with_ai(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Uses Gemini to parse the user query and returns the structured intent (Layer 1)."""
        if not self.model:
            print("AI model not available. Cannot parse query.")
            # Basic keyword matching as fallback?
            if "list servers" in user_query.lower(): return {"function_name": "list_servers", "parameters": {}}
            if "list images" in user_query.lower(): return {"function_name": "list_images", "parameters": {}}
            if any(phrase in user_query.lower() for phrase in ["list networks", "list all networks", "list my networks", "show networks", "display networks", "what networks are available", "available networks"]): 
                return {"function_name": "list_networks", "parameters": {}}
            # Add more basic fallbacks if needed
            return {"function_name": "clarify", "parameters": {}}

        prompt = self._generate_ai_prompt(user_query)
        print("\n--- Sending Prompt to Gemini (Layer 1: Command Generation) ---")
        # print(prompt) # Uncomment to debug the prompt
        print("--- End Prompt ---\n")

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            print(f"Gemini Raw Response (Layer 1): {response_text}")
            parsed_response = self._parse_json_response(response_text, "Layer 1 Command Generation")
            return parsed_response if parsed_response else {"function_name": "clarify", "parameters": {}}
        except Exception as e:
            print(f"Error interacting with Google AI (Layer 1): {e}")
            return {"function_name": "clarify", "parameters": {}}

    def _validate_command_with_ai(self, user_query: str, generated_command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Uses Gemini to validate the generated command against user intent (Layer 2)."""
        if not self.validation_model:
            print("AI validation model not available. Skipping validation.")
            return {"is_valid": True, "feedback": "Validation skipped.", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}

        prompt = self._generate_validation_prompt(user_query, generated_command)
        print("\n--- Sending Prompt to Gemini (Layer 2: Command Validation) ---")
        # print(prompt) # Uncomment to debug the prompt
        print("--- End Prompt ---\n")

        try:
            response = self.validation_model.generate_content(prompt)
            response_text = response.text.strip()
            print(f"Gemini Raw Response (Layer 2): {response_text}")
            parsed_validation = self._parse_json_response(response_text, "Layer 2 Validation")
            
            if parsed_validation and "is_valid" in parsed_validation:
                # Ensure all expected keys are present, with defaults if not
                parsed_validation.setdefault("feedback", "")
                parsed_validation.setdefault("missing_parameters_based_on_intent", [])
                parsed_validation.setdefault("suggested_corrections", {})
                return parsed_validation
            else:
                print("AI validation response was malformed or missing 'is_valid' field.")
                return {"is_valid": False, "feedback": "AI validation response was malformed.", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}
        except Exception as e:
            print(f"Error interacting with Google AI (Layer 2 Validation): {e}")
            return {"is_valid": False, "feedback": f"Error during AI validation: {e}", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}

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
        
    # Removed the first definition of _prompt_for_parameters as it was a duplicate.
    def _prompt_for_parameters(self, function_name: str, missing_params: Dict[str, Dict[str, Any]], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Prompts the user to provide values for missing parameters, allows 'default'."""
        collected_params = {}
        print("\nPlease provide the following information (or type 'default' for a pre-configured value if applicable):")
        for name, details in missing_params.items():
            while True:
                prompt_text = f"  - {name} (Type: {details['type']}): "
                value = input(prompt_text).strip()
                
                if value.lower() == 'default':
                    default_value = self.default_params_map.get(function_name, {}).get(name)
                    if default_value is not None:
                        print(f"    Using default value for '{name}': {default_value}")
                        collected_params[name] = default_value
                        break
                    else:
                        print(f"    No pre-configured default value for '{name}' in '{function_name}'. Please provide a specific value.")
                        # Continue loop to ask for specific value
                elif value: # User provided a specific value
                    collected_params[name] = value
                    break
                elif not details.get('required', True): # Parameter is not strictly required and user entered empty
                    print(f"    Skipping optional parameter '{name}'.")
                    # collected_params[name] = None # Or details.get('default') from API spec if that's desired behavior
                    break
                else: # Parameter is required and user entered empty
                    print("  Input cannot be empty for a required parameter.")
        return collected_params

    def execute_command(self, user_query: str):
        """Parses the user query using a two-layer AI system and executes the command."""
        
        # Layer 1: Initial command generation
        initial_intent = self._generate_initial_command_with_ai(user_query)

        if not initial_intent or initial_intent.get('function_name') == 'clarify':
            print("Could not understand the request or required clarification from Layer 1. Please try again with more details.")
            return

        print(f"\n--- Layer 1 (Initial Intent) ---")
        print(f"Function: {initial_intent.get('function_name')}")
        print(f"Parameters: {initial_intent.get('parameters')}")

        # Layer 2: Validation of the generated command
        validation_result = self._validate_command_with_ai(user_query, initial_intent)

        if not validation_result: # Should not happen if _validate_command_with_ai has robust fallbacks
            print("Critical error during AI validation. Aborting.")
            return

        print(f"\n--- Layer 2 (Validation Result) ---")
        print(f"Is Valid: {validation_result.get('is_valid')}")
        print(f"Feedback: {validation_result.get('feedback')}")
        print(f"Missing by Intent: {validation_result.get('missing_parameters_based_on_intent')}")
        print(f"Suggested Corrections: {validation_result.get('suggested_corrections')}")

        if not validation_result.get("is_valid", False):
            print(f"\nAI Validation (Layer 2) suggests the command may not be correct or complete.")
            print(f"Feedback: {validation_result.get('feedback', 'No specific feedback.')}")
            # For now, we'll proceed but flag it. Future: could re-prompt user or attempt auto-correction more intelligently.
            # If crucial parameters are missing by intent, we should try to collect them.
            # return # Or ask user for confirmation to proceed

        # Use the function and parameters from Layer 1, potentially modified by Layer 2's suggestions
        final_function_name = initial_intent['function_name']
        final_provided_params = initial_intent.get('parameters', {}).copy() # Use a copy

        # Apply AI suggested corrections (simple update, could be more sophisticated)
        if validation_result.get("suggested_corrections"):
            print(f"Applying Layer 2 suggested corrections: {validation_result.get('suggested_corrections')}")
            final_provided_params.update(validation_result.get("suggested_corrections"))

        # If Layer 1 produced 'clarify' but Layer 2 somehow validated it (unlikely), still treat as clarify.
        if final_function_name == 'clarify':
             print("Request requires clarification even after validation. Please try again with more details.")
             return

        # Special validation for volume creation (already present, adapt to final_provided_params)
        if final_function_name == 'create_volume' and 'size_gb' not in final_provided_params:
            print("Error: Volume creation requires 'size_gb' parameter. Please specify volume size.")
            # Potentially try to get it from missing_parameters_based_on_intent or prompt
            return

        if final_function_name not in self.api_methods:
            print(f"Error: The identified function '{final_function_name}' is not a valid OpenStack operation.")
            print("Available functions are:", list(self.api_methods.keys()))
            return

        # Check for missing required parameters (from signature AND from AI intent)
        missing_signature_params = self._get_missing_parameters(final_function_name, final_provided_params)
        
        # Add parameters identified by Layer 2 as missing due to intent, if they are actual params of the function
        intent_missing_params_names = validation_result.get("missing_parameters_based_on_intent", [])
        for p_name in intent_missing_params_names:
            if p_name not in final_provided_params and p_name in self.api_methods[final_function_name]['params']:
                # If it's a valid param for the function and not already provided, add to missing list
                if p_name not in missing_signature_params:
                     missing_signature_params[p_name] = self.api_methods[final_function_name]['params'][p_name]

        if missing_signature_params:
            print(f"\nMissing parameters for '{final_function_name}': {list(missing_signature_params.keys())}")
            
            if final_function_name == 'create_server' and 'network_name' in missing_signature_params:
                print("Tip: You can see available networks by running 'list networks' first.")
                
            additional_params = self._prompt_for_parameters(final_function_name, missing_signature_params, final_provided_params)
            final_provided_params.update(additional_params)
            
            # Re-check if still missing (user might have entered empty strings for required ones)
            still_missing_after_prompt = self._get_missing_parameters(final_function_name, final_provided_params)
            if still_missing_after_prompt:
                 print(f"Error: Still missing required parameters after prompting: {list(still_missing_after_prompt.keys())}. Aborting.")
                 return

        # Get the actual function object from OpenStackAPI
        func_to_call: Optional[Callable] = getattr(self.openstack_api, final_function_name, None)

        if not initial_intent or initial_intent['function_name'] == 'clarify': # Corrected parsed_intent to initial_intent
            print("Could not understand the request or required clarification. Please try again with more details.")
            return

        # This block is now handled above with final_function_name and final_provided_params
        # function_name = parsed_intent['function_name']
        # provided_params = parsed_intent.get('parameters', {})
        # This block is now handled above with final_function_name and final_provided_params

        if not func_to_call or not callable(func_to_call):
            print(f"Internal Error: Could not find callable method '{final_function_name}' in OpenStackAPI.")
            return

        # Special validation for create_server - network existence is handled by api.py's find_network.
        # The old check for 'list_networks' was incorrect here.

        # Special validation for volume creation - check size_gb exists and is valid type
        if final_function_name == 'create_volume':
            if 'size_gb' not in final_provided_params:
                print("Error: Volume creation requires 'size_gb' parameter. Please specify volume size.")
                # This should have been caught by missing parameter check ideally
                return
            if isinstance(final_provided_params['size_gb'], str):
                try:
                    size_str = ''.join(filter(str.isdigit, str(final_provided_params['size_gb'])))
                    if not size_str:
                        raise ValueError("Volume size must contain a numeric value")
                    final_provided_params['size_gb'] = int(size_str)
                    if final_provided_params['size_gb'] <= 0:
                        raise ValueError("Volume size must be greater than 0")
                except ValueError as e:
                    print(f"Error: Invalid volume size - {e}. Please provide a positive number (e.g., '10' for 10GB).")
                    return
            elif not isinstance(final_provided_params['size_gb'], int):
                 print(f"Error: Invalid type for volume size '{final_provided_params['size_gb']}'. Must be an integer.")
                 return
            elif final_provided_params['size_gb'] <= 0:
                 print(f"Error: Volume size must be greater than 0, got {final_provided_params['size_gb']}.")
                 return

        # Prepare arguments for the function call, ensuring correct types if possible
        final_args = {}
        sig = inspect.signature(func_to_call)
        for name, value in final_provided_params.items():
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
                 print(f"Warning: Parameter '{name}' provided but not expected by function '{final_function_name}'. Ignoring.")


        print(f"\n--- Executing {final_function_name} --- ")
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
                 print("Operation completed. It may have failed silently or returned no specific output. Check OpenStack logs if issues persist.")
            else:
                print(result)
            print("--- End Result ---")

        except Exception as e:
            print(f"\n--- Error during execution of {final_function_name} ---")
            print(f"Error: {e}")
            # Consider more specific error handling or re-raising certain exceptions
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