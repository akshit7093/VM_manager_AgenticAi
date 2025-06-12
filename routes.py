#!/usr/bin/env python3
"""Backend routing for OpenStack Agent API.

This file sets up a FastAPI application to provide API endpoints
that allow a frontend to interact with the OpenStackAgent.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sys
import os
import uuid
from typing import Optional, Dict, Any

# Add the parent directory to sys.path to allow imports from agent.py and api.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from agent import OpenStackAgent
except ImportError as e:
    print(f"Error importing OpenStackAgent: {e}")
    print("Please ensure agent.py is in the correct path and all dependencies are installed.")
    OpenStackAgent = None

app = FastAPI(title="OpenStack AI Command Center")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the OpenStack Agent
if OpenStackAgent:
    openstack_agent = OpenStackAgent()
    if hasattr(openstack_agent, 'openstack_api') and hasattr(openstack_agent.openstack_api, 'connect'):
        if not openstack_agent.openstack_api.connect():
            print("Failed to connect to OpenStack via agent on startup.")
            openstack_agent = None
else:
    openstack_agent = None
    print("OpenStackAgent could not be initialized. API endpoints will not function correctly.")

# In-memory store for pending confirmations
pending_confirmations = {}

# Pydantic models for request validation
class CommandRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = {}

@app.post("/api/command")
async def handle_command(command: CommandRequest):
    """Handles natural language commands to interact with OpenStack."""
    if not openstack_agent:
        raise HTTPException(
            status_code=503,
            detail="OpenStack Agent is not initialized or failed to connect to OpenStack. Please check the connection and try again."
        )

    user_query = command.query
    params = command.params
    print(f"Received query: {user_query}, params: {params}")

    try:
        # Check if this is a confirmation response
        if params.get('confirmation_id') and params.get('confirmed') is True:
            # Retrieve the pending command
            confirmation_id = params.get('confirmation_id')
            if confirmation_id not in pending_confirmations:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired confirmation ID."
                )

            # Get the command/action to execute
            action_to_execute = pending_confirmations[confirmation_id]
            command_output = openstack_agent.process_user_query(action_to_execute)
            pending_confirmations.pop(confirmation_id)
        else:
            # Execute the initial command
            command_output = openstack_agent.process_user_query(user_query)

        # Handle different response types from the agent
        if isinstance(command_output, dict):
            if command_output.get('status') == 'confirmation_required':
                confirmation_id = str(uuid.uuid4())
                executable_action = command_output.get('action_details', user_query)
                pending_confirmations[confirmation_id] = executable_action
                return {
                    'status': 'confirmation_required',
                    'confirmation_id': confirmation_id,
                    'message': command_output.get('message', 'Confirmation required')
                }

        return {'result': command_output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get the current status of the OpenStack agent and connection."""
    api_connected = False
    if openstack_agent and hasattr(openstack_agent, 'openstack_api'):
        if hasattr(openstack_agent.openstack_api, 'is_connected'):
            api_connected = openstack_agent.openstack_api.is_connected()
        else:
            # For FakeOpenStackAPI, check if connect() was successful
            api_connected = openstack_agent.openstack_api.connect()

    return {
        "status": "ok" if openstack_agent else "error",
        "agent_initialized": openstack_agent is not None,
        "openstack_connected": api_connected
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)