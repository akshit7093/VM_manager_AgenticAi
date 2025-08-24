#!/usr/bin/env python3
"""
Fake OpenStack API Integration Module

This module mimics the behavior of api.py by providing a unified API for OpenStsack-like
operations, using MongoDB for data storage instead of JSON files.
For development and showcasing purposes.
"""

import json
import uuid
import os
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from mongo_db import MongoDB

class FakeOpenStackAPI:
    """Fake API class mimicking OpenStack operations using MongoDB."""
    
    def __init__(self):
        """Initialize by connecting to MongoDB and loading data."""
        self.conn = None
        self.db = MongoDB()
        self._ensure_collections()
        self._load_data()
    
    def _ensure_collections(self):
        """Ensure all required collections exist in MongoDB."""
        # List of collections we need
        collections = ['servers', 'images', 'flavors', 'networks', 'volumes', 'usage']
        
        # Check if collections exist and have data
        for collection in collections:
            if not self.db.find_all(collection):
                # If collection is empty, try to load from JSON file
                self._load_collection_from_json(collection)
    
    def _load_collection_from_json(self, collection_name: str):
        """Load data from JSON file into MongoDB collection if it exists."""
        try:
            json_file = f'fake_data/{collection_name}.json'
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if data and isinstance(data, list):
                        self.db.insert_many(collection_name, data)
                        print(f"Loaded {len(data)} items from {json_file} into MongoDB")
        except Exception as e:
            print(f"Error loading {collection_name} from JSON: {e}")
    
    def _load_data(self):
        """Load fake data from MongoDB into memory for quick access."""
        try:
            self.servers = self.db.find_all('servers')
            self.images = self.db.find_all('images')
            self.flavors = self.db.find_all('flavors')
            self.networks = self.db.find_all('networks')
            self.volumes = self.db.find_all('volumes')
            self.usage = self.db.find_all('usage')
            if not self.usage:
                self.usage = {'project_usage': {}, 'servers_usage': []}
            else:
                # If usage is a list with one item, extract that item
                if isinstance(self.usage, list) and len(self.usage) == 1:
                    self.usage = self.usage[0]
                # If usage is still a list but empty, initialize it
                elif isinstance(self.usage, list) and len(self.usage) == 0:
                    self.usage = {'project_usage': {}, 'servers_usage': []}
            print("Fake data loaded successfully from MongoDB!")
        except Exception as e:
            print(f"Error loading fake data from MongoDB: {e}")
            self.servers = []
            self.images = []
            self.flavors = []
            self.networks = []
            self.volumes = []
            self.usage = {'project_usage': {}, 'servers_usage': []}
    
    def _save_data_to_mongodb(self, data, collection_name: str):
        """Helper function to save data to MongoDB collection."""
        try:
            # Clear existing collection data
            self.db.delete_many(collection_name, {})
            
            # Insert new data
            if isinstance(data, list):
                if data:
                    self.db.insert_many(collection_name, data)
            else:
                # For usage which might be a dictionary
                self.db.insert_one(collection_name, data)
                
            print(f"Data successfully saved to MongoDB collection: {collection_name}")
        except Exception as e:
            print(f"Error saving data to MongoDB collection {collection_name}: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to MongoDB."""
        return self.db.client is not None
    
    def connect(self) -> bool:
        """Simulate a successful connection."""
        print("Simulating connection to Fake OpenStack via MongoDB...")
        return self.db.connect()
    
    def _ensure_connection(self) -> bool:
        """Always return True as no real connection is needed."""
        return True
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """List all fake servers from MongoDB."""
        print("Listing fake servers from MongoDB...")
        self.servers = self.db.find_all('servers')
        if not self.servers:
            print("No servers found.")
        return self.servers
    
    def list_images(self) -> List[Dict[str, Any]]:
        """List available fake images from MongoDB."""
        print("Listing fake images from MongoDB...")
        self.images = self.db.find_all('images')
        if not self.images:
            print("No images found.")
        return self.images
    
    def list_flavors(self) -> List[Dict[str, Any]]:
        """List available fake flavors from MongoDB."""
        print("Listing fake flavors from MongoDB...")
        self.flavors = self.db.find_all('flavors')
        if not self.flavors:
            print("No flavors found.")
        return self.flavors
    
    def list_networks(self) -> List[Dict[str, Any]]:
        """List available fake networks from MongoDB."""
        print("Listing fake networks from MongoDB...")
        self.networks = self.db.find_all('networks')
        if not self.networks:
            print("No networks found.")
        return self.networks
    
    def list_volumes(self) -> List[Dict[str, Any]]:
        """List available fake volumes from MongoDB."""
        print("Listing fake volumes from MongoDB...")
        self.volumes = self.db.find_all('volumes')
        if not self.volumes:
            print("No volumes found.")
        return self.volumes
    
    def create_server(self, 
                     name: str, 
                     image_name: str, 
                     flavor_name: str, 
                     network_name: str = 'default', 
                     volume_size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Create a new fake server in MongoDB."""
        print(f"Attempting to create fake server '{name}'...")
        
        # Refresh data from MongoDB
        self.images = self.db.find_all('images')
        self.flavors = self.db.find_all('flavors')
        self.networks = self.db.find_all('networks')
        
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
        
        # Get current servers to determine IP address
        self.servers = self.db.find_all('servers')
        
        new_server = {
            'id': str(uuid.uuid4()),
            'name': name,
            'status': 'ACTIVE',  # Immediately active for simplicity
            'created': datetime.now().isoformat(),
            'flavor': {'id': flavor['id']},
            'image': {'id': image['id']},
            'networks': {network['name']: [f"192.168.{len(self.servers) + 1}.100"]}
        }
        
        # Add server to MongoDB
        self.db.insert_one('servers', new_server)
        self.servers.append(new_server)
        
        if volume_size:
            new_volume = {
                'id': str(uuid.uuid4()),
                'name': f"{name}-boot-volume",
                'status': 'in-use',
                'size': volume_size,
                'attachments': [{'server_id': new_server['id']}]
            }
            # Add volume to MongoDB
            self.db.insert_one('volumes', new_volume)
            self.volumes.append(new_volume)
            print(f"  Created fake boot volume '{new_volume['name']}' of size {volume_size} GB.")
        
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
        """Delete a fake server from MongoDB."""
        # Refresh servers from MongoDB
        self.servers = self.db.find_all('servers')
        
        server = next((srv for srv in self.servers if srv['id'] == server_id_or_name or srv['name'] == server_id_or_name), None)
        if not server:
            print(f"Fake server '{server_id_or_name}' not found. Perhaps already deleted?")
            return True
        
        print(f"Deleting fake server '{server['name']}' (ID: {server['id']})...")
        
        # Delete server from MongoDB
        self.db.delete_one('servers', {'id': server['id']})
        self.servers.remove(server)
        
        # Refresh volumes from MongoDB
        self.volumes = self.db.find_all('volumes')
        
        # Find and delete associated volumes
        volumes_to_delete = [vol for vol in self.volumes if any(att['server_id'] == server['id'] for att in vol.get('attachments', []))]
        for volume in volumes_to_delete:
            self.db.delete_one('volumes', {'id': volume['id']})
            self.volumes.remove(volume)
        
        print(f"Fake server '{server['name']}' deleted successfully.")
        return True
    
    def resize_server(self, server_id_or_name: str, flavor_name: str) -> bool:
        """Resize a fake server to a new flavor in MongoDB."""
        # Refresh data from MongoDB
        self.servers = self.db.find_all('servers')
        self.flavors = self.db.find_all('flavors')
        
        server = next((srv for srv in self.servers if srv['id'] == server_id_or_name or srv['name'] == server_id_or_name), None)
        flavor = next((flv for flv in self.flavors if flv['name'] == flavor_name), None)
        
        if not server:
            print(f"Fake server '{server_id_or_name}' not found.")
            return False
        if not flavor:
            print(f"Error: Flavor '{flavor_name}' not found.")
            return False
        
        print(f"Resizing fake server '{server['name']}' to flavor '{flavor_name}'...")
        
        # Update server in MongoDB
        server['flavor'] = {'id': flavor['id']}
        self.db.update_one('servers', {'id': server['id']}, server)
        
        print(f"Fake server '{server['name']}' resized successfully.")
        return True
    
    def create_volume(self, name: str, size_gb: int) -> Optional[Dict[str, Any]]:
        """Create a standalone fake volume in MongoDB."""
        print(f"Creating fake volume '{name}' of size {size_gb} GB...")
        
        new_volume = {
            'id': str(uuid.uuid4()),
            'name': name,
            'status': 'available',
            'size': size_gb,
            'attachments': []
        }
        
        # Add volume to MongoDB
        self.db.insert_one('volumes', new_volume)
        self.volumes.append(new_volume)
        
        print(f"Fake volume '{name}' created with ID: {new_volume['id']}")
        return {
            'id': new_volume['id'],
            'name': new_volume['name'],
            'size': new_volume['size'],
            'status': new_volume['status']
        }
    
    def delete_volume(self, volume_id_or_name: str) -> bool:
        """Delete a fake volume from MongoDB."""
        # Refresh volumes from MongoDB
        self.volumes = self.db.find_all('volumes')
        
        volume = next((vol for vol in self.volumes if vol['id'] == volume_id_or_name or vol['name'] == volume_id_or_name), None)
        if not volume:
            print(f"Fake volume '{volume_id_or_name}' not found. Perhaps already deleted?")
            return True
        
        print(f"Deleting fake volume '{volume['name']}' (ID: {volume['id']})...")
        
        # Delete volume from MongoDB
        self.db.delete_one('volumes', {'id': volume['id']})
        self.volumes.remove(volume)
        
        print(f"Fake volume '{volume['name']}' deleted successfully.")
        return True
    
    def create_network_with_subnet(self, network_name: str, 
                                 subnet_cidr: str = "192.168.100.0/24", 
                                 subnet_name: Optional[str] = None) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Create a fake network with subnet in MongoDB."""
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
        
        # Add network to MongoDB
        self.db.insert_one('networks', new_network)
        self.networks.append(new_network)
        
        # Note: Subnets could be stored in a separate collection if needed
        
        print(f"Fake network '{network_name}' and subnet '{subnet_name}' created.")
        return (
            {'id': new_network['id'], 'name': new_network['name'], 'status': new_network['status']},
            {'id': new_subnet['id'], 'name': new_subnet['name'], 'cidr': new_subnet['cidr'], 'network_id': new_subnet['network_id']}
        )
    
    def get_usage(self, identifier: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics from MongoDB."""
        # Refresh usage data from MongoDB
        usage_data = self.db.find_all('usage')
        if usage_data and isinstance(usage_data, list) and len(usage_data) > 0:
            self.usage = usage_data[0]
        else:
            self.usage = {'project_usage': {}, 'servers_usage': []}
        
        # If no identifier given, return everything
        if not identifier:
            return {
                'project_usage': self.usage.get('project_usage', {}),
                'servers_usage': self.usage.get('servers_usage', [])
            }

        # Check if identifier matches the project
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