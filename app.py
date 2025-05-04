from flask import Flask, request, jsonify
import os

# Import OpenStack connection logic
from openstack_manager import connect_to_openstack, create_server

app = Flask(__name__)

# Initialize OpenStack connection once
openstack_conn = connect_to_openstack()

@app.route('/')
def home():
    return "OpenStack Agent is running!"

@app.route('/create_vm', methods=['POST'])
def handle_create_vm():
    """Handles VM creation requests based on form/JSON data."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data in request body'}), 400

    # Extract required parameters
    vm_name = data.get('name')
    image_name = data.get('image_name')
    flavor_name = data.get('flavor_name')
    network_name = data.get('network_name', 'default') # Default network if not provided
    volume_size = data.get('volume_size') # Optional volume size (can be None)

    if not all([vm_name, image_name, flavor_name]):
        return jsonify({'error': 'Missing required parameters: name, image_name, flavor_name'}), 400

    print(f"Received request to create VM: Name={vm_name}, Image={image_name}, Flavor={flavor_name}, Network={network_name}, VolumeSize={volume_size or 'N/A'}")

    if not openstack_conn:
        return jsonify({'error': 'OpenStack connection not available'}), 503 # Service Unavailable

    try:
        # Pass volume_size to create_server (it handles None correctly)
        server = create_server(openstack_conn, vm_name, image_name, flavor_name, network_name, volume_size=volume_size)
        if server:
            # Note: Server creation is initiated, might not be fully 'ACTIVE' yet.
            response_message = f"Successfully initiated creation of VM: {server.name} (ID: {server.id}, Status: {server.status})"
            return jsonify({'response': response_message}), 202 # Accepted
        else:
            # create_server handles internal errors and prints them, return a generic server error
            return jsonify({'error': 'Failed to initiate VM creation. Check server logs for details.'}), 500
    except Exception as e:
        print(f"Unhandled exception during VM creation: {e}") # Log the exception
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

if __name__ == '__main__':
    # Use environment variable for port or default to 5001
    port = int(os.environ.get('PORT', 5001))
    # Run on 0.0.0.0 to be accessible externally if needed, debug=True for development
    app.run(host='0.0.0.0', port=port, debug=True)