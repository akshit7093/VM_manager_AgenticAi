import openstack
import os
import time # Import time for waiting
from dotenv import load_dotenv
load_dotenv()
# --- Load OpenStack Credentials --- 
# It's recommended to use environment variables
OS_AUTH_URL = os.environ.get("OS_AUTH_URL")
OS_USERNAME = os.environ.get("OS_USERNAME")
OS_PASSWORD = os.environ.get("OS_PASSWORD")
OS_PROJECT_NAME = os.environ.get("OS_PROJECT_NAME")
OS_PROJECT_ID = os.environ.get("OS_PROJECT_ID")
OS_USER_DOMAIN_NAME = os.environ.get("OS_USER_DOMAIN_NAME")
OS_PROJECT_DOMAIN_NAME = os.environ.get("OS_PROJECT_DOMAIN_NAME")
# ------------------------------------

def connect_to_openstack():
    """Connects to OpenStack using credentials and returns a connection object."""
    try:
        # Optional: Enable logging for detailed debugging
        # openstack.enable_logging(debug=True)

        print(f"Attempting to connect to OpenStack at: {OS_AUTH_URL}")
        conn = openstack.connect(
            auth_url=OS_AUTH_URL,
            project_name=OS_PROJECT_NAME,
            username=OS_USERNAME,
            password=OS_PASSWORD,
            user_domain_name=OS_USER_DOMAIN_NAME,
            project_domain_name=OS_PROJECT_DOMAIN_NAME,
            # insecure=True # Uncomment if using self-signed certificates
        )
        print("OpenStack Connection Successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to OpenStack: {e}")
        # Consider raising the exception or handling it more robustly
        return None

# --- Placeholder Functions for OpenStack Actions ---

def list_servers(conn):
    """Lists all servers (VM instances) in the project."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return []
    try:
        print("Listing servers...")
        servers = list(conn.compute.servers())
        if not servers:
            print("No servers found.")
        return servers
    except Exception as e:
        print(f"Error listing servers: {e}")
        return []

def list_images(conn):
    """Lists available images."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return []
    try:
        print("Listing images...")
        images = list(conn.image.images())
        if not images:
            print("No images found.")
        return images
    except Exception as e:
        print(f"Error listing images: {e}")
        return []

def create_server(conn, name, image_name, flavor_name, network_name='default', volume_size=None): # Added volume_size
    """Creates a new server (VM instance), optionally booting from a volume."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return None
    try:
        print(f"Attempting to create server '{name}'...")

        # Find the image, flavor, and network by name
        image = conn.compute.find_image(image_name)
        flavor = conn.compute.find_flavor(flavor_name)
        network = conn.network.find_network(network_name)

        if not image:
            print(f"Error: Image '{image_name}' not found.")
            return None
        if not flavor:
            print(f"Error: Flavor '{flavor_name}' not found.")
            return None
        if not network:
             print(f"Error: Network '{network_name}' not found.")
             return None

        print(f"  Using Image: {image.id}")
        print(f"  Using Flavor: {flavor.id}")
        print(f"  Using Network: {network.id}")

        server_params = {
            'name': name,
            'flavor_id': flavor.id,
            'networks': [{"uuid": network.id}]
            # You might need to add key_name for SSH access:
            # 'key_name': 'your-keypair-name'
        }

        if volume_size:
            print(f"  Creating bootable volume of size {volume_size} GB from image {image.id}...")
            volume = conn.block_storage.create_volume(
                name=f"{name}-boot-volume",
                size=volume_size,
                imageRef=image.id,
                # bootable=True # Often implied by imageRef, but can be explicit
            )
            # Wait for volume to be available
            conn.block_storage.wait_for_status(volume, status='available', failures=['error'], interval=5, wait=300)
            print(f"  Volume {volume.id} created and available.")

            # Prepare block device mapping for booting from volume
            bdm = [
                {
                    'boot_index': '0',
                    'uuid': volume.id,
                    'source_type': 'volume',
                    'destination_type': 'volume',
                    'delete_on_termination': True # Or False if you want to keep the volume
                }
            ]
            server_params['block_device_mapping_v2'] = bdm
            # Do not specify image_id when booting from volume
        else:
            # Boot directly from image (original behavior)
            server_params['image_id'] = image.id

        # Create the server
        print(f"  Submitting server creation request...")
        server = conn.compute.create_server(**server_params)

        # Wait for the server to become active (optional, can take time)
        # server = conn.compute.wait_for_server(server)

        print(f"Server '{name}' creation initiated. ID: {server.id}, Status: {server.status}")
        return server

    except Exception as e:
        print(f"Error creating server '{name}': {e}")
        # Clean up volume if creation failed after volume was made
        if 'volume' in locals() and volume:
            try:
                print(f"  Attempting to delete volume {volume.id} due to server creation error...")
                conn.block_storage.delete_volume(volume)
            except Exception as ve:
                print(f"  Warning: Failed to delete volume {volume.id} after error: {ve}")
        return None

def delete_server(conn, server_to_delete):
    """Deletes a server (VM instance) given its object or ID."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return False

    server_id = None
    server_name = "Unknown"
    if isinstance(server_to_delete, str):
        server_id = server_to_delete
        # Try to find the server to get its name for logging
        try:
            found_server = conn.compute.find_server(server_id)
            if found_server:
                server_name = found_server.name
        except Exception:
            pass # Ignore if finding fails, proceed with deletion by ID
    elif hasattr(server_to_delete, 'id') and hasattr(server_to_delete, 'name'):
        server_id = server_to_delete.id
        server_name = server_to_delete.name
    else:
        print("Error: Invalid input for server_to_delete. Provide server object or ID string.")
        return False

    print(f"Attempting to delete server '{server_name}' (ID: {server_id})...")
    try:
        # The 'wait' parameter is not valid for conn.compute.delete_server
        # Deletion is inherently asynchronous in the SDK call itself.
        # If waiting is needed, it should be implemented separately by polling the server status.
        conn.compute.delete_server(server_id)
        print(f"Server '{server_name}' (ID: {server_id}) deleted successfully.")
        return True
    except openstack.exceptions.ResourceNotFound:
        print(f"Server '{server_name}' (ID: {server_id}) not found. Perhaps already deleted?")
        return True # Consider it success if not found
    except Exception as e:
        print(f"Error deleting server '{server_name}' (ID: {server_id}): {e}")
        return False

# --- New Functions ---

def create_network_with_subnet(conn, network_name, subnet_cidr="192.168.100.0/24", subnet_name=None):
    """Creates a private network and subnet, returns network and subnet objects."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return None, None
    try:
        print(f"Creating network '{network_name}'...")
        network = conn.network.create_network(name=network_name)
        print(f"  Network created: ID={network.id}, Name={network.name}")
        if not subnet_name:
            subnet_name = f"{network_name}-subnet"
        print(f"Creating subnet '{subnet_name}' with CIDR {subnet_cidr}...")
        subnet = conn.network.create_subnet(
            name=subnet_name,
            network_id=network.id,
            ip_version=4,
            cidr=subnet_cidr,
            enable_dhcp=True
        )
        print(f"  Subnet created: ID={subnet.id}, Name={subnet.name}, CIDR={subnet.cidr}")
        return network, subnet
    except Exception as e:
        print(f"Error creating network or subnet: {e}")
        return None, None

def resize_server(conn, server, flavor_name):
    """Resizes a server to a new flavor and confirms the resize."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return False
    try:
        print(f"Attempting to resize server '{server.name}' (ID: {server.id}) to flavor '{flavor_name}'...")
        flavor = conn.compute.find_flavor(flavor_name)
        if not flavor:
            print(f"Error: Flavor '{flavor_name}' not found.")
            return False

        print(f"  Found target flavor: {flavor.id}")
        conn.compute.resize_server(server, flavor.id)

        # Wait for the server to reach VERIFY_RESIZE status
        print("  Waiting for server to reach VERIFY_RESIZE status...")
        conn.compute.wait_for_server(server, status='VERIFY_RESIZE', failures=['ERROR'], interval=5, wait=600)
        print(f"  Server '{server.name}' is ready for resize confirmation.")

        # Confirm the resize
        print("  Confirming resize...")
        conn.compute.confirm_server_resize(server)

        # Optional: Wait for the server to become ACTIVE again after confirmation
        # print("  Waiting for server to become ACTIVE after resize...")
        # conn.compute.wait_for_server(server, status='ACTIVE', failures=['ERROR'], interval=5, wait=300)

        print(f"Server '{server.name}' successfully resized to flavor '{flavor_name}'.")
        return True

    except Exception as e:
        print(f"Error resizing server '{server.name}': {e}")
        # Attempt to revert resize if possible (might not always work depending on state)
        try:
            print("  Attempting to revert resize...")
            conn.compute.revert_server_resize(server)
        except Exception as re:
            print(f"  Warning: Failed to revert resize: {re}")
        return False

def create_volume(conn, name, size_gb):
    """Creates a standalone Cinder volume."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return None
    try:
        print(f"Attempting to create volume '{name}' of size {size_gb} GB...")
        volume = conn.block_storage.create_volume(
            name=name,
            size=size_gb
            # Add other options like volume_type if needed
            # 'volume_type': 'your_volume_type'
        )
        # Wait for the volume to become available
        print(f"  Waiting for volume '{name}' (ID: {volume.id}) to become available...")
        conn.block_storage.wait_for_status(volume, status='available', failures=['error'], interval=5, wait=300)
        print(f"Volume '{name}' (ID: {volume.id}) created successfully.")
        return volume
    except Exception as e:
        print(f"Error creating volume '{name}': {e}")
        return None

def delete_volume(conn, volume_name_or_id):
    """Deletes a standalone Cinder volume by name or ID."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return False
    try:
        print(f"Attempting to find volume '{volume_name_or_id}' for deletion...")
        volume = conn.block_storage.find_volume(volume_name_or_id, ignore_missing=False)
        if not volume:
             # find_volume raises ResourceNotFound if ignore_missing=False and not found
             # This part might not be reached if ResourceNotFound is caught below
             print(f"Error: Volume '{volume_name_or_id}' not found.")
             return False

        print(f"  Found volume '{volume.name}' (ID: {volume.id}). Attempting deletion...")
        conn.block_storage.delete_volume(volume)
        # Optional: Wait for deletion confirmation (volume status becomes 'deleting' then disappears)
        # try:
        #     conn.block_storage.wait_for_delete(volume, interval=2, wait=120)
        #     print(f"  Volume '{volume.name}' deletion confirmed.")
        # except openstack.exceptions.ResourceNotFound:
        #     print(f"  Volume '{volume.name}' deletion confirmed (not found after delete call).")
        # except Exception as we:
        #     print(f"  Warning: Error waiting for volume deletion confirmation: {we}")

        print(f"Volume '{volume.name}' (ID: {volume.id}) deletion initiated successfully.")
        return True
    except openstack.exceptions.ResourceNotFound:
        print(f"Volume '{volume_name_or_id}' not found. Perhaps already deleted?")
        return True # Consider it success if not found
    except Exception as e:
        print(f"Error deleting volume '{volume_name_or_id}': {e}")
        return False

# manager_module.py
import openstack

def manager_get_usage(conn, server_id_or_name=None):
    """Prints usage for a specific server alongside overall project quotas & usage."""
    if not conn:
        print("Error: Not connected to OpenStack.")
        return

    # First, fetch project limits
    limits = conn.compute.get_limits().absolute
    # We're interested in these five main resources:
    pu = {
        'cores':    ('totalCoresUsed', 'maxTotalCores'),
        'ram (MB)': ('totalRAMUsed', 'maxTotalRAMSize'),
        'instances':('totalInstancesUsed', 'maxTotalInstances'),
        'volumes':  ('totalVolumesUsed', 'maxTotalVolumes'),
        'gigabytes':('totalGigabytesUsed', 'maxTotalVolumeGigabytes'),
    }

    # If server was specified, show instance details first
    if server_id_or_name:
        print(f"\n--- Usage for Instance: {server_id_or_name} ---")
        server = conn.compute.find_server(server_id_or_name)
        if not server:
            print(f"  Server '{server_id_or_name}' not found.\n")
        else:
            server = conn.compute.get_server(server.id)
            print(f"  Name:   {server.name}")
            print(f"  ID:     {server.id}")
            print(f"  Status: {server.status}")
            # Flavor info
            flavor_id   = server.flavor['id']
            try:
                flavor = conn.compute.get_flavor(flavor_id)
                print(f"  Flavor: {flavor.name} (ID: {flavor.id})")
                print(f"    vCPUs:      {flavor.vcpus}")
                print(f"    RAM:        {flavor.ram} MB")
                print(f"    Root Disk:  {flavor.disk} GB")
            except Exception:
                print(f"  Flavor ID: {flavor_id} (details unavailable)")

            # Attached volumes
            if server.attached_volumes:
                print("  Attached Volumes:")
                for att in server.attached_volumes:
                    vol = conn.block_storage.get_volume(att['id'])
                    print(f"    - {vol.name} (ID: {vol.id}): {vol.size} GB, status={vol.status}")
            else:
                print("  No volumes attached.")

    # Now show project quotas vs usage
    print("\n--- Project Quotas & Current Usage ---")
    for label, (used_key, max_key) in pu.items():
        used = limits.get(used_key, 'N/A')
        quota = limits.get(max_key, 'N/A')
        print(f"  {label:10}: {used} / {quota}")



# Example usage (for testing this module directly)
if __name__ == "__main__":
    print("Testing OpenStack Manager Module...")
    connection = connect_to_openstack()
    if connection:
        print("\n--- Testing Server Listing ---")
        list_servers(connection)

        print("\n--- Testing Image Listing ---")
        list_images(connection)

        print("\n--- Testing Usage Query ---")
        get_project_usage(connection)

        # Add tests for new functions here if desired, e.g.:
        # print("\n--- Testing Volume Creation ---")
        # test_vol = create_volume(connection, "test-manager-vol", 1)
        # if test_vol:
        #     print("\n--- Testing Volume Deletion ---")
        #     delete_volume(connection, test_vol.id)
        print("\n--- Testing Image Listing ---")
        list_images(connection)
        # print("\n--- Testing Server Creation (Example - Disabled by default) ---")
        # create_server(connection, 'test-from-manager', 'Ubuntu-22.04-LTS', 'standard.small') # Replace with valid names
    else:
        print("Failed to establish OpenStack connection.")