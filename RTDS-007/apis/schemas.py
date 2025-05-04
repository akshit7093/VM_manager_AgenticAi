from pydantic import BaseModel
from typing import Optional

class ServerCreateRequest(BaseModel):
    name: str
    image_name: str
    flavor_name: str
    network_name: str = "default"
    volume_size: Optional[int] = None

class ResizeRequest(BaseModel):
    flavor_name: str

class VolumeCreateRequest(BaseModel):
    name: str
    size_gb: int

class NetworkCreateRequest(BaseModel):
    network_name: str
    subnet_cidr: str = "192.168.100.0/24"
    subnet_name: Optional[str] = None