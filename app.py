from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os

# Import OpenStack connection logic
from openstack_manager import connect_to_openstack, create_server

app = FastAPI()

# Initialize OpenStack connection once
openstack_conn = connect_to_openstack()

@app.get("/")
def home():
    return {"message": "OpenStack Agent is running!"}

class VMRequest(BaseModel):
    # Define your VM creation parameters here
    name: str
    # Add other fields as needed

@app.post('/create_vm')
def handle_create_vm(request: VMRequest):
    """Handles VM creation requests based on form/JSON data."""
    try:
        # Your VM creation logic here
        result = create_server(openstack_conn, request.dict())
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)