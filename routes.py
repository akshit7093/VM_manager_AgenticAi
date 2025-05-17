#!/usr/bin/env python3
"""
Backend routing for OpenStack Agent API.

This file sets up a Flask application to provide API endpoints
that allow a frontend to interact with the OpenStackAgent.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS # To handle Cross-Origin Resource Sharing
import sys
import os

# Add the parent directory to sys.path to allow imports from agent.py and api.py
# This is important if routes.py is run as the main script
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from agent import OpenStackAgent
except ImportError as e:
    print(f"Error importing OpenStackAgent: {e}")
    print("Please ensure agent.py is in the correct path and all dependencies are installed.")
    # Fallback or re-raise, depending on desired behavior if agent can't be imported
    # For now, let it proceed and potentially fail later if agent is None
    OpenStackAgent = None 

app = Flask(__name__)
CORS(app) # Enable CORS for all routes, allowing frontend requests from different origins

# Initialize the OpenStack Agent
# This assumes OpenStackAgent can be initialized without immediate connection issues
# or that its methods handle connection establishment internally.
if OpenStackAgent:
    openstack_agent = OpenStackAgent()
    # Attempt to connect the API within the agent if it has a connect method
    # and if it's not automatically done on init or first call
    if hasattr(openstack_agent, 'openstack_api') and hasattr(openstack_agent.openstack_api, 'connect'):
        if not openstack_agent.openstack_api.connect():
            print("Failed to connect to OpenStack via agent on startup.")
            # Decide how to handle this: app could run but commands will fail,
            # or prevent app from starting. For now, it will print and continue.
else:
    openstack_agent = None
    print("OpenStackAgent could not be initialized. API endpoints will not function correctly.")

@app.route('/api/command', methods=['POST'])
def handle_command():
    """Handles natural language commands to interact with OpenStack."""
    if not openstack_agent:
        return jsonify({'error': 'OpenStack Agent is not initialized. Cannot process command.'}), 500

    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query in request body'}), 400

    user_query = data['query']
    print(f"Received query: {user_query}")

    try:
        # Execute the command via the agent
        # Assumes execute_command will return a serializable result (dict, list, string, or None)
        command_output = openstack_agent.execute_command(user_query)
        
        # Check if the agent returned a missing parameters response
        if isinstance(command_output, dict) and command_output.get('status') == 'missing_parameters':
            print(f"Command requires missing parameters: {command_output.get('missing_params')}")
            return jsonify(command_output), 400 # Return 400 Bad Request for missing parameters

        # Prepare result based on the type of command_output
        if isinstance(command_output, list) and all(isinstance(item, dict) for item in command_output):
            # Format list of dictionaries into a readable string
            formatted_output = ""
            if command_output:
                # Assuming all dicts have the same keys, use keys from the first dict for header
                headers = command_output[0].keys()
                # Simple header line
                formatted_output += " | ".join(headers) + "\n"
                formatted_output += "-" * (len(" | ".join(headers)) + (len(headers) - 1) * 3) + "\n"
                # Data rows
                for item in command_output:
                    formatted_output += " | ".join(str(item.get(key, 'N/A')) for key in headers) + "\n"
            else:
                formatted_output = "Command executed successfully, returned an empty list."
            result = {'status': 'success', 'raw_output': formatted_output, 'output': []} # Use raw_output for formatted string
        elif isinstance(command_output, dict):
             # Format single dictionary into a readable string
            formatted_output = ""
            for key, value in command_output.items():
                formatted_output += f"{key}: {value}\n"
            result = {'status': 'success', 'raw_output': formatted_output, 'output': []}
        elif isinstance(command_output, str):
            # Check if the agent's execute_command returned an error string
            # A more robust approach would be for execute_command to raise exceptions for errors.
            if command_output.lower().startswith("error:") or "error:" in command_output.lower() or "failed:" in command_output.lower():
                print(f"Command execution returned an error string: {command_output}")
                # Return a 500 error if the agent indicates an error in its string output
                return jsonify({'error': command_output, 'status': 'agent_error'}), 500
            result = {'status': 'success', 'raw_output': command_output} # Single string output, use raw_output
        elif command_output is None:
            # This case implies the command ran but produced no specific output to return (e.g., a successful action with no data payload).
            result = {'status': 'success', 'raw_output': 'Command executed successfully with no output.'}
        else: 
            # Fallback for any other unexpected type, convert to string.
            # This might indicate an issue in execute_command's return contract.
            print(f"Warning: execute_command returned an unexpected type: {type(command_output)}. Converting to string.")
            result = {'status': 'success', 'raw_output': str(command_output)} # Use raw_output for fallback

        # Ensure 'output' is always an empty list or None if raw_output is used
        if 'raw_output' in result and 'output' not in result:
             result['output'] = []

        print(f"Command execution result: {result}")
        return jsonify(result), 200

        print(f"Command execution result: {result}")
        return jsonify(result), 200
    
    except Exception as e:
        # This will catch exceptions raised from within openstack_agent.execute_command
        # or other unexpected errors in this try block.
        print(f"Error processing command '{user_query}': {e}")
        import traceback
        traceback.print_exc() # Log the full traceback for server-side debugging
        # Provide a generic error message to the client
        error_message = f'An internal server error occurred while processing your request: {str(e)}'
        return jsonify({'error': error_message, 'status': 'server_error'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the status of the API and OpenStack connection."""
    if not openstack_agent or not hasattr(openstack_agent, 'openstack_api'):
        return jsonify({'status': 'error', 'message': 'OpenStack Agent not available.'}), 503
        
    api_conn_status = "Connected" if openstack_agent.openstack_api.conn else "Not Connected"
    return jsonify({
        'status': 'ok',
        'message': 'API is running.',
        'openstack_connection': api_conn_status
    }), 200

if __name__ == '__main__':
    # Note: For development, Flask's built-in server is fine.
    # For production, use a proper WSGI server like Gunicorn or uWSGI.
    print("Starting Flask development server for OpenStack Agent API...")
    app.run(debug=True, host='0.0.0.0', port=5000)