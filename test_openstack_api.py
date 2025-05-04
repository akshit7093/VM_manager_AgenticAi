import openstack
import os
import json
import time
from openstack_manager import (
    create_server as manager_create_server,
    delete_server as manager_delete_server,
    resize_server as manager_resize_server,
    create_volume as manager_create_volume,
    delete_volume as manager_delete_volume,
    manager_get_usage as manager_get_usage,
    create_network_with_subnet as manager_create_network_with_subnet
)

# OpenStack credentials (recommended to use environment variables)
OS_AUTH_URL = os.environ.get("OS_AUTH_URL", "https://api-ap-south-mum-1.openstack.acecloudhosting.com:5000/v3")
OS_USERNAME = os.environ.get("OS_USERNAME", "Hackathon_AIML_1")
OS_PASSWORD = os.environ.get("OS_PASSWORD", "Hackathon_AIML_1@567")
OS_PROJECT_NAME = os.environ.get("OS_PROJECT_NAME", "ACE_HACKATHON_AIML")
OS_PROJECT_ID = os.environ.get("OS_PROJECT_ID", "a02b14bcfca64e44bd68f2d00d8555b5")
OS_USER_DOMAIN_NAME = os.environ.get("OS_USER_DOMAIN_NAME", "Default")
OS_PROJECT_DOMAIN_NAME = os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default")

def connect_to_openstack():
    """Connects to OpenStack using openstacksdk."""
    try:
        print(f"Attempting to connect to OpenStack at: {OS_AUTH_URL}")
        conn = openstack.connect(
            auth_url=OS_AUTH_URL,
            project_name=OS_PROJECT_NAME,
            username=OS_USERNAME,
            password=OS_PASSWORD,
            user_domain_name=OS_USER_DOMAIN_NAME,
            project_domain_name=OS_PROJECT_DOMAIN_NAME,
        )
        print("Connection Successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to OpenStack: {e}")
        return None

def list_flavors(conn):
    """Lists available flavors to help user choose correctly."""
    print("\nAvailable flavors:")
    try:
        flavors = list(conn.compute.flavors())
        if flavors:
            for flavor in flavors:
                print(f"  - {flavor.name} (ID: {flavor.id}, RAM: {flavor.ram} MB, VCPUs: {flavor.vcpus}, Disk: {flavor.disk} GB)")
        else:
            print("  No flavors available.")
    except Exception as e:
        print(f"Error listing flavors: {e}")

if __name__ == "__main__":
    if any(val.startswith("YOUR_") or not val for val in [OS_AUTH_URL, OS_USERNAME, OS_PASSWORD, OS_PROJECT_NAME, OS_USER_DOMAIN_NAME, OS_PROJECT_DOMAIN_NAME]):
        print("\n*** WARNING: Please ensure OpenStack environment variables (OS_*) are set or update the script variables with your actual credentials! ***\n")
    else:
        conn = connect_to_openstack()
        if conn:
            print("\nSuccessfully connected to OpenStack using openstacksdk.")
            # List servers
            try:
                print("\nListing servers...")
                servers = list(conn.compute.servers())
                if servers:
                    for server in servers:
                        print(f"  - Server Name: {server.name}, ID: {server.id}, Status: {server.status}")
                else:
                    print("  No servers found.")
            except Exception as e:
                print(f"  Error listing servers: {e}")

            # List images
            try:
                print("\nListing images...")
                images = list(conn.image.images())
                if images:
                    for image in images:
                        print(f"  - Image Name: {image.name}, ID: {image.id}, Status: {image.status}")
                else:
                    print("  No images found.")
            except Exception as e:
                print(f"  Error listing images: {e}")

            # Create VM
            # Network creation step before VM creation
            print("\n--- Network Creation ---")
            network_name_to_create = input("Enter the name for the new private network (e.g., blue-net): ")
            subnet_cidr = input("Enter the subnet CIDR for the new network (default 192.168.100.0/24): ") or "192.168.100.0/24"
            print(f"\nCreating a private network called '{network_name_to_create}' with subnet {subnet_cidr}...")
            created_network, created_subnet = manager_create_network_with_subnet(conn, network_name_to_create, subnet_cidr=subnet_cidr)
            if created_network and created_subnet:
                print(f"Network '{created_network.name}' and subnet '{created_subnet.name}' created successfully.")
                network_name_to_use = created_network.name
            else:
                print("Failed to create network and subnet. Aborting VM creation.")
                network_name_to_use = None
            # Create VM only if network creation succeeded
            if network_name_to_use:
                print("\nAttempting to create a VM...")
                vm_name_to_create = "test-vm-from-script-new-007"
                image_name_to_use = "Ubuntu-24.04"
                flavor_name_to_use = "S.4"
                volume_size_gb = 10
                try:
                    created_server = manager_create_server(
                        conn,
                        vm_name_to_create,
                        image_name_to_use,
                        flavor_name_to_use,
                        network_name_to_use,
                        volume_size=volume_size_gb
                    )
                    if created_server:
                        print(f"\nVM creation initiated successfully:")
                        print(f"  - Name: {created_server.name}")
                        print(f"  - ID: {created_server.id}")
                        print(f"  - Status: {created_server.status}")
                        print("  Note: It might take some time for the VM to become fully ACTIVE.")
                    else:
                        print("\nVM creation failed. Check logs above for details.")
                except Exception as e:
                    print(f"\nError during VM creation attempt: {e}")
                    created_server = None
            else:
                created_server = None

            # Additional Operations
            created_volume = None
            if created_server:
                print("\nWaiting a bit before performing additional operations...")
                time.sleep(15)

                # Resize VM
                print("\nAttempting to resize the VM...")
                list_flavors(conn)
                resize_flavor_name = input("Enter the desired flavor name for resizing (e.g., S.5): ")
                try:
                    server_to_resize = conn.compute.get_server(created_server.id)
                    if server_to_resize and server_to_resize.status == 'ACTIVE':
                        resize_success = manager_resize_server(conn, server_to_resize, resize_flavor_name)
                        if resize_success:
                            print(f"  VM '{server_to_resize.name}' resize to '{resize_flavor_name}' initiated/completed.")
                            created_server = conn.compute.get_server(created_server.id)
                        else:
                            print(f"  VM '{server_to_resize.name}' resize failed. Check logs.")
                    elif server_to_resize:
                        print(f"  Skipping resize because server status is '{server_to_resize.status}', not ACTIVE.")
                    else:
                        print("  Skipping resize because server object could not be retrieved.")
                except Exception as e:
                    print(f"\nError during VM resize attempt: {e}")

                # Create Volume
                print("\nAttempting to create a standalone volume...")
                volume_name_to_create = input("Enter the name for the new standalone volume (e.g., data-disk): ")
                while True:
                    try:
                        new_volume_size_gb_str = input("Enter the size for the new standalone volume in GB (e.g., 100): ")
                        new_volume_size_gb = int(new_volume_size_gb_str)
                        if new_volume_size_gb <= 0:
                            print("Volume size must be a positive integer.")
                        else:
                            break
                    except ValueError:
                        print("Invalid input. Please enter a whole number for the volume size.")
                try:
                    created_volume = manager_create_volume(conn, volume_name_to_create, new_volume_size_gb)
                    if created_volume:
                        print(f"  Volume '{created_volume.name}' (ID: {created_volume.id}) created successfully.")
                    else:
                        print(f"  Volume creation failed. Check logs.")
                except Exception as e:
                    print(f"\nError during volume creation attempt: {e}")

                # Query Project Usage with Instance Details
                print("\nQuerying project and instance usage...")
                try:
                    # Pass the created server's ID to manager_get_usage to show its usage against project quotas
                    manager_get_usage(conn, server_id_or_name=created_server.id)
                except Exception as e:
                    print(f"\nError during usage query: {e}")

                # Delete Volume with Confirmation
                if created_volume:
                    confirm = input(f"\nDo you want to delete the volume '{created_volume.name}' (ID: {created_volume.id})? (yes/no): ")
                    if confirm.lower() == 'yes':
                        print(f"Attempting to delete the volume...")
                        try:
                            delete_vol_success = manager_delete_volume(conn, created_volume.id)
                            if delete_vol_success:
                                print(f"  Volume '{created_volume.name}' deletion initiated.")
                            else:
                                print(f"  Volume '{created_volume.name}' deletion failed. Check logs.")
                        except Exception as e:
                            print(f"\nError during volume deletion attempt: {e}")
                    else:
                        print("  Volume deletion skipped.")

            # Delete VM with Confirmation
            if created_server:
                confirm = input(f"\nDo you want to delete the VM '{created_server.name}' (ID: {created_server.id})? (yes/no): ")
                if confirm.lower() == 'yes':
                    print(f"Attempting to delete the VM...")
                    try:
                        delete_success = manager_delete_server(conn, created_server)
                        if delete_success:
                            print(f"  VM '{created_server.name}' deletion process completed.")
                        else:
                            print(f"  VM '{created_server.name}' deletion failed. Check logs.")
                    except Exception as e:
                        print(f"\nError during VM deletion attempt: {e}")
                else:
                    print("  VM deletion skipped.")
        else:
            print("\nFailed to connect to OpenStack.")