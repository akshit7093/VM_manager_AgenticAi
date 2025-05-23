#!/usr/bin/env python3
"""
Fake OpenStack API Integration Module

This module mimics the behavior of api.py by providing a unified API for OpenStack-like
operations, returning data from pre-defined JSON files instead of calling the OpenStack API.
For development and showcasing purposes.
"""

import json
import uuid
import os
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

class FakeOpenStackAPI:
    """Fake API class mimicking OpenStack operations using JSON data."""
    
    def __init__(self):
        """Initialize by loading fake data from JSON files."""
        self.conn = None
        self._load_data()
    
    def _load_data(self):
        """Load fake data from JSON files into memory."""
        try:
            with open('fake_data/servers.json', 'r') as f:
                self.servers = json.load(f)
            with open('fake_data/images.json', 'r') as f:
                self.images = json.load(f)
            with open('fake_data/flavors.json', 'r') as f:
                self.flavors = json.load(f)
            with open('fake_data/networks.json', 'r') as f:
                self.networks = json.load(f)
            with open('fake_data/volumes.json', 'r') as f:
                self.volumes = json.load(f)
            with open('fake_data/usage.json', 'r') as f:
                self.usage = json.load(f)
            print("Fake data loaded successfully!")
        except Exception as e:
            print(f"Error loading fake data: {e}")
            self.servers = []
            self.images = []
            self.flavors = []
            self.networks = []
            self.volumes = []
            self.usage = {'project_usage': {}, 'servers_usage': []}

    def _save_data_to_file(self, data, filename):
        """Helper function to save data to a JSON file."""
        try:
            filepath = os.path.join('fake_data', filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Data successfully saved to {filepath}")
        except Exception as e:
            print(f"Error saving data to {filepath}: {e}")
    
    def connect(self) -> bool:
        """Simulate a successful connection."""
        print("Simulating connection to Fake OpenStack...")
        return True
    
    def _ensure_connection(self) -> bool:
        """Always return True as no real connection is needed."""
        return True
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """List all fake servers."""
        print("Listing fake servers...")
        if not self.servers:
            print("No servers found.")
        return self.servers
    
    def list_images(self) -> List[Dict[str, Any]]:
        """List available fake images."""
        print("Listing fake images...")
        if not self.images:
            print("No images found.")
        return self.images
    
    def list_flavors(self) -> List[Dict[str, Any]]:
        """List available fake flavors."""
        print("Listing fake flavors...")
        if not self.flavors:
            print("No flavors found.")
        return self.flavors
    
    def list_networks(self) -> List[Dict[str, Any]]:
        """List available fake networks."""
        print("Listing fake networks...")
        if not self.networks:
            print("No networks found.")
        return self.networks
    
    def list_volumes(self) -> List[Dict[str, Any]]:
        """List available fake volumes."""
        print("Listing fake volumes...")
        if not self.volumes:
            print("No volumes found.")
        return self.volumes
    
    def create_server(self, 
                     name: str, 
                     image_name: str, 
                     flavor_name: str, 
                     network_name: str = 'default', 
                     volume_size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Create a new fake server."""
        print(f"Attempting to create fake server '{name}'...")
        
        image = next((img for img in self.images if img['name'] == image_name), None)
        flavor = next((flv for flv in self.flavors if flv['name'] == flavor_name), None)
        network = next((net for net in self.networks if net['name'] == network_name), None)
        
        if not image:
            print(f"Error: Image '{image_name}' not found.")
            return None
        if not flavor:
            print(f"Error: Flavor '{flavor_name}' not found.")
            return None
        if not network:
            print(f"Error: Network '{network_name}' not found.")
            return None
        
        new_server = {
            'id': str(uuid.uuid4()),
            'name': name,
            'status': 'ACTIVE',  # Immediately active for simplicity
            'created': datetime.now().isoformat(),
            'flavor': {'id': flavor['id']},
            'image': {'id': image['id']},
            'networks': {network['name']: [f"192.168.{len(self.servers) + 1}.100"]}
        }
        
        if volume_size:
            new_volume = {
                'id': str(uuid.uuid4()),
                'name': f"{name}-boot-volume",
                'status': 'in-use',
                'size': volume_size,
                'attachments': [{'server_id': new_server['id']}]
            }
            self.volumes.append(new_volume)
            print(f"  Created fake boot volume '{new_volume['name']}' of size {volume_size} GB.")
        
        self.servers.append(new_server)
        self._save_data_to_file(self.servers, 'servers.json')
        if volume_size: # Also save volumes if a new one was created
            self._save_data_to_file(self.volumes, 'volumes.json')
        print(f"Fake server '{name}' created with ID: {new_server['id']}")
        return {
            'id': new_server['id'],
            'name': new_server['name'],
            'status': new_server['status'],
            'image': image_name,
            'flavor': flavor_name,
            'network': network_name,
            'volume_size': volume_size
        }
    
    def delete_server(self, server_id_or_name: str) -> bool:
        """Delete a fake server."""
        server = next((srv for srv in self.servers if srv['id'] == server_id_or_name or srv['name'] == server_id_or_name), None)
        if not server:
            print(f"Fake server '{server_id_or_name}' not found. Perhaps already deleted?")
            return True
        
        print(f"Deleting fake server '{server['name']}' (ID: {server['id']})...")
        self.servers.remove(server)
        self._save_data_to_file(self.servers, 'servers.json')
        
        # Remove associated volumes and save
        initial_volume_count = len(self.volumes)
        self.volumes = [vol for vol in self.volumes if not any(att['server_id'] == server['id'] for att in vol.get('attachments', []))]
        if len(self.volumes) != initial_volume_count:
            self._save_data_to_file(self.volumes, 'volumes.json')
        print(f"Fake server '{server['name']}' deleted successfully.")
        return True
    
    def resize_server(self, server_id_or_name: str, flavor_name: str) -> bool:
        """Resize a fake server to a new flavor."""
        server = next((srv for srv in self.servers if srv['id'] == server_id_or_name or srv['name'] == server_id_or_name), None)
        flavor = next((flv for flv in self.flavors if flv['name'] == flavor_name), None)
        
        if not server:
            print(f"Fake server '{server_id_or_name}' not found.")
            return False
        if not flavor:
            print(f"Error: Flavor '{flavor_name}' not found.")
            return False
        
        print(f"Resizing fake server '{server['name']}' to flavor '{flavor_name}'...")
        server['flavor'] = {'id': flavor['id']}
        self._save_data_to_file(self.servers, 'servers.json')
        print(f"Fake server '{server['name']}' resized successfully.")
        return True
    
    def create_volume(self, name: str, size_gb: int) -> Optional[Dict[str, Any]]:
        """Create a standalone fake volume."""
        print(f"Creating fake volume '{name}' of size {size_gb} GB...")
        new_volume = {
            'id': str(uuid.uuid4()),
            'name': name,
            'status': 'available',
            'size': size_gb,
            'attachments': []
        }
        self.volumes.append(new_volume)
        self._save_data_to_file(self.volumes, 'volumes.json')
        print(f"Fake volume '{name}' created with ID: {new_volume['id']}")
        return {
            'id': new_volume['id'],
            'name': new_volume['name'],
            'size': new_volume['size'],
            'status': new_volume['status']
        }
    
    def delete_volume(self, volume_id_or_name: str) -> bool:
        """Delete a fake volume."""
        volume = next((vol for vol in self.volumes if vol['id'] == volume_id_or_name or vol['name'] == volume_id_or_name), None)
        if not volume:
            print(f"Fake volume '{volume_id_or_name}' not found. Perhaps already deleted?")
            return True
        
        print(f"Deleting fake volume '{volume['name']}' (ID: {volume['id']})...")
        self.volumes.remove(volume)
        self._save_data_to_file(self.volumes, 'volumes.json')
        print(f"Fake volume '{volume['name']}' deleted successfully.")
        return True
    
    def create_network_with_subnet(self, network_name: str, 
                                 subnet_cidr: str = "192.168.100.0/24", 
                                 subnet_name: Optional[str] = None) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Create a fake network with subnet."""
        if not subnet_name:
            subnet_name = f"{network_name}-subnet"
        
        print(f"Creating fake network '{network_name}' with subnet '{subnet_name}'...")
        new_network = {
            'id': str(uuid.uuid4()),
            'name': network_name,
            'status': 'ACTIVE',
            'subnets': [f"subnet-{uuid.uuid4()}"]
        }
        new_subnet = {
            'id': new_network['subnets'][0],
            'name': subnet_name,
            'cidr': subnet_cidr,
            'network_id': new_network['id']
        }
        
        self.networks.append(new_network)
        # Note: Subnets are usually part of the network object or a separate list.
        # Assuming subnets are not stored in a separate top-level list in fake_data for now.
        # If they were, e.g., self.subnets, we'd save that too.
        self._save_data_to_file(self.networks, 'networks.json')
        print(f"Fake network '{network_name}' and subnet '{subnet_name}' created.")
        return (
            {'id': new_network['id'], 'name': new_network['name'], 'status': new_network['status']},
            {'id': new_subnet['id'], 'name': new_subnet['name'], 'cidr': new_subnet['cidr'], 'network_id': new_subnet['network_id']}
        )
    
    def get_usage(self, identifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics for the entire project and all servers,
        or for a specific server by ID or name.

        Args:
            identifier: Optional server ID or name to get specific usage.

        Returns:
            If identifier is None: returns full usage JSON (project_usage + servers_usage).
            If identifier matches a server: returns that server's usage dict.
            Otherwise: returns {'error': 'Not found'}.
        """
        # If no identifier given, return everything
        if not identifier:
            return {
                'project_usage': self.usage.get('project_usage', {}),
                'servers_usage': self.usage.get('servers_usage', [])
            }

        # Check if identifier matches the project
        # (optional: if you want to allow project-level queries by name/id)
        if identifier.lower() in ('project', 'project_usage'):
            return self.usage.get('project_usage', {})

        # Otherwise, look for a server match
        match = next(
            (srv for srv in self.usage.get('servers_usage', [])
             if srv.get('id') == identifier or srv.get('name') == identifier),
            None
        )
        if match:
            return match

        # Nothing matched
        return {'error': f"'{identifier}' not found"}

if __name__ == "__main__":
    api = FakeOpenStackAPI()
    servers = api.list_servers()
    print("Servers:", servers)