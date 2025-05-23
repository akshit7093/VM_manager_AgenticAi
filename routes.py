#!/usr/bin/env python3
"""
Backend routing for OpenStack Agent API.

This file sets up a Flask application to provide API endpoints
that allow a frontend to interact with the OpenStackAgent.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import uuid

# Add the parent directory to sys.path to allow imports from agent.py and api.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from agent import OpenStackAgent
except ImportError as e:
    print(f"Error importing OpenStackAgent: {e}")
    print("Please ensure agent.py is in the correct path and all dependencies are installed.")
    OpenStackAgent = None

app = Flask(__name__)
CORS(app)

# Initialize the OpenStack Agent
if OpenStackAgent:
    openstack_agent = OpenStackAgent()
    if hasattr(openstack_agent, 'openstack_api') and hasattr(openstack_agent.openstack_api, 'connect'):
        if not openstack_agent.openstack_api.connect():
            print("Failed to connect to OpenStack via agent on startup.")
            openstack_agent = None
else:
    openstack_agent = None
    print("OpenStackAgent could not be initialized. API endpoints will not function correctly.")

# In-memory store for pending confirmations
pending_confirmations = {}

@app.route('/api/command', methods=['POST'])
def handle_command():
    """Handles natural language commands to interact with OpenStack."""
    if not openstack_agent:
        return jsonify({
            'error': 'OpenStack Agent is not initialized or failed to connect to OpenStack. Please check the connection and try again.',
            'status': 'connection_error'
        }), 503

    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query in request body'}), 400

    user_query = data['query']
    params = data.get('params', {})
    print(f"Received query: {user_query}, params: {params}")

    try:
        # Check if this is a confirmation response
        if params.get('confirmation_id') and params.get('confirmed') is True:
            # Retrieve the pending command
            confirmation_id = params.get('confirmation_id')
            if confirmation_id not in pending_confirmations:
                return jsonify({
                    'error': 'Invalid or expired confirmation ID.',
                    'status': 'invalid_confirmation'
                }), 400

            # Get the command/action to execute (this was stored from the agent's initial assessment)
            action_to_execute = pending_confirmations[confirmation_id]

            # Directly execute the pre-vetted action.
            # It's assumed that process_user_query(action_to_execute) will execute it
            # without requiring further interactive confirmation if action_to_execute
            # was what the agent provided as 'action_details' or was the original user_query.
            command_output = openstack_agent.process_user_query(action_to_execute)

            # Remove from pending confirmations after processing
            pending_confirmations.pop(confirmation_id)

        else:


            # Execute the initial command
            command_output = openstack_agent.process_user_query(user_query)

        # Handle different response types from the agent
        if isinstance(command_output, dict):
            if command_output.get('status') == 'confirmation_required':
                confirmation_id = str(uuid.uuid4())
                # Store the specific action details from the agent if available, otherwise fallback to user_query.
                # This 'executable_action' is what will be run if user confirms.
                executable_action = command_output.get('action_details', user_query)
                pending_confirmations[confirmation_id] = executable_action
                
                # For display on the frontend, use agent's action_details or a message based on user_query.
                display_action_details = command_output.get('action_details', f'Execute command based on: "{user_query}"')
                
                return jsonify({
                    'status': 'confirmation_required_popup',  # Signal frontend for UI confirmation
                    'action_details': display_action_details,
                    'confirmation_id': confirmation_id,
                    'message': command_output.get('message', 'This action requires confirmation. Please use the popup.')
                }), 200

            if command_output.get('status') == 'missing_parameters':
                print(f"Command requires missing parameters: {command_output.get('missing_params')}")
                return jsonify(command_output), 400

            formatted_lines = []
            for key, value in command_output.items():
                if isinstance(value, dict):
                    nested_items = [f"{k}: {v}" for k, v in value.items()]
                    formatted_lines.append(f"{key}: {', '.join(nested_items)}")
                else:
                    formatted_lines.append(f"{key}: {value}")
            result = {'status': 'success', 'output': formatted_lines}

        elif isinstance(command_output, list) and all(isinstance(item, dict) for item in command_output):
            formatted_lines = []
            if not command_output:
                formatted_lines.append("No servers found.")
            else:
                for server_dict in command_output:
                    line_parts = []
                    if 'name' in server_dict:
                        line_parts.append(f"Name: {server_dict['name']}")
                    if 'id' in server_dict:
                        line_parts.append(f"ID: {server_dict['id']}")
                    if 'status' in server_dict:
                        line_parts.append(f"Status: {server_dict['status']}")
                    networks = server_dict.get('networks')
                    if isinstance(networks, dict) and networks:
                        network_details_str = []
                        for net_name, ips_list in networks.items():
                            if isinstance(ips_list, list) and ips_list:
                                network_details_str.append(f"{net_name}: {ips_list[0]}")
                        if network_details_str:
                            line_parts.append(f"Networks: {'; '.join(network_details_str)}")
                    formatted_lines.append(", ".join(line_parts))
            result = {'status': 'success', 'output': formatted_lines}

        elif isinstance(command_output, str):
            if (command_output.lower().startswith("error:") or
                "error:" in command_output.lower() or
                "failed:" in command_output.lower()):
                print(f"Command execution returned an error string: {command_output}")
                return jsonify({'error': command_output, 'status': 'agent_error'}), 500
            result = {'status': 'success', 'raw_output': command_output}

        elif command_output is None:
            result = {'status': 'success', 'raw_output': 'Command executed successfully with no output.'}

        else:
            print(f"Warning: execute_command returned an unexpected type: {type(command_output)}. Converting to string.")
            result = {'status': 'success', 'raw_output': str(command_output)}

        if 'raw_output' in result and 'output' not in result:
            result['output'] = []

        print(f"Command execution result: {result}")
        return jsonify({'result': result}), 200

    except Exception as e:
        print(f"Error processing command '{user_query}': {e}")
        import traceback
        traceback.print_exc()
        error_message = f'An internal server error occurred while processing your request: {str(e)}'
        return jsonify({'error': error_message, 'status': 'server_error'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the status of the API and OpenStack connection."""
    if not openstack_agent or not hasattr(openstack_agent, 'openstack_api'):
        return jsonify({'status': 'error', 'message': 'OpenStack Agent not available or failed to connect.'}), 503

    api_conn_status = "Connected" if openstack_agent.openstack_api.conn else "Not Connected"
    return jsonify({
        'status': 'ok',
        'message': 'API is running.',
        'openstack_connection': api_conn_status
    }), 200

if __name__ == '__main__':
    print("Starting Flask development server for OpenStack Agent API...")
    app.run(debug=True, host='0.0.0.0', port=5000)