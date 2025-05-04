import sys
from dotenv import load_dotenv
from core.openstack_api import OpenStackAPI
load_dotenv()
from typing import Optional, Tuple, Dict, Any, List

def main():
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
                server_id = input("Enter server ID to delete: ").strip()
                if api.delete_server(server_id):
                    print("Server deletion successful.")
                else:
                    print("Server deletion failed.")
            
            elif choice == '8':
                server_id = input("Enter server ID to resize: ").strip()
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
                volume_id = input("Enter volume ID to delete: ").strip()
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


if __name__ == "__main__":
    main()