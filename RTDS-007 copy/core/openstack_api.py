import openstack
import os
import time
from typing import Optional, Tuple, Dict, Any, List
from dotenv import load_dotenv
load_dotenv()

OS_AUTH_URL         = os.getenv("OS_AUTH_URL")
OS_USERNAME         = os.getenv("OS_USERNAME")
OS_PASSWORD         = os.getenv("OS_PASSWORD")
OS_PROJECT_NAME     = os.getenv("OS_PROJECT_NAME")
OS_PROJECT_ID       = os.getenv("OS_PROJECT_ID")
OS_USER_DOMAIN_NAME = os.getenv("OS_USER_DOMAIN_NAME")
OS_PROJECT_DOMAIN_NAME = os.getenv("OS_PROJECT_DOMAIN_NAME")
OS_INTERFACE        = os.getenv("OS_INTERFACE")
OS_REGION_NAME      = os.getenv("OS_REGION_NAME")


class OpenStackAPI:
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
    
    def create_server(self, name: str, image_name: str, flavor_name: str, network_name: str = 'default', volume_size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new server (VM instance).
        
        Args:
            name: Name of the server to create
            image_name: Name of the image to use
            flavor_name: Name of the flavor to use
            network_name: Name of the network to attach to
            volume_size: Size of boot volume in GB (optional)
        
        Returns:
            Dictionary with server details (including ID and IPs) or None if failed
        """
        if not self._ensure_connection():
            return None

        volume = None  # Initialize volume variable for error handling
        try:
            print(f"Attempting to create server '{name}'...")

            # Find resources
            image = self.conn.compute.find_image(image_name)
            flavor = self.conn.compute.find_flavor(flavor_name)
            network = self.conn.network.find_network(network_name)

            # Validate resources
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

            # Prepare server parameters
            server_params = {
                'name': name,
                'flavor_id': flavor.id,
                'networks': [{"uuid": network.id}]
            }

            # Handle volume boot if specified
            if volume_size:
                print(f"  Creating bootable volume of size {volume_size} GB...")
                volume = self.conn.block_storage.create_volume(
                    name=f"{name}-boot-volume",
                    size=volume_size,
                    imageRef=image.id,
                )
                self.conn.block_storage.wait_for_status(volume, status='available', 
                                                    failures=['error'], interval=5, wait=300)
                print(f"  Volume {volume.id} created and available.")

                server_params['block_device_mapping_v2'] = [{
                    'boot_index': '0',
                    'uuid': volume.id,
                    'source_type': 'volume',
                    'destination_type': 'volume',
                    'delete_on_termination': True
                }]
            else:
                server_params['image_id'] = image.id

            # Create server
            print("  Submitting server creation request...")
            server = self.conn.compute.create_server(**server_params)
            
            # Wait for server to become active
            print("  Waiting for server to become active...")
            server = self.conn.compute.wait_for_server(
                server,
                status='ACTIVE',
                failures=['ERROR'],
                interval=10,
                wait=600
            )

            # Get IP addresses
            ips = []
            if hasattr(server, 'addresses') and server.addresses:
                for network_name, addresses in server.addresses.items():
                    for address in addresses:
                        if 'addr' in address:
                            ips.append(f"{network_name}: {address['addr']}")

            print(f"\nServer creation successful!")
            print(f"  ID: {server.id}")
            print(f"  Name: {server.name}")
            print(f"  Status: {server.status}")
            print(f"  IP Addresses: {', '.join(ips) if ips else 'No IPs assigned'}")

            return {
                'id': server.id,
                'name': server.name,
                'status': server.status,
                'ips': ips,
                'image': image_name,
                'flavor': flavor_name,
                'network': network_name,
                'volume_size': volume_size
            }

        except Exception as e:
            print(f"\nError creating server '{name}': {e}")
            if volume:
                try:
                    print("  Cleaning up volume due to creation failure...")
                    self.conn.block_storage.delete_volume(volume)
                except Exception as ve:
                    print(f"  Warning: Failed to delete volume {volume.id}: {ve}")
            return None
    
    def delete_server(self, server_id_or_name: str) -> bool:
        """
        Delete a server (VM instance).
        
        Args:
            server_id_or_name: IDof the server to delete
        
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
            self.conn.block_storage.wait_for_status(volume, status='available', failures=['error'], interval=5, wait=300)
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
    
    def create_network_with_subnet(self, network_name: str, subnet_cidr: str = "192.168.100.0/24", subnet_name: Optional[str] = None) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
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
            Dictionary with usage statistics
        """
        if not self._ensure_connection():
            return {}
        
        result = {'project_usage': {}, 'server_usage': {}}
        
        try:
            # Get project limits
            limits = self.conn.compute.get_limits().absolute
            pu = {
                'cores':    ('totalCoresUsed', 'maxTotalCores'),
                'ram (MB)': ('totalRAMUsed', 'maxTotalRAMSize'),
                'instances':('totalInstancesUsed', 'maxTotalInstances'),
                'volumes':  ('totalVolumesUsed', 'maxTotalVolumes'),
                'gigabytes':('totalGigabytesUsed', 'maxTotalVolumeGigabytes'),
            }
            
            # Add project usage to result
            for label, (used_key, max_key) in pu.items():
                result['project_usage'][label] = {
                    'used': limits.get(used_key, 'N/A'),
                    'quota': limits.get(max_key, 'N/A')
                }
            
            # Get server-specific usage if requested
            if server_id_or_name:
                server = self.conn.compute.find_server(server_id_or_name)
                if server:
                    server = self.conn.compute.get_server(server.id)
                    server_usage = {
                        'id': server.id,
                        'name': server.name,
                        'status': server.status,
                        'created': server.created,
                        'networks': server.networks
                    }
                    
                    # Get flavor details
                    flavor_id = server.flavor['id']
                    try:
                        flavor = self.conn.compute.get_flavor(flavor_id)
                        server_usage['flavor'] = {
                            'name': flavor.name,
                            'id': flavor.id,
                            'vcpus': flavor.vcpus,
                            'ram': flavor.ram,
                            'disk': flavor.disk
                        }
                    except Exception:
                        server_usage['flavor'] = {'id': flavor_id}
                    
                    # Get volume details
                    if server.attached_volumes:
                        server_usage['volumes'] = []
                        for att in server.attached_volumes:
                            vol = self.conn.block_storage.get_volume(att['id'])
                            server_usage['volumes'].append({
                                'id': vol.id,
                                'name': vol.name,
                                'size': vol.size,
                                'status': vol.status
                            })
                    
                    result['server_usage'] = server_usage
                else:
                    result['server_usage'] = {'error': f"Server '{server_id_or_name}' not found"}
            
            return result
        except Exception as e:
            print(f"Error getting usage statistics: {e}")
            return {'error': str(e)}

openstack_api = OpenStackAPI()