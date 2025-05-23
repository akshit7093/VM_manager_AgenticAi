#!/usr/bin/env python3
"""
OpenStack API Integration Module

This module combines functionality from test_openstack_api.py and openstack_manager.py
to provide a unified, dynamic API for OpenStack operations with user prompts.
"""

import openstack
import os
import time
from typing import Optional, Tuple, Dict, Any, List

# --- Load OpenStack Credentials ---
# It's recommended to use environment variables
OS_AUTH_URL = os.environ.get("OS_AUTH_URL", "https://api-ap-south-mum-1.openstack.acecloudhosting.com:5000/v3")
OS_USERNAME = os.environ.get("OS_USERNAME", "Hackathon_AIML_1")
OS_PASSWORD = os.environ.get("OS_PASSWORD", "Hackathon_AIML_1@567")
OS_PROJECT_NAME = os.environ.get("OS_PROJECT_NAME", "ACE_HACKATHON_AIML")
OS_PROJECT_ID = os.environ.get("OS_PROJECT_ID", "a02b14bcfca64e44bd68f2d00d8555b5")
OS_USER_DOMAIN_NAME = os.environ.get("OS_USER_DOMAIN_NAME", "Default")
OS_PROJECT_DOMAIN_NAME = os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default")


class OpenStackAPI:
    """Main API class for OpenStack operations."""
    
    def __init__(self):
        """Initialize the OpenStack connection."""
        self.conn = None
    
    def connect(self) -> bool:
        """Connect to OpenStack and return connection status."""
        try:
            print(f"Attempting to connect to OpenStack at: {OS_AUTH_URL}")
            self.conn = openstack.connect(
                auth_url=OS_AUTH_URL,
                project_name=OS_PROJECT_NAME,
                username=OS_USERNAME,
                password=OS_PASSWORD,
                user_domain_name=OS_USER_DOMAIN_NAME,
                project_domain_name=OS_PROJECT_DOMAIN_NAME,
            )
            print("OpenStack Connection Successful!")
            return True
        except Exception as e:
            print(f"Error connecting to OpenStack: {e}")
            return False
    
    def _ensure_connection(self) -> bool:
        """Ensure we have an active connection."""
        if not self.conn:
            return self.connect()
        return True
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """List all servers (VM instances) in the project."""
        if not self._ensure_connection():
            return []
        
        try:
            print("Listing servers...")
            servers = list(self.conn.compute.servers())
            result = []
            for server in servers:
                server_details = {
                    'id': server.id,
                    'name': server.name,
                    'status': server.status,
                    'created': server.created_at if hasattr(server, 'created_at') else None,
                    'flavor': getattr(server, 'flavor', {}),
                    'image': getattr(server, 'image', {}),
                    'networks': getattr(server, 'networks', {})
                }
                result.append(server_details)
            if not result:
                print("No servers found.")
            return result
        except Exception as e:
            print(f"Error listing servers: {e}")
            return []
    
    def list_images(self) -> List[Dict[str, Any]]:
        """List available images."""
        if not self._ensure_connection():
            return []
        
        try:
            print("Listing images...")
            images = list(self.conn.image.images())
            result = []
            for image in images:
                result.append({
                    'id': image.id,
                    'name': image.name,
                    'status': image.status,
                    'size': image.size,
                    'created_at': image.created_at
                })
            if not result:
                print("No images found.")
            return result
        except Exception as e:
            print(f"Error listing images: {e}")
            return []
    
    def list_flavors(self) -> List[Dict[str, Any]]:
        """List available flavors."""
        if not self._ensure_connection():
            return []
        
        try:
            print("Listing flavors...")
            flavors = list(self.conn.compute.flavors())
            result = []
            for flavor in flavors:
                result.append({
                    'id': flavor.id,
                    'name': flavor.name,
                    'vcpus': flavor.vcpus,
                    'ram': flavor.ram,
                    'disk': flavor.disk,
                    'is_public': flavor.is_public
                })
            if not result:
                print("No flavors found.")
            return result
        except Exception as e:
            print(f"Error listing flavors: {e}")
            return []
    
    def list_networks(self) -> List[Dict[str, Any]]:
        """List available networks."""
        if not self._ensure_connection():
            return []
        
        try:
            print("Listing networks...")
            networks = list(self.conn.network.networks())
            result = []
            for network in networks:
                result.append({
                    'id': network.id,
                    'name': network.name,
                    'status': network.status,
                    'subnets': network.subnet_ids
                })
            if not result:
                print("No networks found.")
            return result
        except Exception as e:
            print(f"Error listing networks: {e}")
            return []
    
    def list_volumes(self) -> List[Dict[str, Any]]:
        """List available volumes."""
        if not self._ensure_connection():
            return []
        
        try:
            print("Listing volumes...")
            volumes = list(self.conn.block_storage.volumes())
            result = []
            for volume in volumes:
                result.append({
                    'id': volume.id,
                    'name': volume.name,
                    'status': volume.status,
                    'size': volume.size,
                    'attachments': volume.attachments
                })
            if not result:
                print("No volumes found.")
            return result
        except Exception as e:
            print(f"Error listing volumes: {e}")
            return []
    
    def create_server(self, 
                     name: str, 
                     image_name: str, 
                     flavor_name: str, 
                     network_name: str = 'default', 
                     volume_size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new server (VM instance).
        
        Args:
            name: Name of the server to create
            image_name: Name of the image to use
            flavor_name: Name of the flavor to use
            network_name: Name of the network to attach to
            volume_size: Size of boot volume in GB (optional)
        
        Returns:
            Dictionary with server details or None if failed
        """
        if not self._ensure_connection():
            return None
        
        try:
            print(f"Attempting to create server '{name}'...")

            # Find the image, flavor, and network by name
            image = self.conn.compute.find_image(image_name)
            flavor = self.conn.compute.find_flavor(flavor_name)
            network = self.conn.network.find_network(network_name)

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
            }

            if volume_size:
                print(f"  Creating bootable volume of size {volume_size} GB from image {image.id}...")
                volume = self.conn.block_storage.create_volume(
                    name=f"{name}-boot-volume",
                    size=volume_size,
                    imageRef=image.id,
                )
                self.conn.block_storage.wait_for_status(volume, status='available', 
                                                      failures=['error'], interval=5, wait=300)
                print(f"  Volume {volume.id} created and available.")

                bdm = [
                    {
                        'boot_index': '0',
                        'uuid': volume.id,
                        'source_type': 'volume',
                        'destination_type': 'volume',
                        'delete_on_termination': True
                    }
                ]
                server_params['block_device_mapping_v2'] = bdm
            else:
                server_params['image_id'] = image.id

            print(f"  Submitting server creation request...")
            server = self.conn.compute.create_server(**server_params)

            print(f"Server '{name}' creation initiated. ID: {server.id}, Status: {server.status}")
            return {
                'id': server.id,
                'name': server.name,
                'status': server.status,
                'image': image_name,
                'flavor': flavor_name,
                'network': network_name,
                'volume_size': volume_size
            }

        except Exception as e:
            print(f"Error creating server '{name}': {e}")
            if 'volume' in locals() and volume:
                try:
                    print(f"  Attempting to delete volume {volume.id} due to server creation error...")
                    self.conn.block_storage.delete_volume(volume)
                except Exception as ve:
                    print(f"  Warning: Failed to delete volume {volume.id} after error: {ve}")
            return None
    
    def delete_server(self, server_id_or_name: str) -> bool:
        """
        Delete a server (VM instance).
        
        Args:
            server_id_or_name: ID or name of the server to delete
        
        Returns:
            True if deletion was successful or server not found, False otherwise
        """
        if not self._ensure_connection():
            return False
        
        server_id = None
        server_name = "Unknown"
        
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            if not server:
                print(f"Server '{server_id_or_name}' not found. Perhaps already deleted?")
                return True
            
            server_id = server.id
            server_name = server.name
            
            print(f"Attempting to delete server '{server_name}' (ID: {server_id})...")
            self.conn.compute.delete_server(server_id)
            print(f"Server '{server_name}' (ID: {server_id}) deleted successfully.")
            return True
        except openstack.exceptions.ResourceNotFound:
            print(f"Server '{server_id_or_name}' not found. Perhaps already deleted?")
            return True
        except Exception as e:
            print(f"Error deleting server '{server_name}' (ID: {server_id}): {e}")
            return False
    
    def resize_server(self, server_id_or_name: str, flavor_name: str) -> bool:
        """
        Resize a server to a new flavor.
        
        Args:
            server_id_or_name: ID or name of the server to resize
            flavor_name: Name of the new flavor to use
        
        Returns:
            True if resize was successful, False otherwise
        """
        if not self._ensure_connection():
            return False
        
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            if not server:
                print(f"Server '{server_id_or_name}' not found.")
                return False
            
            print(f"Attempting to resize server '{server.name}' (ID: {server.id}) to flavor '{flavor_name}'...")
            flavor = self.conn.compute.find_flavor(flavor_name)
            if not flavor:
                print(f"Error: Flavor '{flavor_name}' not found.")
                return False

            print(f"  Found target flavor: {flavor.id}")
            self.conn.compute.resize_server(server, flavor.id)

            print("  Waiting for server to reach VERIFY_RESIZE status...")
            self.conn.compute.wait_for_server(server, status='VERIFY_RESIZE', 
                                            failures=['ERROR'], interval=5, wait=600)
            print(f"  Server '{server.name}' is ready for resize confirmation.")

            print("  Confirming resize...")
            self.conn.compute.confirm_server_resize(server)

            print(f"Server '{server.name}' successfully resized to flavor '{flavor_name}'.")
            return True

        except Exception as e:
            print(f"Error resizing server '{server_id_or_name}': {e}")
            if 'server' in locals() and server:
                try:
                    print("  Attempting to revert resize...")
                    self.conn.compute.revert_server_resize(server)
                except Exception as re:
                    print(f"  Warning: Failed to revert resize: {re}")
            return False
    
    def create_volume(self, name: str, size_gb: int) -> Optional[Dict[str, Any]]:
        """
        Create a standalone volume.
        
        Args:
            name: Name of the volume to create
            size_gb: Size of the volume in GB
        
        Returns:
            Dictionary with volume details or None if failed
        """
        if not self._ensure_connection():
            return None
        
        try:
            print(f"Attempting to create volume '{name}' of size {size_gb} GB...")
            volume = self.conn.block_storage.create_volume(
                name=name,
                size=size_gb
            )
            
            print(f"  Waiting for volume '{name}' (ID: {volume.id}) to become available...")
            self.conn.block_storage.wait_for_status(volume, status='available', 
                                                  failures=['error'], interval=5, wait=300)
            print(f"Volume '{name}' (ID: {volume.id}) created successfully.")
            return {
                'id': volume.id,
                'name': volume.name,
                'size': volume.size,
                'status': volume.status
            }
        except Exception as e:
            print(f"Error creating volume '{name}': {e}")
            return None
    
    def delete_volume(self, volume_id_or_name: str) -> bool:
        """
        Delete a volume.
        
        Args:
            volume_id_or_name: ID or name of the volume to delete
        
        Returns:
            True if deletion was successful or volume not found, False otherwise
        """
        if not self._ensure_connection():
            return False
        
        try:
            volume = self.conn.block_storage.find_volume(volume_id_or_name, ignore_missing=False)
            print(f"  Found volume '{volume.name}' (ID: {volume.id}). Attempting deletion...")
            self.conn.block_storage.delete_volume(volume)
            print(f"Volume '{volume.name}' (ID: {volume.id}) deletion initiated successfully.")
            return True
        except openstack.exceptions.ResourceNotFound:
            print(f"Volume '{volume_id_or_name}' not found. Perhaps already deleted?")
            return True
        except Exception as e:
            print(f"Error deleting volume '{volume_id_or_name}': {e}")
            return False
    
    def create_network_with_subnet(self, network_name: str, 
                                 subnet_cidr: str = "192.168.100.0/24", 
                                 subnet_name: Optional[str] = None) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Create a network with subnet.
        
        Args:
            network_name: Name of the network to create
            subnet_cidr: CIDR for the subnet (default: 192.168.100.0/24)
            subnet_name: Name of the subnet (default: network_name + "-subnet")
        
        Returns:
            Tuple of (network_details, subnet_details) or None if failed
        """
        if not self._ensure_connection():
            return None
        
        try:
            if not subnet_name:
                subnet_name = f"{network_name}-subnet"
                
            print(f"Creating network '{network_name}' with subnet '{subnet_name}'...")
            network = self.conn.network.create_network(name=network_name)
            subnet = self.conn.network.create_subnet(
                name=subnet_name,
                network_id=network.id,
                ip_version=4,
                cidr=subnet_cidr,
                enable_dhcp=True
            )
            
            network_details = {
                'id': network.id,
                'name': network.name,
                'status': network.status
            }
            
            subnet_details = {
                'id': subnet.id,
                'name': subnet.name,
                'cidr': subnet.cidr,
                'network_id': subnet.network_id
            }
            
            return network_details, subnet_details
        except Exception as e:
            print(f"Error creating network or subnet: {e}")
            return None
    
    def get_usage(self, server_id_or_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics for the project and optionally a specific server.
        
        Args:
            server_id_or_name: Optional server ID or name to get specific usage
        
        Returns:
            - No identifier: returns dict with 'project_usage' and 'servers_usage' list.
            - 'project'/'project_usage': returns {'project_usage': ...}.
            - Matching server: returns {'project_usage': ..., 'server_usage': ...}.
            - Not found: {'error': '... not found'}.
        """
        if not self._ensure_connection():
            return {'error': 'Connection not available'}

        # Build project usage
        limits = self.conn.compute.get_limits().absolute
        pu_keys = {
            'cores':    ('totalCoresUsed', 'maxTotalCores'),
            'ram (MB)': ('totalRAMUsed', 'maxTotalRAMSize'),
            'instances':('totalInstancesUsed', 'maxTotalInstances'),
            'volumes':  ('totalVolumesUsed', 'maxTotalVolumes'),
            'gigabytes':('totalGigabytesUsed', 'maxTotalVolumeGigabytes'),
        }
        project_usage = {}
        for label, (used_key, max_key) in pu_keys.items():
            project_usage[label] = {
                'used': getattr(limits, used_key, limits.get(used_key, 'N/A')),
                'quota': getattr(limits, max_key, limits.get(max_key, 'N/A'))
            }

        # No identifier: return project + all servers
        if not server_id_or_name:
            servers_usage = []
            for srv in self.conn.compute.servers():
                full = self.conn.compute.get_server(srv.id)
                servers_usage.append({
                    'id': full.id,
                    'name': full.name,
                    'status': full.status,
                    'created_at': getattr(full, 'created_at', None),
                    'networks': getattr(full, 'networks', {})
                })
            return {'project_usage': project_usage, 'servers_usage': servers_usage}

        # Project-only request
        if server_id_or_name.lower() in ('project', 'project_usage'):
            return {'project_usage': project_usage}

        # Server-specific request
        server_ref = self.conn.compute.find_server(server_id_or_name)
        if server_ref:
            s = self.conn.compute.get_server(server_ref.id)
            server_usage = {
                'id': s.id,
                'name': s.name,
                'status': s.status,
                'created_at': getattr(s, 'created_at', None),
                'networks': getattr(s, 'networks', {})
            }
            # Flavor details
            if hasattr(s, 'flavor') and s.flavor:
                fid = s.flavor.get('id')
                try:
                    f = self.conn.compute.get_flavor(fid)
                    server_usage['flavor'] = {
                        'id': f.id, 'name': f.name,
                        'vcpus': f.vcpus, 'ram': f.ram, 'disk': f.disk
                    }
                except Exception:
                    server_usage['flavor'] = {'id': fid}
            # Volume details
            vols = []
            for att in getattr(s, 'attached_volumes', []):
                vid = att.get('id')
                if vid:
                    try:
                        v = self.conn.block_storage.get_volume(vid)
                        vols.append({'id': v.id, 'name': v.name, 'size': v.size, 'status': v.status})
                    except Exception:
                        continue
            server_usage['volumes'] = vols

            return {'project_usage': project_usage, 'server_usage': server_usage}

        # Not found
        return {'error': f"'{server_id_or_name}' not found"}


def prompt_for_server_creation(api: OpenStackAPI) -> Optional[Dict[str, Any]]:
    """Prompt user for server creation parameters and create server."""
    print("\n--- Server Creation ---")
    
    # Get available resources for user reference
    images = api.list_images()
    flavors = api.list_flavors()
    networks = api.list_networks()
    
    print("\nAvailable resources:")
    print("Images:")
    for img in images[:5]:  # Show first 5 to avoid overwhelming
        print(f"  - {img['name']}")
    print("\nFlavors:")
    for flv in flavors[:5]:
        print(f"  - {flv['name']} (RAM: {flv['ram']} MB, VCPUs: {flv['vcpus']}, Disk: {flv['disk']} GB)")
    print("\nNetworks:")
    for net in networks[:5]:
        print(f"  - {net['name']}")
    
    # Get user input
    name = input("\nEnter server name: ").strip()
    image_name = input("Enter image name: ").strip()
    flavor_name = input("Enter flavor name: ").strip()
    network_name = input("Enter network name (default: 'default'): ").strip() or 'default'
    
    use_volume = input("Create boot volume? (yes/no): ").strip().lower() == 'yes'
    volume_size = None
    if use_volume:
        while True:
            try:
                volume_size = int(input("Enter boot volume size in GB: "))
                if volume_size > 0:
                    break
                print("Volume size must be positive.")
            except ValueError:
                print("Please enter a valid number.")
    
    # Create server
    return api.create_server(name, image_name, flavor_name, network_name, volume_size)


def main():
    """Main interactive function."""
    print("OpenStack API Integration")
    print("------------------------")
    
    api = OpenStackAPI()
    if not api.connect():
        print("Failed to connect to OpenStack. Exiting.")
        return
    
    while True:
        print("\nMain Menu:")
        print("1. List Servers")
        print("2. List Images")
        print("3. List Flavors")
        print("4. List Networks")
        print("5. List Volumes")
        print("6. Create Server")
        print("7. Delete Server")
        print("8. Resize Server")
        print("9. Create Volume")
        print("10. Delete Volume")
        print("11. Create Network with Subnet")
        print("12. Get Usage Statistics")
        print("0. Exit")
        
        choice = input("Enter your choice: ").strip()
        
        try:
            if choice == '1':
                servers = api.list_servers()
                print("\nServers:")
                for srv in servers:
                    print(f"  - {srv['name']} (ID: {srv['id']}, Status: {srv['status']})")
            
            elif choice == '2':
                images = api.list_images()
                print("\nImages:")
                for img in images:
                    print(f"  - {img['name']} (ID: {img['id']}, Size: {img['size']} bytes)")
            
            elif choice == '3':
                flavors = api.list_flavors()
                print("\nFlavors:")
                for flv in flavors:
                    print(f"  - {flv['name']} (VCPUs: {flv['vcpus']}, RAM: {flv['ram']} MB, Disk: {flv['disk']} GB)")
            
            elif choice == '4':
                networks = api.list_networks()
                print("\nNetworks:")
                for net in networks:
                    print(f"  - {net['name']} (ID: {net['id']}, Subnets: {len(net['subnets'])})")
            
            elif choice == '5':
                volumes = api.list_volumes()
                print("\nVolumes:")
                for vol in volumes:
                    print(f"  - {vol['name']} (ID: {vol['id']}, Size: {vol['size']} GB, Status: {vol['status']})")
            
            elif choice == '6':
                server = prompt_for_server_creation(api)
                if server:
                    print(f"\nServer creation initiated:")
                    print(f"  Name: {server['name']}")
                    print(f"  ID: {server['id']}")
                    print(f"  Status: {server['status']}")
                else:
                    print("\nServer creation failed.")
            
            elif choice == '7':
                server_id = input("Enter server ID or name to delete: ").strip()
                if api.delete_server(server_id):
                    print("Server deletion successful.")
                else:
                    print("Server deletion failed.")
            
            elif choice == '8':
                server_id = input("Enter server ID or name to resize: ").strip()
                flavors = api.list_flavors()
                print("\nAvailable flavors:")
                for flv in flavors:
                    print(f"  - {flv['name']} (RAM: {flv['ram']} MB, VCPUs: {flv['vcpus']}, Disk: {flv['disk']} GB)")
                new_flavor = input("Enter new flavor name: ").strip()
                if api.resize_server(server_id, new_flavor):
                    print("Server resize successful.")
                else:
                    print("Server resize failed.")
            
            elif choice == '9':
                name = input("Enter volume name: ").strip()
                while True:
                    try:
                        size = int(input("Enter volume size in GB: "))
                        if size > 0:
                            break
                        print("Size must be positive.")
                    except ValueError:
                        print("Please enter a valid number.")
                volume = api.create_volume(name, size)
                if volume:
                    print(f"\nVolume created:")
                    print(f"  Name: {volume['name']}")
                    print(f"  ID: {volume['id']}")
                    print(f"  Size: {volume['size']} GB")
                else:
                    print("\nVolume creation failed.")
            
            elif choice == '10':
                volume_id = input("Enter volume ID or name to delete: ").strip()
                if api.delete_volume(volume_id):
                    print("Volume deletion successful.")
                else:
                    print("Volume deletion failed.")
            
            elif choice == '11':
                name = input("Enter network name: ").strip()
                cidr = input("Enter subnet CIDR (default: 192.168.100.0/24): ").strip() or "192.168.100.0/24"
                subnet_name = input("Enter subnet name (optional, default: networkname-subnet): ").strip()
                result = api.create_network_with_subnet(name, cidr, subnet_name)
                if result:
                    network, subnet = result
                    print(f"\nNetwork created:")
                    print(f"  Name: {network['name']}")
                    print(f"  ID: {network['id']}")
                    print(f"\nSubnet created:")
                    print(f"  Name: {subnet['name']}")
                    print(f"  CIDR: {subnet['cidr']}")
                else:
                    print("\nNetwork creation failed.")
            
            elif choice == '12':
                server_id = input("Enter server ID or name for details (optional, press Enter for project only): ").strip() or None
                usage = api.get_usage(server_id)
                print("\nUsage Statistics:")
                if 'project_usage' in usage:
                    print("\nProject Usage:")
                    for resource, stats in usage['project_usage'].items():
                        print(f"  {resource:10}: {stats['used']} / {stats['quota']}")
                if 'server_usage' in usage and usage['server_usage']:
                    print("\nServer Usage:")
                    srv = usage['server_usage']
                    print(f"  Name: {srv['name']}")
                    print(f"  ID: {srv['id']}")
                    print(f"  Status: {srv['status']}")
                    if 'flavor' in srv:
                        print("\n  Flavor:")
                        print(f"    Name: {srv['flavor'].get('name', 'N/A')}")
                        print(f"    VCPUs: {srv['flavor'].get('vcpus', 'N/A')}")
                        print(f"    RAM: {srv['flavor'].get('ram', 'N/A')} MB")
                        print(f"    Disk: {srv['flavor'].get('disk', 'N/A')} GB")
                    if 'volumes' in srv and srv['volumes']:
                        print("\n  Volumes:")
                        for vol in srv['volumes']:
                            print(f"    - {vol['name']}: {vol['size']} GB ({vol['status']})")
            
            elif choice == '0':
                print("Exiting...")
                break
            
            else:
                print("Invalid choice. Please try again.")
        
        except Exception as e:
            print(f"An error occurred: {e}")
            # Optionally, log the full traceback for debugging
            # import traceback
            # traceback.print_exc()


if __name__ == "__main__":
    main()