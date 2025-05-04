from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from .openstack_api import openstack_api
from .schemas import (
    ServerCreateRequest,
    ResizeRequest,
    VolumeCreateRequest,
    NetworkCreateRequest
)

router = APIRouter()

# Server Operations
@router.get("/servers", response_model=List[Dict[str, Any]])
async def list_all_servers():
    """List all virtual machine instances"""
    return openstack_api.list_servers()

@router.post("/servers", status_code=status.HTTP_201_CREATED)
async def create_new_server(server_data: ServerCreateRequest):
    """Launch a new virtual machine instance"""
    result = openstack_api.create_server(
        name=server_data.name,
        image_name=server_data.image_name,
        flavor_name=server_data.flavor_name,
        network_name=server_data.network_name,
        volume_size=server_data.volume_size
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server creation failed"
        )
    return result

@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_server(server_id: str):
    """Terminate a virtual machine instance"""
    if not openstack_api.delete_server(server_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found or deletion failed"
        )

@router.post("/servers/{server_id}/resize")
async def resize_existing_server(server_id: str, resize_data: ResizeRequest):
    """Resize an existing virtual machine instance"""
    if not openstack_api.resize_server(server_id, resize_data.flavor_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server resize failed"
        )
    return {"status": "resize initiated"}

# Image Operations
@router.get("/images", response_model=List[Dict[str, Any]])
async def list_all_images():
    """List all available OS images"""
    return openstack_api.list_images()

# Flavor Operations
@router.get("/flavors", response_model=List[Dict[str, Any]])
async def list_all_flavors():
    """List all available hardware flavors"""
    return openstack_api.list_flavors()

# Network Operations
@router.get("/networks", response_model=List[Dict[str, Any]])
async def list_all_networks():
    """List all available networks"""
    return openstack_api.list_networks()

@router.post("/networks", status_code=status.HTTP_201_CREATED)
async def create_new_network(network_data: NetworkCreateRequest):
    """Create a new network with subnet"""
    result = openstack_api.create_network_with_subnet(
        network_name=network_data.network_name,
        subnet_cidr=network_data.subnet_cidr,
        subnet_name=network_data.subnet_name
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Network creation failed"
        )
    return {"network": result[0], "subnet": result[1]}

# Volume Operations
@router.get("/volumes", response_model=List[Dict[str, Any]])
async def list_all_volumes():
    """List all block storage volumes"""
    return openstack_api.list_volumes()

@router.post("/volumes", status_code=status.HTTP_201_CREATED)
async def create_new_volume(volume_data: VolumeCreateRequest):
    """Create a new block storage volume"""
    result = openstack_api.create_volume(
        name=volume_data.name,
        size_gb=volume_data.size_gb
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Volume creation failed"
        )
    return result

@router.delete("/volumes/{volume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_volume(volume_id: str):
    """Delete a block storage volume"""
    if not openstack_api.delete_volume(volume_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume not found or deletion failed"
        )

# Usage Statistics
@router.get("/usage")
async def get_resource_usage(server_id: Optional[str] = Query(None)):
    """Get resource utilization statistics"""
    usage = openstack_api.get_usage(server_id)
    if 'error' in usage:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=usage['error']
        )
    return usage