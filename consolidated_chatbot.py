#!/usr/bin/env python3
"""
Consolidated OpenStack AI Agent Chatbot Assistant.
Combines api.py, agent.py, and runner.py functionality.
"""

import argparse
import sys
import json
import re
import os
import time
from collections import deque
from datetime import datetime
import logging
from typing import Optional, Tuple, Dict, Any, List, Callable

import openstack # From api.py
import requests # From runner.py
from flask import Flask, request, jsonify # From runner.py
from flask_cors import CORS # From runner.py
import google.generativeai as genai # From agent.py
import inspect # From agent.py

# Attempt to import Rich for a better CLI experience
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.text import Text
    from rich.status import Status
    from rich.pretty import Pretty
    from rich.table import Table
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback classes if Rich is not available (copied from runner.py)
    class console:
        @staticmethod
        def print(*args, **kwargs):
            print(*args)
    class Prompt:
        @staticmethod
        def ask(prompt_text, default=None):
            return input(prompt_text + (f" [{default}]" if default else "") + ": ")
    class Confirm:
        @staticmethod
        def ask(prompt_text, default=False):
            return input(prompt_text + (" [y/N]" if not default else " [Y/n]") + ": ").lower() in ('y', 'yes')
    class Panel:
        def __init__(self, content, title="", border_style="", expand=False, subtitle=""):
            print(f"--- {title} ---")
            print(content.text if isinstance(content, Text) else str(content))
            if subtitle:
                print(f"({subtitle})")
            print("---------------")
    class Text:
        def __init__(self, text_content, style=None, overflow=None):
            self.text = str(text_content)
        @staticmethod
        def assemble(*args):
            return Text("".join(part[0] if isinstance(part, tuple) else str(part) for part in args))
        def __str__(self):
            return self.text
    class Pretty:
        def __init__(self, obj, expand_all=None):
            try:
                self.formatted_text = json.dumps(obj, indent=2)
            except ValueError:
                self.formatted_text = str(obj)
        def __str__(self):
            return self.formatted_text
    class Table:
        def __init__(self, title=None):
            self.title = title
            self.rows = []
            self.columns = []
        def add_column(self, header, style=None):
            self.columns.append(header)
        def add_row(self, *args):
            self.rows.append(args)
        def __str__(self):
            output = f"{self.title}\n" if self.title else ""
            output += " | ".join(self.columns) + "\n"
            output += "-" * (len(output) - 1) + "\n"
            for row in self.rows:
                output += " | ".join(str(cell) for cell in row) + "\n"
            return output

# --- Credential Management ---
def get_openstack_credentials():
    """Prompts user for OpenStack credentials if not found in environment."""
    console.print("[cyan]Checking OpenStack Credentials...[/cyan]")
    creds_definitions = [
        ("OS_AUTH_URL", "", None, True),
        ("OS_USERNAME", "OpenStack Username", None, True),
        ("OS_PASSWORD", "OpenStack Password", None, True),
        ("OS_PROJECT_NAME", "OpenStack Project Name", None, True),
        ("OS_PROJECT_ID", "OpenStack Project ID", "", False), # Optional, default to empty string if skipped
        ("OS_USER_DOMAIN_NAME", "OpenStack User Domain Name", "Default", True),
        ("OS_PROJECT_DOMAIN_NAME", "OpenStack Project Domain Name", "Default", True)
    ]

    creds = {}
    all_set_from_env = True
    any_errors = False

    for env_var, prompt_text, default_val, is_strictly_required in creds_definitions:
        val = os.environ.get(env_var)
        if not val:
            all_set_from_env = False
            prompt_message = f"[bold magenta]Enter {prompt_text}[/bold magenta]"
            
            current_default_for_prompt = default_val
            # If it's strictly required but has a default (like domain names), we still want to show the default in prompt
            # If it's optional (like project_id), its default (empty string) is fine for Prompt.ask

            if env_var == "OS_PASSWORD":
                if RICH_AVAILABLE:
                    val = Prompt.ask(prompt_message, password=True).strip()
                else:
                    val = Prompt.ask(prompt_message + " (input will be visible)").strip()
            else:
                val = Prompt.ask(prompt_message, default=current_default_for_prompt).strip()

            if is_strictly_required and not val and not default_val:
                console.print(f"[bold red]Error: {prompt_text} is required and was not provided.[/bold red]")
                any_errors = True
        
        # If val is still empty after prompt (user pressed Enter) and there's a default_val, use default_val.
        # This is especially for optional fields or fields with 'Default' as a common value.
        creds[env_var] = val if val else default_val

    if all_set_from_env:
        console.print("[green]OpenStack credentials successfully loaded from environment variables.[/green]")
    else:
        console.print("[yellow]Some OpenStack credentials were prompted.[/yellow]")

    essential_vars_to_check = ["OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD", "OS_PROJECT_NAME", "OS_USER_DOMAIN_NAME", "OS_PROJECT_DOMAIN_NAME"]
    missing_essentials_after_prompt = []
    for var_key, _, _, _ in creds_definitions:
        if var_key in essential_vars_to_check and not creds.get(var_key):
            # Find the user-friendly name for the missing essential var
            friendly_name = next((name for key, name, _, _ in creds_definitions if key == var_key), var_key)
            missing_essentials_after_prompt.append(friendly_name)
    
    if any_errors or missing_essentials_after_prompt:
        console.print(f"[bold red]Warning: The following essential OpenStack credentials are still missing or were not provided: {', '.join(missing_essentials_after_prompt)}. Connection will likely fail.[/bold red]")
    elif not all_set_from_env: # No errors, but some were prompted
        console.print("[green]OpenStack credentials seem to be provided (some via prompt).[/green]")
        
    return creds

OS_CREDENTIALS = get_openstack_credentials()

# --- OpenStackAPI Class (from api.py) ---
class OpenStackAPI:
    """Main API class for OpenStack operations."""
    
    def __init__(self):
        """Initialize the OpenStack connection."""
        self.conn = None
        self.credentials = OS_CREDENTIALS # Use credentials fetched at startup
    
    def connect(self) -> bool:
        """Connect to OpenStack and return connection status."""
        # Check if essential credentials are set before attempting to connect
        essential_creds = ["OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD", "OS_PROJECT_NAME", "OS_USER_DOMAIN_NAME", "OS_PROJECT_DOMAIN_NAME"]
        if not all(self.credentials.get(key) for key in essential_creds):
            missing_details = [key for key in essential_creds if not self.credentials.get(key)]
            console.print(f"[bold red]Essential OpenStack credentials missing: {', '.join(missing_details)}. Cannot attempt connection.[/bold red]")
            return False
        try:
            console.print(f"[cyan]Attempting to connect to OpenStack at: {self.credentials['OS_AUTH_URL']}...[/cyan]")
            self.conn = openstack.connect(
                auth_url=self.credentials['OS_AUTH_URL'],
                project_name=self.credentials['OS_PROJECT_NAME'],
                username=self.credentials['OS_USERNAME'],
                password=self.credentials['OS_PASSWORD'],
                user_domain_name=self.credentials['OS_USER_DOMAIN_NAME'],
                project_domain_name=self.credentials['OS_PROJECT_DOMAIN_NAME'],
                project_id=self.credentials.get('OS_PROJECT_ID') # project_id can be None
            )
            # Verify connection by trying a simple read operation
            try:
                self.conn.identity.projects() # Check if we can list projects
                console.print("[bold green]OpenStack Connection Successful and Verified![/bold green]")
                return True
            except openstack.exceptions.SDKException as verify_exc:
                console.print(f"[bold red]OpenStack Connection Succeeded, but Verification Failed: {verify_exc}[/bold red]")
                console.print("[yellow]This could indicate issues with permissions for the authenticated user or endpoint configuration problems.[/yellow]")
                self.conn = None # Invalidate the connection object
                return False

        except openstack.exceptions.OpenStackCloudException as os_exc: 
            console.print(f"[bold red]Error connecting to OpenStack (OpenStackCloudException): {os_exc}[/bold red]")
            if hasattr(os_exc, 'http_status') and os_exc.http_status == 401:
                 console.print("[yellow]Hint: Authentication Failure (401). Please double-check your credentials (username, password, project name, domains).[/yellow]")
            elif "ConnectTimeout" in str(os_exc) or "ConnectionError" in str(os_exc) or "Max retries exceeded" in str(os_exc):
                 console.print("[yellow]Hint: Could not connect to the auth URL. Check if the URL is correct, reachable, and if there are any network issues (firewall, proxy).[/yellow]")
            else:
                 console.print(f"[yellow]Details: {os_exc.message}[/yellow]")
            return False
        except requests.exceptions.RequestException as req_exc: # Catch network-level errors from requests library
            console.print(f"[bold red]Network error while trying to connect to OpenStack: {req_exc}[/bold red]")
            console.print("[yellow]Hint: Check your network connection and the OpenStack Auth URL's reachability.[/yellow]")
            return False
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred while connecting to OpenStack: {e}[/bold red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def _ensure_connection(self) -> bool:
        """Ensure we have an active connection."""
        if not self.conn:
            return self.connect()
        return True

    # ... (All other methods from OpenStackAPI in api.py will be added here) ...
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
                     network_name: str, 
                     volume_size: Optional[int] = None, 
                     key_name: Optional[str] = None, 
                     security_groups: Optional[List[str]] = None, 
                     availability_zone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new server (VM instance).
        Args:
            name: Name of the server to create
            image_name: Name of the image to use
            flavor_name: Name of the flavor to use
            network_name: Name of the network to attach to
            volume_size: Size of boot volume in GB (optional)
            key_name: Name of the key pair to use (optional)
            security_groups: List of security group names (optional)
            availability_zone: Availability zone for the server (optional)
        Returns:
            Dictionary with server details or None if failed
        """
        if not self._ensure_connection():
            return None
        
        try:
            print(f"Creating server '{name}'...")
            image = self.conn.compute.find_image(image_name)
            flavor = self.conn.compute.find_flavor(flavor_name)
            network = self.conn.network.find_network(network_name)

            if not image:
                print(f"Image '{image_name}' not found.")
                return None
            if not flavor:
                print(f"Flavor '{flavor_name}' not found.")
                return None
            if not network:
                print(f"Network '{network_name}' not found.")
                return None

            server_params = {
                'name': name,
                'image_id': image.id,
                'flavor_id': flavor.id,
                'networks': [{'uuid': network.id}],
            }

            if key_name:
                keypair = self.conn.compute.find_keypair(key_name)
                if keypair:
                    server_params['key_name'] = keypair.name
                else:
                    print(f"Key pair '{key_name}' not found.")
            
            if security_groups:
                sg_objects = []
                for sg_name in security_groups:
                    sg = self.conn.network.find_security_group(sg_name)
                    if sg:
                        sg_objects.append({'name': sg.name})
                    else:
                        print(f"Security group '{sg_name}' not found. Skipping.")
                if sg_objects:
                    server_params['security_groups'] = sg_objects
            
            if availability_zone:
                server_params['availability_zone'] = availability_zone

            if volume_size:
                # Create a bootable volume and then create server from volume
                print(f"Creating bootable volume of size {volume_size}GB...")
                boot_volume = self.conn.block_storage.create_volume(
                    name=f"{name}-boot-volume",
                    size=volume_size,
                    imageRef=image.id, # Use imageRef for bootable volume from image
                    availability_zone=availability_zone
                )
                self.conn.block_storage.wait_for_status(boot_volume, status='available')
                print(f"Boot volume '{boot_volume.name}' created.")
                
                # Update server_params to boot from volume
                del server_params['image_id'] # Remove image_id as we are booting from volume
                server_params['block_device_mapping_v2'] = [
                    {
                        'boot_index': '0',
                        'uuid': boot_volume.id,
                        'source_type': 'volume',
                        'destination_type': 'volume',
                        'delete_on_termination': True # Or False, depending on desired behavior
                    }
                ]
            
            print(f"Submitting server creation request with params: {server_params}")
            server = self.conn.compute.create_server(**server_params)
            
            print(f"Waiting for server '{name}' to become active...")
            server = self.conn.compute.wait_for_server(server, timeout=600) # Wait up to 10 minutes
            
            print(f"Server '{name}' created successfully with ID: {server.id}")
            return server.to_dict()
        except Exception as e:
            print(f"Error creating server '{name}': {e}")
            # Attempt to clean up boot volume if server creation failed after volume creation
            if 'boot_volume' in locals() and boot_volume:
                try:
                    print(f"Attempting to delete orphaned boot volume '{boot_volume.name}'...")
                    self.conn.block_storage.delete_volume(boot_volume.id)
                    self.conn.block_storage.wait_for_delete(boot_volume)
                    print(f"Orphaned boot volume '{boot_volume.name}' deleted.")
                except Exception as cleanup_e:
                    print(f"Error deleting orphaned boot volume '{boot_volume.name}': {cleanup_e}")
            return None

    def delete_server(self, server_id_or_name: str) -> bool:
        """Delete a server by its ID or name."""
        if not self._ensure_connection():
            return False
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            if not server:
                print(f"Server '{server_id_or_name}' not found.")
                return False
            print(f"Deleting server '{server.name}' (ID: {server.id})...")
            self.conn.compute.delete_server(server.id)
            self.conn.compute.wait_for_delete(server, timeout=300)
            print(f"Server '{server.name}' deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting server '{server_id_or_name}': {e}")
            return False

    def get_server_details(self, server_id_or_name: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific server by ID or name."""
        if not self._ensure_connection():
            return None
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            if not server:
                print(f"Server '{server_id_or_name}' not found.")
                return None
            return server.to_dict()
        except Exception as e:
            print(f"Error getting server details for '{server_id_or_name}': {e}")
            return None

    def create_volume(self, name: str, size_gb: int, description: Optional[str] = None, image_name: Optional[str] = None, volume_type: Optional[str] = None, availability_zone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new block storage volume."""
        if not self._ensure_connection(): return None
        try:
            params = {'name': name, 'size': size_gb}
            if description: params['description'] = description
            if image_name:
                image = self.conn.image.find_image(image_name)
                if image: params['imageRef'] = image.id
                else: print(f"Image '{image_name}' not found."); return None
            if volume_type: params['volume_type'] = volume_type
            if availability_zone: params['availability_zone'] = availability_zone
            
            print(f"Creating volume '{name}' of size {size_gb}GB...")
            volume = self.conn.block_storage.create_volume(**params)
            self.conn.block_storage.wait_for_status(volume, status='available', timeout=300)
            print(f"Volume '{name}' created successfully.")
            return volume.to_dict()
        except Exception as e:
            print(f"Error creating volume: {e}"); return None

    def delete_volume(self, volume_id_or_name: str) -> bool:
        """Delete a block storage volume."""
        if not self._ensure_connection(): return False
        try:
            volume = self.conn.block_storage.find_volume(volume_id_or_name)
            if not volume: print(f"Volume '{volume_id_or_name}' not found."); return False
            print(f"Deleting volume '{volume.name}'...")
            self.conn.block_storage.delete_volume(volume.id)
            self.conn.block_storage.wait_for_delete(volume, timeout=300)
            print(f"Volume '{volume.name}' deleted.")
            return True
        except Exception as e:
            print(f"Error deleting volume: {e}"); return False

    def attach_volume_to_server(self, server_id_or_name: str, volume_id_or_name: str, device: Optional[str] = None) -> bool:
        """Attach a volume to a server."""
        if not self._ensure_connection(): return False
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            volume = self.conn.block_storage.find_volume(volume_id_or_name)
            if not server: print(f"Server '{server_id_or_name}' not found."); return False
            if not volume: print(f"Volume '{volume_id_or_name}' not found."); return False
            
            print(f"Attaching volume '{volume.name}' to server '{server.name}'...")
            self.conn.compute.create_server_volume(server.id, volume.id, device=device)
            # Wait for attachment - OpenStack SDK might not have a direct wait for this
            # Check volume status or server details for attachment confirmation if needed
            time.sleep(10) # Simple wait, can be improved
            print("Volume attached (assumed, check server details).")
            return True
        except Exception as e:
            print(f"Error attaching volume: {e}"); return False

    def detach_volume_from_server(self, server_id_or_name: str, volume_id_or_name: str) -> bool:
        """Detach a volume from a server."""
        if not self._ensure_connection(): return False
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            volume = self.conn.block_storage.find_volume(volume_id_or_name)
            if not server: print(f"Server '{server_id_or_name}' not found."); return False
            if not volume: print(f"Volume '{volume_id_or_name}' not found."); return False

            attachment_id = None
            for att in volume.attachments:
                if att['server_id'] == server.id:
                    attachment_id = att['attachment_id']
                    break
            if not attachment_id:
                print(f"Volume '{volume.name}' not attached to server '{server.name}'.")
                return False

            print(f"Detaching volume '{volume.name}' from server '{server.name}'...")
            self.conn.compute.delete_server_volume(server.id, attachment_id)
            # Wait for detachment
            time.sleep(10) # Simple wait
            print("Volume detached (assumed, check volume status).")
            return True
        except Exception as e:
            print(f"Error detaching volume: {e}"); return False

    def create_network_with_subnet(self, network_name: str, subnet_name: str, subnet_cidr: str, enable_dhcp: bool = True, dns_nameservers: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Create a network and a subnet within it."""
        if not self._ensure_connection(): return None
        try:
            print(f"Creating network '{network_name}'...")
            network = self.conn.network.create_network(name=network_name)
            # self.conn.network.wait_for_status(network, status='ACTIVE', failures=['ERROR'], interval=2, wait=120)
            
            subnet_params = {
                'network_id': network.id,
                'name': subnet_name,
                'ip_version': 4,
                'cidr': subnet_cidr,
                'enable_dhcp': enable_dhcp
            }
            if dns_nameservers:
                subnet_params['dns_nameservers'] = dns_nameservers
            
            print(f"Creating subnet '{subnet_name}' ({subnet_cidr}) in network '{network_name}'...")
            subnet = self.conn.network.create_subnet(**subnet_params)
            # self.conn.network.wait_for_status(subnet, status='ACTIVE', failures=['ERROR'], interval=2, wait=120)
            
            print(f"Network '{network_name}' and subnet '{subnet_name}' created.")
            return {'network': network.to_dict(), 'subnet': subnet.to_dict()}
        except Exception as e:
            print(f"Error creating network/subnet: {e}")
            # Cleanup if network was created but subnet failed
            if 'network' in locals() and network:
                try: self.conn.network.delete_network(network.id); print(f"Cleaned up network '{network.name}'.")
                except: pass
            return None

    def delete_network(self, network_id_or_name: str) -> bool:
        """Delete a network. Ensure subnets and ports are removed first if necessary."""
        if not self._ensure_connection(): return False
        try:
            network = self.conn.network.find_network(network_id_or_name)
            if not network: print(f"Network '{network_id_or_name}' not found."); return False
            
            # Basic check for attached ports (routers, VMs) - more robust checks might be needed
            ports = list(self.conn.network.ports(network_id=network.id))
            if ports:
                print(f"Network '{network.name}' has active ports. Please detach/delete them first.")
                for port in ports:
                    print(f"  - Port ID: {port.id}, Device: {port.device_owner or 'N/A'}")
                return False

            print(f"Deleting network '{network.name}'...")
            self.conn.network.delete_network(network.id)
            # No direct wait_for_delete for network in SDK, assume success or handle error
            print(f"Network '{network.name}' delete request sent.")
            return True
        except Exception as e:
            print(f"Error deleting network: {e}"); return False

    def resize_server(self, server_id_or_name: str, flavor_name: str) -> bool:
        """Resize a server to a new flavor."""
        if not self._ensure_connection(): return False
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            flavor = self.conn.compute.find_flavor(flavor_name)
            if not server: print(f"Server '{server_id_or_name}' not found."); return False
            if not flavor: print(f"Flavor '{flavor_name}' not found."); return False

            print(f"Resizing server '{server.name}' to flavor '{flavor.name}'...")
            self.conn.compute.resize_server(server.id, flavor.id)
            
            print(f"Waiting for server '{server.name}' to resize (status: VERIFY_RESIZE)...")
            self.conn.compute.wait_for_server(server, status='VERIFY_RESIZE', failures=['ERROR'], interval=5, wait=600)
            
            # User must confirm the resize
            print(f"Server '{server.name}' resized. Please confirm the resize manually or via API call to 'confirm_server_resize'.")
            # self.conn.compute.confirm_server_resize(server.id) # Uncomment to auto-confirm
            return True
        except Exception as e:
            print(f"Error resizing server: {e}"); return False

    def confirm_server_resize(self, server_id_or_name: str) -> bool:
        """Confirm a pending server resize."""
        if not self._ensure_connection(): return False
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            if not server: print(f"Server '{server_id_or_name}' not found."); return False
            if server.status != 'VERIFY_RESIZE':
                print(f"Server '{server.name}' is not in VERIFY_RESIZE state (current: {server.status}).")
                return False
            
            print(f"Confirming resize for server '{server.name}'...")
            self.conn.compute.confirm_server_resize(server.id)
            self.conn.compute.wait_for_server(server, status='ACTIVE', failures=['ERROR'], interval=2, wait=300)
            print(f"Resize confirmed for server '{server.name}'. Now ACTIVE.")
            return True
        except Exception as e:
            print(f"Error confirming server resize: {e}"); return False

    def revert_server_resize(self, server_id_or_name: str) -> bool:
        """Revert a pending server resize."""
        if not self._ensure_connection(): return False
        try:
            server = self.conn.compute.find_server(server_id_or_name)
            if not server: print(f"Server '{server_id_or_name}' not found."); return False
            if server.status != 'VERIFY_RESIZE':
                print(f"Server '{server.name}' is not in VERIFY_RESIZE state (current: {server.status}).")
                return False

            print(f"Reverting resize for server '{server.name}'...")
            self.conn.compute.revert_server_resize(server.id)
            self.conn.compute.wait_for_server(server, status='ACTIVE', failures=['ERROR'], interval=2, wait=300)
            print(f"Resize reverted for server '{server.name}'. Now ACTIVE with original flavor.")
            return True
        except Exception as e:
            print(f"Error reverting server resize: {e}"); return False

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
                    server = self.conn.compute.get_server(server.id) # Ensure full server object
                    server_usage = {
                        'id': server.id,
                        'name': server.name,
                        'status': server.status,
                        'created_at': server.created_at if hasattr(server, 'created_at') else None,
                        'networks': getattr(server, 'networks', {})
                    }
                    
                    # Get flavor details
                    if hasattr(server, 'flavor') and server.flavor:
                        flavor_id = server.flavor.get('id')
                        if flavor_id:
                            try:
                                flavor = self.conn.compute.get_flavor(flavor_id)
                                server_usage['flavor'] = {
                                    'name': flavor.name,
                                    'id': flavor.id,
                                    'vcpus': flavor.vcpus,
                                    'ram': flavor.ram,
                                    'disk': flavor.disk
                                }
                            except Exception as flavor_exc:
                                console.print(f"[yellow]Could not fetch details for flavor {flavor_id}: {flavor_exc}[/yellow]")
                                server_usage['flavor'] = {'id': flavor_id, 'error': str(flavor_exc)}
                    
                    # Get volume details
                    if hasattr(server, 'attached_volumes') and server.attached_volumes:
                        server_usage['volumes'] = []
                        for att in server.attached_volumes:
                            volume_id_to_fetch = att.get('id') or att.get('volumeId') # some versions use volumeId
                            if volume_id_to_fetch:
                                try:
                                    vol = self.conn.block_storage.get_volume(volume_id_to_fetch)
                                    server_usage['volumes'].append({
                                        'id': vol.id,
                                        'name': vol.name,
                                        'size': vol.size,
                                        'status': vol.status
                                    })
                                except Exception as vol_exc:
                                    console.print(f"[yellow]Could not fetch details for attached volume {volume_id_to_fetch}: {vol_exc}[/yellow]")
                                    server_usage['volumes'].append({'id': volume_id_to_fetch, 'error': str(vol_exc)})
                            else:
                                console.print(f"[yellow]Attached volume entry found without an ID: {att}[/yellow]")
                    
                    result['server_usage'] = server_usage
                else:
                    result['server_usage'] = {'error': f"Server '{server_id_or_name}' not found"}
            
            return result
        except Exception as e:
            console.print(f"[bold red]Error getting usage statistics: {e}[/bold red]")
            return {'error': str(e)}

# --- End of OpenStackAPI Class ---

# --- OpenStackAgent Class (from agent.py) ---
# Configuration for OpenStackAgent
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # It's better to get this from env
DEFAULT_PARAMS_MAP = {
    'create_server': {
        'network_name': 'default-private-net',
        'volume_size': 10,
        'flavor_name': 'm1.small',
        'image_name': 'Ubuntu-20.04',
    },
    'create_volume': {
        'name': 'default-volume',
        'size_gb': 10,
    },
    'create_network_with_subnet': {
        'subnet_cidr': '192.168.100.0/24',
        'subnet_name': 'default-subnet',
    },
    'resize_server': {
        'flavor_name': 'm1.medium',
    },
}

if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY not set in environment variables. AI functionality will be limited or fail.")
    # Provide a way for the user to input it, or use a default/placeholder if appropriate for the context
    # For now, we'll let it proceed, but genai.configure might fail or functionalities will be impacted.
    # GOOGLE_API_KEY = "YOUR_FALLBACK_API_KEY_OR_PROMPT_LOGIC_HERE"

# Configure Google AI (genai) if API key is available
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error configuring Google AI: {e}. AI features may not work.")
else:
    print("Google AI not configured as GOOGLE_API_KEY is missing.")

class OpenStackAgent:
    """The AI agent to interact with OpenStack."""

    def __init__(self):
        self.openstack_api = OpenStackAPI() # Uses the consolidated OpenStackAPI
        if GOOGLE_API_KEY: # Initialize model only if API key is present and configured
            try:
                self.model = genai.GenerativeModel('gemma-3-27b-it') # Consider making model configurable
                self.validation_model = self.model
            except Exception as e:
                print(f"Failed to initialize GenerativeModel: {e}. AI features will be impacted.")
                self.model = None
                self.validation_model = None
        else:
            self.model = None
            self.validation_model = None
            print("OpenStackAgent initialized without AI model due to missing GOOGLE_API_KEY.")

        self.default_params_map = DEFAULT_PARAMS_MAP
        self.last_execution_time = None
        self.api_methods = self._get_api_methods()
        print("Agent initialized.")

    def _get_api_methods(self) -> Dict[str, Dict[str, Any]]:
        """Inspects OpenStackAPI to find public methods and their parameters."""
        methods = {}
        for name, func in inspect.getmembers(self.openstack_api):
            if not name.startswith('_') and inspect.isroutine(func):
                # Exclude methods that are not part of the direct operational API for the agent
                if name in ['connect', '_ensure_connection']:
                    continue
                sig = inspect.signature(func)
                params = {}
                for param_name, param in sig.parameters.items():
                    params[param_name] = {
                        'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                        'required': param.default == inspect.Parameter.empty,
                        'default': (None if param.default == inspect.Parameter.empty else param.default)
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
        """Creates the prompt for the Gemini model."""
        prompt = f"You are an assistant that translates natural language requests into OpenStack API calls.\n"
        prompt += f"Based on the user's request: '{user_query}', identify the correct OpenStack operation and extract the necessary parameters.\n\n"
        prompt += "Available OpenStack Operations:\n"
        prompt += self._get_api_methods_formatted()
        prompt += "\nSpecial Notes:\n"
        prompt += "- For create_volume, required fields are name (str) and size_gb (int).\n"
        prompt += "- For create_server, required fields are name, flavor_name, image_name; network_name and volume_size are optional.\n"
        prompt += "- For commands with parameters, include only parameters explicitly mentioned or clearly inferable.\n"
        prompt += "Please respond ONLY with a JSON object containing:\n"
        prompt += "1. 'function_name': The name of the function to call.\n"
        prompt += "2. 'parameters': A dictionary of parameter names and their extracted values from the user query.\n"
        prompt += "   - Include in 'parameters' only those parameters whose values can be extracted or inferred.\n"
        prompt += "   - If a parameter cannot be determined, do not include it in 'parameters'.\n"
        prompt += "   - Do NOT include placeholder values like 'Please provide...'.\n"
        prompt += "Example Response for 'create a volume named myvol':\n"
        prompt += '{"function_name": "create_volume", "parameters": {"name": "myvol"}}\n'
        prompt += "If unclear, respond with: {'function_name': 'clarify', 'parameters': {}}\n"
        prompt += "Response JSON:"
        return prompt

    def _generate_validation_prompt(self, user_query: str, generated_command: Dict[str, Any]) -> str:
        """Creates the validation prompt."""
        prompt = f"Validate if the command reflects the user's query: '{user_query}'\n"
        prompt += f"Generated command:\n  Function: {generated_command.get('function_name')}\n  Parameters: {json.dumps(generated_command.get('parameters', {}))}\n"
        prompt += "Available Operations:\n" + self._get_api_methods_formatted()
        prompt += "\nNotes:\n"
        prompt += "- For create_volume, ensure name and size_gb are present.\n"
        prompt += "- For create_server, ensure name, flavor_name, image_name are present; network_name and volume_size are optional.\n"
        prompt += "Respond with JSON: {'is_valid': <bool>, 'feedback': '<str>', 'missing_parameters_based_on_intent': [<str>], 'suggested_corrections': {<str>: <str>}}\n"
        prompt += "- Do NOT suggest placeholder values like 'Please provide...'.\n"
        prompt += "- List missing required parameters in 'missing_parameters_based_on_intent'.\n"
        prompt += "- Only suggest corrections for parameters explicitly inferable from the query.\n"
        prompt += "Response JSON:"
        return prompt

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parses JSON response from AI."""
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError as e:
                    console.print(f"[red]JSON parse failed after fix: {e}[/red]")
            return None

    def _generate_initial_command_with_ai(self, user_query: str) -> Dict[str, Any]:
        """Generates initial command using AI."""
        prompt = self._generate_ai_prompt(user_query)
        try:
            response = self.model.generate_content(prompt)
            parsed = self._parse_json_response(response.text)
            return parsed if parsed else {"function_name": "clarify", "parameters": {}}
        except Exception as e:
            console.print(f"[red]AI error (Layer 1): {e}[/red]")
            return {"function_name": "clarify", "parameters": {}}

    def _validate_command_with_ai(self, user_query: str, generated_command: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the command."""
        prompt = self._generate_validation_prompt(user_query, generated_command)
        try:
            response = self.validation_model.generate_content(prompt)
            parsed = self._parse_json_response(response.text)
            if parsed and "is_valid" in parsed:
                parsed.setdefault("feedback", "")
                parsed.setdefault("missing_parameters_based_on_intent", [])
                parsed.setdefault("suggested_corrections", {})
                return parsed
            return {"is_valid": False, "feedback": "Validation failed.", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}
        except Exception as e:
            console.print(f"[red]AI error (Layer 2): {e}[/red]")
            return {"is_valid": False, "feedback": f"Validation error: {e}", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}

    def _get_missing_parameters(self, function_name: str, provided_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Identifies missing or None-valued required parameters."""
        missing = {}
        if function_name not in self.api_methods:
            return {}
        required_params = self.api_methods[function_name]['params']
        for param_name, details in required_params.items():
            if details['required']:
                if param_name not in provided_params or provided_params[param_name] is None:
                    missing[param_name] = details
        return missing

    def _prompt_for_parameters(self, function_name: str, missing_params: Dict[str, Dict[str, Any]], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Prompts user for missing parameters and informs about optional ones."""
        collected = {}
        console.print("\n[bold]Required parameters:[/bold]")
        
        # First prompt for required parameters
        for name, details in missing_params.items():
            while True:
                value = Prompt.ask(f"  - {name} (Type: {details['type']})").strip()
                if value.lower() in ['default', 'your choice']:
                    default_val = self.default_params_map.get(function_name, {}).get(name)
                    if default_val is not None:
                        console.print(f"    Using default: {default_val}")
                        collected[name] = default_val
                        break
                    else:
                        console.print(f"[yellow]    No default for '{name}'. Please specify.[/yellow]")
                elif value:
                    try:
                        if details['type'] == 'int':
                            collected[name] = int(value)
                        elif details['type'] == 'bool':
                            collected[name] = value.lower() in ['true', 'yes', '1']
                        else:
                            collected[name] = value
                        break
                    except ValueError:
                        console.print(f"[yellow]    Please enter a valid {details['type']}.[/yellow]")
                else:
                    console.print("[yellow]    Required parameter cannot be empty.[/yellow]")
        
        # Inform about optional parameters with defaults
        optional_params = self.api_methods[function_name]['params']
        console.print("\n[bold]Optional parameters with defaults:[/bold]")
        for param, details in optional_params.items():
            if not details['required'] and param not in collected and param not in missing_params:
                default_val = self.default_params_map.get(function_name, {}).get(param, details['default'])
                console.print(f"  - {param} (Type: {details['type']}, Default: {default_val})")
        
        return collected

    def execute_command(self, user_query: str):
        """Executes the command after validation and parameter collection."""
        if not self.model or not self.validation_model:
            console.print("[red]AI models are not initialized. Cannot process command. Check GOOGLE_API_KEY.[/red]")
            return

        initial_intent = self._generate_initial_command_with_ai(user_query)
        if initial_intent.get('function_name') == 'clarify':
            console.print("[yellow]Unclear request. Please provide more details.[/yellow]")
            return

        console.print(Text.assemble(Text("\nLayer 1 - Initial AI Intent:\n", style="bold underline"),
                                  Text(f"  Function: ", style="bold"), Text(str(initial_intent.get('function_name')), style="cyan"),
                                  Text(f"\n  Parameters: ", style="bold"), Text(str(initial_intent.get('parameters')), style="white")))

        validation = self._validate_command_with_ai(user_query, initial_intent)
        console.print(Text.assemble(Text("\nLayer 2 - Validation Result:\n", style="bold underline"),
                                  Text(f"  Is Valid: ", style="bold"), Text(str(validation.get('is_valid')), style="cyan" if validation.get('is_valid') else "red"),
                                  Text(f"\n  Feedback: ", style="bold"), Text(str(validation.get('feedback'))),
                                  Text(f"\n  Missing by Intent: ", style="bold"), Text(str(validation.get('missing_parameters_based_on_intent'))),
                                  Text(f"\n  Suggested Corrections: ", style="bold"), Text(str(validation.get('suggested_corrections')))))

        final_function_name = initial_intent['function_name']
        final_params = initial_intent.get('parameters', {}).copy()

        if validation.get("suggested_corrections"):
            for param, value in validation.get("suggested_corrections").items():
                if not str(value).startswith("Please provide"):
                    final_params[param] = value

        missing_required_params = self._get_missing_parameters(final_function_name, final_params)
        if missing_required_params:
            console.print(f"[yellow]Missing required parameters: {', '.join(missing_required_params.keys())}[/yellow]")
            collected = self._prompt_for_parameters(final_function_name, missing_required_params, final_params)
            final_params.update(collected)

        remaining_missing = self._get_missing_parameters(final_function_name, final_params)
        if remaining_missing:
            console.print(f"[red]Cannot proceed. Still missing required parameters: {', '.join(remaining_missing.keys())}[/red]")
            return

        console.print(Text.assemble(Text("\nExecuting Command:\n", style="bold underline"),
                                  Text(f"  Function: ", style="bold"), Text(str(final_function_name), style="green"),
                                  Text(f"\n  Parameters: ", style="bold"), Pretty(final_params)))
        
        if not self.openstack_api.connect(): # Ensure connection before calling API method
            console.print("[red]Failed to connect to OpenStack. Cannot execute command.[/red]")
            return

        api_function = getattr(self.openstack_api, final_function_name, None)
        if api_function:
            try:
                accepted_params_spec = inspect.signature(api_function).parameters
                filtered_params = {k: v for k, v in final_params.items() if k in accepted_params_spec}
                
                start_time = time.time()
                output = api_function(**filtered_params)
                self.last_execution_time = time.time() - start_time
                console.print("\n[bold green]Execution Successful![/bold green]")
                if output is not None:
                    console.print(Text("Output:", style="bold"))
                    console.print(Pretty(output))
                console.print(f"Execution Time: {self.last_execution_time:.2f} seconds")
            except Exception as e:
                console.print(f"\n[bold red]Execution failed: {e}[/bold red]")
                if "401" in str(e):
                    console.print("[yellow]Hint: Authentication error (HTTP 401). Please verify your OpenStack credentials (environment variables or prompted values).[/yellow]")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        else:
            console.print(f"[red]Error: Function '{final_function_name}' not found in OpenStackAPI.[/red]")

            # 'default': (None if param.default == inspect.Parameter.empty else param.default)
                

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
        """Creates the prompt for the Gemini model."""
        prompt = f"You are an assistant that translates natural language requests into OpenStack API calls.\n"
        prompt += f"Based on the user's request: '{user_query}', identify the correct OpenStack operation and extract the necessary parameters.\n\n"
        prompt += "Available OpenStack Operations:\n"
        prompt += self._get_api_methods_formatted()
        prompt += "\nSpecial Notes:\n"
        prompt += "- For create_volume, required fields are name (str) and size_gb (int).\n"
        prompt += "- For create_server, required fields are name, flavor_name, image_name; network_name and volume_size are optional.\n"
        prompt += "- For commands with parameters, include only parameters explicitly mentioned or clearly inferable.\n"
        prompt += "Please respond ONLY with a JSON object containing:\n"
        prompt += "1. 'function_name': The name of the function to call.\n"
        prompt += "2. 'parameters': A dictionary of parameter names and their extracted values from the user query.\n"
        prompt += "   - Include in 'parameters' only those parameters whose values can be extracted or inferred.\n"
        prompt += "   - If a parameter cannot be determined, do not include it in 'parameters'.\n"
        prompt += "   - Do NOT include placeholder values like 'Please provide...'.\n"
        prompt += "Example Response for 'create a volume named myvol':\n"
        prompt += '{"function_name": "create_volume", "parameters": {"name": "myvol"}}\n'
        prompt += "If unclear, respond with: {'function_name': 'clarify', 'parameters': {}}\n"
        prompt += "Response JSON:"
        return prompt

    def _generate_validation_prompt(self, user_query: str, generated_command: Dict[str, Any]) -> str:
        """Creates the validation prompt."""
        prompt = f"Validate if the command reflects the user's query: '{user_query}'\n"
        prompt += f"Generated command:\n  Function: {generated_command.get('function_name')}\n  Parameters: {json.dumps(generated_command.get('parameters', {}))}\n"
        prompt += "Available Operations:\n" + self._get_api_methods_formatted()
        prompt += "\nNotes:\n"
        prompt += "- For create_volume, ensure name and size_gb are present.\n"
        prompt += "- For create_server, ensure name, flavor_name, image_name are present; network_name and volume_size are optional.\n"
        prompt += "Respond with JSON: {'is_valid': <bool>, 'feedback': '<str>', 'missing_parameters_based_on_intent': [<str>], 'suggested_corrections': {<str>: <str>}}\n"
        prompt += "- Do NOT suggest placeholder values like 'Please provide...'.\n"
        prompt += "- List missing required parameters in 'missing_parameters_based_on_intent'.\n"
        prompt += "- Only suggest corrections for parameters explicitly inferable from the query.\n"
        prompt += "Response JSON:"
        return prompt

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parses JSON response from AI."""
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError as e:
                    print(f"JSON parse failed after fix: {e}")
            return None

    def _generate_initial_command_with_ai(self, user_query: str) -> Dict[str, Any]:
        """Generates initial command using AI."""
        if not self.model:
            print("AI model not available for generating command.")
            return {"function_name": "clarify", "parameters": {"error": "AI model not initialized"}}
        prompt = self._generate_ai_prompt(user_query)
        try:
            response = self.model.generate_content(prompt)
            parsed = self._parse_json_response(response.text)
            return parsed if parsed else {"function_name": "clarify", "parameters": {}}
        except Exception as e:
            print(f"AI error (Layer 1): {e}")
            return {"function_name": "clarify", "parameters": {}}

    def _validate_command_with_ai(self, user_query: str, generated_command: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the command."""
        if not self.validation_model:
            print("AI model not available for validating command.")
            return {"is_valid": False, "feedback": "AI model not initialized for validation.", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}
        prompt = self._generate_validation_prompt(user_query, generated_command)
        try:
            response = self.validation_model.generate_content(prompt)
            parsed = self._parse_json_response(response.text)
            if parsed and "is_valid" in parsed:
                parsed.setdefault("feedback", "")
                parsed.setdefault("missing_parameters_based_on_intent", [])
                parsed.setdefault("suggested_corrections", {})
                return parsed
            return {"is_valid": False, "feedback": "Validation failed.", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}
        except Exception as e:
            print(f"AI error (Layer 2): {e}")
            return {"is_valid": False, "feedback": f"Validation error: {e}", "missing_parameters_based_on_intent": [], "suggested_corrections": {}}

    def _get_missing_parameters(self, function_name: str, provided_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Identifies missing or None-valued required parameters."""
        missing = {}
        if function_name not in self.api_methods:
            return {}
        required_params = self.api_methods[function_name]['params']
        for param_name, details in required_params.items():
            if details['required']:
                if param_name not in provided_params or provided_params[param_name] is None:
                    missing[param_name] = details
        return missing

    def _prompt_for_parameters(self, function_name: str, missing_params: Dict[str, Dict[str, Any]], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Prompts user for missing parameters."""
        collected = {}
        console.print("\nPlease provide the following required parameters (or type 'default' or 'your choice' for default values):")
        for name, details in missing_params.items():
            while True:
                # Use Rich Prompt if available, otherwise fallback
                value = Prompt.ask(f"  - {name} (Type: {details['type']})").strip()
                if value.lower() in ['default', 'your choice']:
                    default_val = self.default_params_map.get(function_name, {}).get(name)
                    if default_val is not None:
                        console.print(f"    Using default: {default_val}")
                        collected[name] = default_val
                        break
                    else:
                        console.print(f"    No default for '{name}'. Please specify.")
                elif value:
                    try:
                        if details['type'] == 'int':
                            collected[name] = int(value)
                        elif details['type'] == 'bool': # Basic bool conversion
                            collected[name] = value.lower() in ['true', 'yes', '1', 'y']
                        else:
                            collected[name] = value
                        break
                    except ValueError:
                        console.print(f"    Please enter a valid {details['type']}.")
                else:
                    console.print("    Required parameter cannot be empty.")
        return collected

    def execute_command(self, user_query: str, is_web: bool = False) -> Any:
        """Executes the command after validation and parameter collection."""
        if not self.model or not self.validation_model:
            error_msg = "AI models are not initialized. Cannot process command."
            print(error_msg)
            if is_web:
                return {'status': 'error', 'message': error_msg}
            return None # Or raise an exception

        initial_intent = self._generate_initial_command_with_ai(user_query)
        if initial_intent.get('function_name') == 'clarify':
            clarify_msg = "Unclear request. Please provide more details or rephrase."
            if 'error' in initial_intent.get('parameters', {}):
                 clarify_msg = f"AI Error: {initial_intent['parameters']['error']}. {clarify_msg}"
            print(clarify_msg)
            if is_web:
                return {'status': 'clarification_needed', 'message': clarify_msg}
            return None

        print(f"\nLayer 1 - Function: {initial_intent.get('function_name')}, Parameters: {initial_intent.get('parameters')}")

        validation = self._validate_command_with_ai(user_query, initial_intent)
        print(f"Layer 2 - Valid: {validation.get('is_valid')}, Feedback: {validation.get('feedback')}")
        print(f"Missing by Intent: {validation.get('missing_parameters_based_on_intent')}")
        print(f"Suggested Corrections: {validation.get('suggested_corrections')}")

        final_function_name = initial_intent['function_name']
        final_params = initial_intent.get('parameters', {}).copy()

        if validation.get("suggested_corrections"):
            for param, value in validation.get("suggested_corrections").items():
                if not str(value).startswith("Please provide"): # Ensure value is string for startswith
                    final_params[param] = value
        
        # Handle missing parameters based on AI's understanding of intent
        # This part is tricky; for web, we might want to return these missing params to the UI
        if is_web and validation.get('missing_parameters_based_on_intent'):
            missing_for_web = validation['missing_parameters_based_on_intent']
            # Further check if these are truly required by the function signature
            truly_missing_params_details = self._get_missing_parameters(final_function_name, final_params)
            truly_missing_param_names = list(truly_missing_params_details.keys())
            
            # We only report as 'missing_parameters' if they are genuinely required by the function and not yet provided.
            if any(p_name in truly_missing_param_names for p_name in missing_for_web):
                return {
                    'status': 'missing_parameters',
                    'function_name': final_function_name,
                    'provided_parameters': final_params,
                    'missing_parameters': {p:truly_missing_params_details[p] for p in truly_missing_param_names if p in missing_for_web and p in truly_missing_params_details},
                    'message': f"Missing parameters for {final_function_name}: {', '.join(p for p in missing_for_web if p in truly_missing_param_names)}"
                }

        # For CLI, or if web didn't return above, proceed to prompt for any remaining hard-required params
        missing_params_details = self._get_missing_parameters(final_function_name, final_params)
        if missing_params_details:
            if is_web:
                # If it's a web request and we still have missing *required* params not caught by intent, report them.
                return {
                    'status': 'missing_parameters',
                    'function_name': final_function_name,
                    'provided_parameters': final_params,
                    'missing_parameters': missing_params_details,
                    'message': f"Core required parameters for {final_function_name} are missing: {', '.join(missing_params_details.keys())}"
                }
            else: # CLI mode, prompt the user
                print(f"Missing required parameters: {', '.join(missing_params_details.keys())}")
                collected = self._prompt_for_parameters(final_function_name, missing_params_details, final_params)
                final_params.update(collected)
        
        # Final check for CLI after prompting
        if not is_web:
            remaining_missing = self._get_missing_parameters(final_function_name, final_params)
            if remaining_missing:
                error_msg = f"Cannot proceed. Missing required parameters: {', '.join(remaining_missing.keys())}"
                print(error_msg)
                return None # Or raise an exception for CLI

        print(f"\nExecuting {final_function_name} with parameters: {final_params}")
        if not self.openstack_api.connect(): # Ensure connection before executing
            connect_error = "Failed to connect to OpenStack."
            print(connect_error)
            if is_web:
                return {'status': 'error', 'message': connect_error}
            return None

        api_function = getattr(self.openstack_api, final_function_name, None)
        if api_function:
            try:
                accepted_params_spec = inspect.signature(api_function).parameters
                filtered_params = {k: v for k, v in final_params.items() if k in accepted_params_spec}
                
                start_time = time.time()
                output = api_function(**filtered_params)
                self.last_execution_time = time.time() - start_time
                
                success_msg = f"Command '{final_function_name}' executed successfully."
                print(f"\n{success_msg}")
                if output:
                    print(f"Output: {json.dumps(output, indent=2) if isinstance(output, (dict, list)) else output}")
                print(f"Time: {self.last_execution_time:.2f} seconds")
                
                if is_web:
                    return {'status': 'success', 'result': output, 'execution_time': self.last_execution_time}
                return output
            except Exception as e:
                exec_error = f"Execution failed for '{final_function_name}': {e}"
                print(f"\n{exec_error}")
                if "401" in str(e):
                    print("Authentication error (HTTP 401). Please verify your OpenStack credentials.")
                if is_web:
                    return {'status': 'error', 'message': exec_error}
                return None # Or raise for CLI
        else:
            not_found_msg = f"Function '{final_function_name}' not found in OpenStackAPI."
            print(not_found_msg)
            if is_web:
                return {'status': 'error', 'message': not_found_msg}
            return None
# --- End of OpenStackAgent Class ---

# --- Runner Components (from runner.py) ---

# Configuration and context management (from runner.py)
class ChatbotConfig:
    def __init__(self):
        self.verbose = False
        self.output_format = "pretty"  # Options: pretty, json, raw
        self.language = "en"
        self.load_config()

    def load_config(self):
        config_file = "chatbot_config.json" # This will be relative to where consolidated_chatbot.py is run
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.verbose = config.get("verbose", False)
                    self.output_format = config.get("output_format", "pretty")
                    self.language = config.get("language", "en")
            except json.JSONDecodeError:
                print(f"Error reading {config_file}. Using default configuration.")
            except Exception as e:
                print(f"Unexpected error loading {config_file}: {e}. Using default configuration.")
        else:
            print(f"{config_file} not found. Using default configuration.")

    def save_config(self):
        config = {
            "verbose": self.verbose,
            "output_format": self.output_format,
            "language": self.language
        }
        try:
            with open("chatbot_config.json", 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Configuration saved to chatbot_config.json")
        except Exception as e:
            print(f"Error saving configuration: {e}")

class ConversationContext:
    def __init__(self, max_history=10):
        self.history = deque(maxlen=max_history)
        self.current_context = None

    def add_to_history(self, command, output):
        self.history.append({"command": command, "output": output, "timestamp": datetime.now().isoformat()})

    def get_history(self):
        return list(self.history)

    def set_current_context(self, context):
        self.current_context = context

    def get_current_context(self):
        return self.current_context

# Setup logging (from runner.py)
# Ensure the log file is created where the script is run, or specify an absolute path.
logging.basicConfig(filename="consolidated_chatbot.log", level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Enhanced help with examples and settings (from runner.py)
def display_help(config):
    help_text = Text.assemble(
        ("Welcome to the OpenStack AI Chatbot Assistant!\n\n", "bold white"),
        ("Basic Commands:\n", "bold purple"),
        ("- list all servers: ", "italic magenta"), ("Lists all servers.\n", "white"),
        ("- create a new server named [name]: ", "italic magenta"), ("Creates a server.\n", "white"),
        ("- delete server with ID [ID]: ", "italic magenta"), ("Deletes a server.\n", "white"),
        ("- show details of server with ID [ID]: ", "italic magenta"), ("Shows server details.\n", "white"),
        ("\nAdvanced Commands:\n", "bold purple"),
        ("- set verbose on/off: ", "italic blue"), ("Toggles verbose mode.\n", "white"),
        ("- set output format [pretty/json/raw]: ", "italic blue"), ("Changes output style.\n", "white"),
        ("- history: ", "italic blue"), ("Shows command history.\n", "white"),
        ("- tutorial: ", "italic blue"), ("Starts an interactive tutorial.\n", "white"),
        ("\nExamples:\n", "bold purple"),
        ("- 'list all servers' then 'show details of the first one'\n", "white"),
        ("- 'create a new server named test-vm with flavor m1.small'\n", "white"),
        ("\nTips:\n", "italic yellow"),
        ("- Use 'it' or 'that' to refer to the last output.\n", "white"),
        ("- Current settings: Verbose=", "white"), (str(config.verbose), "bold green" if config.verbose else "bold red"),
        (", Format=", "white"), (config.output_format, "bold cyan"), ("\n", "white")
    )
    console.print(Panel(help_text, title="[bold purple]Chatbot Help[/bold purple]", border_style="purple"))

# Interactive tutorial (from runner.py)
def run_tutorial(agent: OpenStackAgent, context: ConversationContext, config: ChatbotConfig):
    console.print(Panel(Text("Starting interactive tutorial...", style="bold cyan"), title="Tutorial", border_style="cyan"))
    steps = [
        ("Let's list all servers. Type: 'list all servers'", lambda x: "list all" in x.lower() and "servers" in x.lower()),
        ("Great! Now, refer to the last output. Try: 'show details of the first one'", 
         lambda x: "show details" in x.lower() and ("first" in x.lower() or "it" in x.lower())),
        ("Nice! Let's create a server. Type: 'create a new server named tutorial-vm'", 
         lambda x: "create" in x.lower() and "server" in x.lower() and "tutorial-vm" in x.lower())
    ]
    for step, validator in steps:
        while True:
            user_input = Prompt.ask(f"\n[bold blue]{step}[/bold blue]")
            if validator(user_input):
                try:
                    # The agent.execute_command might return different structures now (dict for web)
                    # For CLI tutorial, we expect direct output or None
                    output = agent.execute_command(user_input, is_web=False)
                    context.add_to_history(user_input, output)
                    context.set_current_context(output if isinstance(output, list) else [output])
                    console.print(Panel(format_output(output, config), title="Step Output", border_style="green")) # Use format_output
                    break
                except Exception as e:
                    console.print(Text(f"Error: {e}. Try again!", style="red"))
            else:
                console.print(Text("That’s not quite right. Try again!", style="yellow"))

# Parse follow-up queries (from runner.py)
def parse_follow_up(user_input, current_context_data):
    # current_context_data is expected to be the 'result' part of the agent's output if it was a successful command,
    # or the direct output if not structured with 'status'.
    if not current_context_data or not isinstance(current_context_data, list):
        # If it's a dict (like from a single server detail), wrap it in a list
        if isinstance(current_context_data, dict) and 'id' in current_context_data:
             current_context_data = [current_context_data]
        else:
            return None # Cannot parse if not a list of dicts or a single dict with id

    target_item = None
    if "first" in user_input and current_context_data:
        target_item = current_context_data[0]
    elif "second" in user_input and len(current_context_data) > 1:
        target_item = current_context_data[1]
    elif "last" in user_input and current_context_data:
        target_item = current_context_data[-1]
    
    if target_item and isinstance(target_item, dict):
        return target_item.get("id")
    elif target_item: # If it's not a dict but some other value (e.g., a simple string list)
        return str(target_item)
        
    # Fallback for specific ID parsing if general terms don't match
    match_id = re.search(r"(server|network|volume|image|flavor)\s+(?:with\s+ID|ID|named)\s+([\w\-]+)", user_input, re.IGNORECASE)
    if match_id:
        # This part might be too simplistic if the context isn't just a list of items with IDs.
        # For now, it assumes the user is referring to an ID that might be in the context or a new one.
        return match_id.group(2)
    return None

# Format output (from runner.py)
def format_output(output, config: ChatbotConfig):
    if output is None:
        return Text("Command executed successfully. No direct output to display.", style="italic green")
    
    # Handle agent's structured response for web/API calls if it slips into CLI formatting
    if isinstance(output, dict) and 'status' in output:
        if output['status'] == 'success':
            actual_result = output.get('result')
            if actual_result is None:
                 return Text("Command successful, no specific result data returned.", style="green")
            output = actual_result # Process the actual result
        elif output['status'] == 'error':
            return Text(f"Error: {output.get('message', 'Unknown error from agent.')}", style="red")
        elif output['status'] == 'missing_parameters':
            return Text(f"Missing parameters: {output.get('message', 'Parameters are required.')}", style="yellow")
        elif output['status'] == 'clarification_needed':
            return Text(f"Clarification needed: {output.get('message', 'Please rephrase.')}", style="yellow")
        else:
            return Pretty(output, expand_all=True) # Fallback for unknown status

    if config.output_format == "json":
        try:
            return Pretty(json.dumps(output, indent=2))
        except TypeError: # Handle non-serializable objects if any
            return Pretty(str(output))
    elif config.output_format == "raw":
        return Text(str(output))
    else:  # pretty (default)
        if isinstance(output, list) and output and isinstance(output[0], dict):
            table = Table(title="Results")
            # Dynamically get keys from the first item, assuming homogeneity
            keys = list(output[0].keys())
            for key in keys:
                table.add_column(key.replace('_', ' ').capitalize(), style="blue")
            for item in output:
                table.add_row(*[str(item.get(k, "")) for k in keys])
            return table
        elif isinstance(output, dict): # Handle single dictionary output prettily
            table = Table(title="Details")
            table.add_column("Property", style="blue")
            table.add_column("Value", style="white")
            for key, value in output.items():
                table.add_row(key.replace('_', ' ').capitalize(), str(value))
            return table
        return Pretty(output, expand_all=True) # Fallback for other types

# CLI runner (from runner.py)
def run_cli(remote_url=None):
    welcome_ascii = (
        "╭────────────── OpenStack AI Agent ───────────────╮\n"
        "│ Welcome to the OpenStack AI Agent v1.0          │\n"
        "│                                                 │\n"
        "│ Interact with OpenStack using natural language. │\n"
        "│ Try commands like:                              │\n"
        "│ - 'list all servers'                            │\n"
        "│ - 'create a new server named my-vm'             │\n"
        "│ - 'show details of server with ID 1234'         │\n"
        "│                                                 │\n"
        "│ Type 'help' for commands or 'exit' to quit.     │\n"
        "╰─────────────────────────────────────────────────╯\n"
        "   🚀 Powered by Consolidated Chatbot Script! 🚀    "
    )
    if RICH_AVAILABLE:
        console.print(Panel(Text(welcome_ascii, style="bold cyan"), title="", border_style="cyan", expand=False))
    else:
        print(welcome_ascii)

    config = ChatbotConfig()
    context = ConversationContext()
    agent = None
    if not remote_url:
        # Uses the consolidated OpenStackAgent
        agent = OpenStackAgent() 
        if not agent.openstack_api.connect(): # Initial connection attempt
            console.print(Panel(Text("Failed to connect to OpenStack on startup. Check credentials and API endpoint.", style="bold red"), title="Connection Error"))
            # Decide if to exit or allow commands that don't need OpenStack

    while True:
        try:
            user_input = Prompt.ask("\n[bold purple]➜ Command[/bold purple]", default="help")
            user_input = user_input.strip()

            if user_input.lower() in ["exit", "quit"]:
                console.print(Panel(Text("Goodbye!", style="yellow"), title="Session Ended", border_style="yellow"))
                break

            if user_input.lower() == "help":
                display_help(config)
                continue

            if user_input.lower() == "tutorial":
                if agent: # Tutorial needs a local agent
                    run_tutorial(agent, context, config)
                else:
                    console.print(Text("Tutorial requires a local agent. Cannot run in remote mode.", style="yellow"))
                continue

            if user_input.lower() == "history":
                history = context.get_history()
                if not history:
                    console.print(Text("No command history yet.", style="italic"))
                    continue
                table = Table(title="Command History")
                table.add_column("Timestamp", style="dim cyan")
                table.add_column("Command", style="bold magenta")
                table.add_column("Output Preview", style="white")
                for entry in history:
                    output_prev = str(entry["output"])[:50] + "..." if len(str(entry["output"])) > 50 else str(entry["output"])
                    table.add_row(entry["timestamp"], entry["command"], output_prev)
                console.print(table)
                continue

            if user_input.lower().startswith("set verbose"):
                config.verbose = "on" in user_input.lower()
                config.save_config()
                console.print(Text(f"Verbose mode {'enabled' if config.verbose else 'disabled'}.", style="green"))
                continue
            elif user_input.lower().startswith("set output format"):
                fmt_match = re.search(r"format\s+(pretty|json|raw)", user_input.lower())
                if fmt_match:
                    config.output_format = fmt_match.group(1)
                    config.save_config()
                    console.print(Text(f"Output format set to {config.output_format}.", style="green"))
                else:
                    console.print(Text("Invalid format. Use: pretty, json, raw.", style="red"))
                continue

            # Handle follow-up queries like 'it', 'that', 'first', etc.
            if any(ref in user_input.lower().split() for ref in ["it", "that", "first", "second", "last"]):
                last_command_output = context.get_current_context()
                if last_command_output:
                    # The context might be the direct result or a structured dict from agent
                    data_for_parsing = last_command_output
                    if isinstance(last_command_output, dict) and 'status' in last_command_output and last_command_output['status'] == 'success':
                        data_for_parsing = last_command_output.get('result')
                    
                    target_id = parse_follow_up(user_input, data_for_parsing)
                    if target_id:
                        # Replace the reference word (e.g., 'it') with the resolved ID
                        # This is a simple replacement; more robust parsing might be needed for complex sentences.
                        user_input = re.sub(r"\b(it|that|first|second|last)\b", str(target_id), user_input, count=1, flags=re.IGNORECASE)
                        console.print(Text(f"Interpreted as: '{user_input}'", style="dim cyan"))
                    else:
                        console.print(Panel(Text("Cannot resolve reference from prior context.", style="red"), title="Error"))
                        continue
                else:
                    console.print(Panel(Text("No prior context available to resolve reference.", style="red"), title="Error"))
                    continue
            
            status_message = f"[yellow]Processing: '{user_input}'[/yellow]"
            if RICH_AVAILABLE:
                with console.status(status_message, spinner="dots") as status_indicator:
                    command_output = None
                    if remote_url:
                        try:
                            payload = {'command': user_input}
                            response = requests.post(f"{remote_url.rstrip('/')}/command", json=payload, timeout=30)
                            response.raise_for_status()
                            json_response = response.json()
                            if 'result' in json_response:
                                command_output = json_response['result']
                            elif 'error' in json_response:
                                raise Exception(json_response['error'])
                            elif 'message' in json_response: # Handle other structured responses
                                command_output = json_response # Pass the whole dict for formatting
                            else:
                                raise Exception("Invalid response format from remote API.")
                            
                            context.add_to_history(user_input, command_output)
                            context.set_current_context(command_output)
                            output_display = format_output(command_output, config)
                            console.print(Panel(output_display, title="[green]Remote Success[/green]", border_style="green", 
                                                subtitle=f"Remote Command: '{user_input}'"))
                            logging.info(f"Remote Command: {user_input} | Success | Output: {json.dumps(command_output)}")
                        except requests.exceptions.RequestException as e:
                            error_msg = f"Network error connecting to remote API: {e}"
                            console.print(Panel(Text(f"Error: {error_msg}", style="red"), title="[red]Remote API Error[/red]"))
                            logging.error(f"Remote Command: {user_input} | Error: {error_msg}")
                        except Exception as e:
                            error_msg = str(e) or "Unknown error from remote API."
                            console.print(Panel(Text(f"Error: {error_msg}", style="red"), title="[red]Remote API Error[/red]"))
                            logging.error(f"Remote Command: {user_input} | Error: {error_msg}")
                    elif agent: # Local processing
                        try:
                            if status_indicator: status_indicator.stop() # Stop status for agent's own prints
                            command_output = agent.execute_command(user_input, is_web=False)
                            if status_indicator: status_indicator.start() # Restart status
                            
                            context.add_to_history(user_input, command_output)
                            context.set_current_context(command_output)
                            output_display = format_output(command_output, config)
                            console.print(Panel(output_display, title="[green]Success[/green]", border_style="green", 
                                                subtitle=f"Command: '{user_input}'"))
                            if config.verbose and agent.last_execution_time is not None:
                                console.print(Text(f"Verbose: Processed in {agent.last_execution_time:.2f}s", style="dim cyan"))
                            logging.info(f"Command: {user_input} | Success | Output: {json.dumps(command_output)}")
                        except Exception as e:
                            error_msg = str(e) or "Unknown error during local execution."
                            suggestion = "Try 'help' or rephrase." if "not found" not in error_msg.lower() else "Check ID/name."
                            console.print(Panel(Text(f"Error: {error_msg}\nSuggestion: {suggestion}", style="red"), title="[red]Error[/red]"))
                            logging.error(f"Command: {user_input} | Error: {error_msg}")
                    else:
                        console.print(Panel(Text("Agent not available and no remote URL specified.", style="red"), title="Configuration Error"))
            else: # Fallback for no RICH_AVAILABLE
                print(status_message.replace('[yellow]', '').replace('[/yellow]', '')) # Basic status print
                # Simplified execution without Rich status context manager
                command_output = None
                if remote_url:
                    # ... (Simplified remote execution, similar to above but without Rich status) ...
                    print("Remote execution not fully implemented for non-Rich mode here.") 
                elif agent:
                    # ... (Simplified local execution) ...
                    try:
                        command_output = agent.execute_command(user_input, is_web=False)
                        context.add_to_history(user_input, command_output)
                        context.set_current_context(command_output)
                        output_display = format_output(command_output, config)
                        # Panel fallback prints directly, so just call it
                        Panel(output_display, title="Success", subtitle=f"Command: '{user_input}'")
                        if config.verbose and agent.last_execution_time is not None:
                            print(f"Verbose: Processed in {agent.last_execution_time:.2f}s")
                        logging.info(f"Command: {user_input} | Success | Output: {json.dumps(command_output)}")
                    except Exception as e:
                        error_msg = str(e) or "Unknown error during local execution."
                        suggestion = "Try 'help' or rephrase." if "not found" not in error_msg.lower() else "Check ID/name."
                        Panel(Text(f"Error: {error_msg}\nSuggestion: {suggestion}", style="red"), title="Error")
                        logging.error(f"Command: {user_input} | Error: {error_msg}")
                else:
                    Panel(Text("Agent not available and no remote URL specified.", style="red"), title="Configuration Error")

        except KeyboardInterrupt:
            console.print(Panel(Text("Interrupted. Exiting...", style="yellow"), title="Interrupted"))
            break
        except Exception as e:
            console.print(Panel(Text(f"Fatal CLI error: {e}", style="red"), title="CLI Error"))
            logging.critical(f"Fatal CLI error: {e}", exc_info=True)
            break # Exit on fatal errors in the loop

# Web server runner (from runner.py)
app = Flask(__name__)
CORS(app)
# Global agent for Flask app - initialized when run_web is called.
# This is a simple approach; for production, consider Flask app factories and better state management.
global_web_agent: Optional[OpenStackAgent] = None

@app.route('/command', methods=['POST'])
def handle_command():
    global global_web_agent
    if not global_web_agent:
        # This should ideally not happen if run_web initializes it properly.
        logging.error("Web agent not initialized before request.")
        return jsonify({'error': 'Web agent not initialized. Server error.'}), 500

    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'error': 'Missing command in request body'}), 400
    
    user_command = data['command']
    logging.info(f"API Command Received: {user_command}")
    
    try:
        # The agent's execute_command is now designed to return a dict for web
        command_output_structured = global_web_agent.execute_command(user_command, is_web=True)
        
        if isinstance(command_output_structured, dict) and 'status' in command_output_structured:
            if command_output_structured['status'] == 'success':
                logging.info(f"API Command: {user_command} | Success | Result: {json.dumps(command_output_structured.get('result'))}")
                return jsonify({'result': command_output_structured.get('result')}), 200
            elif command_output_structured['status'] == 'missing_parameters':
                logging.warning(f"API Command: {user_command} | Missing Parameters | Details: {json.dumps(command_output_structured)}")
                return jsonify(command_output_structured), 400 # Bad Request
            elif command_output_structured['status'] == 'clarification_needed':
                logging.info(f"API Command: {user_command} | Clarification Needed | Message: {command_output_structured.get('message')}")
                return jsonify(command_output_structured), 400 # Bad Request
            else: # Includes 'error' status or other unknown statuses
                error_msg = command_output_structured.get('message', 'An unknown error occurred in the agent.')
                logging.error(f"API Command: {user_command} | Agent Error | Message: {error_msg}")
                return jsonify({'error': error_msg}), 500 # Internal Server Error
        else:
            # This case should ideally be handled by the agent returning a structured error
            error_msg = "Unexpected response format from agent during web command execution."
            logging.error(f"API Command: {user_command} | Unexpected Agent Response: {command_output_structured}")
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        error_msg = str(e) or "Unknown error processing command in web handler."
        logging.critical(f"API Command: {user_command} | Unhandled Exception in /command: {error_msg}", exc_info=True)
        return jsonify({'error': error_msg}), 500

def run_web():
    global global_web_agent
    console.print(Panel(Text("Initializing OpenStack Agent for Web Server...", style="bold blue"), title="Web Server Mode"))
    global_web_agent = OpenStackAgent()
    if not global_web_agent.openstack_api.connect():
        console.print(Panel(Text("CRITICAL: Failed to connect to OpenStack for web server. API will likely fail.", style="bold red"), title="Connection Error"))
    else:
        console.print(Text("OpenStack Agent initialized and connected for Web Server.", style="green"))

    console.print(Panel(Text("Starting Flask web server for OpenStack AI Agent...", style="bold blue"), title="Web Server Mode", border_style="blue"))
    console.print(Text("API Endpoint available at ", style="green"), Text("/command", style="bold green"), Text(" (POST)", style="green"))
    console.print(Text("Example usage with curl:", style="yellow"))
    console.print(Text("curl -X POST -H \"Content-Type: application/json\" -d '{\"command\": \"list all servers\"}' http://localhost:5001/command", style="italic yellow"))
    
    # Disable Flask's default logging to avoid duplicate messages if our logging is sufficient
    # Or configure Flask logging to integrate with our main logger
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING) # Or ERROR, to reduce verbosity from HTTP requests

    app.run(host='0.0.0.0', port=5001, debug=False) # debug=False for production/demonstration

# Main function (from runner.py)
def main():
    parser = argparse.ArgumentParser(description="Consolidated OpenStack AI Chatbot Assistant")
    parser.add_argument("mode", choices=["cli", "web"], default="cli", nargs="?", 
                        help="Run in CLI or web mode. Default: cli.")
    parser.add_argument("--remote-url", type=str, default=None, 
                        help="URL of a remote OpenStack AI Agent API for the CLI to connect to (e.g., http://your-server:5001). This makes the CLI a client.")
    # Add argument for GOOGLE_API_KEY if not set in environment
    parser.add_argument("--google-api-key", type=str, default=os.environ.get("GOOGLE_API_KEY"),
                        help="Google API Key for Gemini. Overrides GOOGLE_API_KEY environment variable if provided.")

    args = parser.parse_args()

    # Update GOOGLE_API_KEY if provided via CLI argument
    global GOOGLE_API_KEY
    if args.google_api_key:
        GOOGLE_API_KEY = args.google_api_key
        # Re-configure genai if the key was updated and is valid
        if GOOGLE_API_KEY:
            try:
                genai.configure(api_key=GOOGLE_API_KEY)
                print(f"Google AI configured with API key from CLI argument.")
            except Exception as e:
                print(f"Error re-configuring Google AI with provided key: {e}")
        else:
            print("No Google API Key provided via CLI or environment. AI features will be limited.")
    elif not GOOGLE_API_KEY:
        # Prompt for Google API Key if not found in env or args
        print("Google API Key not found in environment variables or CLI arguments.")
        key_input = Prompt.ask("Please enter your Google API Key (or press Enter to skip AI features):").strip()
        if key_input:
            GOOGLE_API_KEY = key_input
            try:
                genai.configure(api_key=GOOGLE_API_KEY)
                print("Google AI configured with API key provided at runtime.")
            except Exception as e:
                print(f"Error configuring Google AI with provided key: {e}")
        else:
            print("AI features will be limited as no Google API Key was provided.")

    if args.remote_url:
        print(f"CLI Mode: Connecting to remote agent at {args.remote_url}")
        run_cli(remote_url=args.remote_url)
    elif args.mode == "cli":
        print("CLI Mode: Running local agent.")
        run_cli()
    elif args.mode == "web":
        print("Web Server Mode: Starting local agent API.")
        run_web()
    else:
        # This case should not be reached due to argparse choices
        print("Invalid mode or arguments. Use --help for options.")
        sys.exit(1)

if __name__ == "__main__":
    main()