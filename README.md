# OpenStack Management Interface

This project provides a simple interface for managing OpenStack resources, primarily focusing on creating Virtual Machines (VMs).

## Project Structure

- `app.py`: A Flask web application that exposes an API endpoint (`/create_vm`) to handle VM creation requests.
- `openstack_manager.py`: Contains the core logic for interacting with the OpenStack API using the `openstacksdk`. It includes functions for connecting to OpenStack, listing resources (servers, images), and creating VMs (including handling boot-from-volume).
- `test_openstack_api.py`: A command-line script for testing the OpenStack connection and the VM creation functionality provided by `openstack_manager.py`.
- `requirements.txt`: Lists the necessary Python dependencies.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate

    pip install -r requirements.txt
    ```

3.  **Configure OpenStack Credentials:**
    The scripts (`openstack_manager.py` and `test_openstack_api.py`) primarily rely on environment variables for OpenStack credentials. Set the following variables in your environment:
    - `OS_AUTH_URL`: Your OpenStack Keystone authentication URL (e.g., `https://your-openstack-api:5000/v3`).
    - `OS_USERNAME`: Your OpenStack username.
    - `OS_PASSWORD`: Your OpenStack password.
    - `OS_PROJECT_NAME`: The name of your OpenStack project.
    - `OS_PROJECT_ID`: The ID of your OpenStack project.
    - `OS_USER_DOMAIN_NAME`: Your user domain name (often `Default`).
    - `OS_PROJECT_DOMAIN_NAME`: Your project domain name (often `Default`).

    Alternatively, you can modify the default values directly within the Python scripts, but using environment variables is more secure and flexible.

## Usage

### 1. Running the Web API (`app.py`)

   Start the Flask development server:
   ```bash
   python app.py
   ```
   The server will typically run on `http://localhost:5001` (or the port specified by the `PORT` environment variable).

   You can then send POST requests to the `/create_vm` endpoint with a JSON body specifying the VM details:

   **Example using `curl`:**
   ```bash
   curl -X POST -H "Content-Type: application/json" -d \
   '{
     "name": "my-api-vm",
     "image_name": "Ubuntu-24.04",
     "flavor_name": "S.4",
     "network_name": "test-net",
     "volume_size": 10
   }' \
   http://localhost:5001/create_vm
   ```

   - `name`, `image_name`, `flavor_name` are required.
   - `network_name` defaults to 'default' if omitted.
   - `volume_size` (in GB) is optional. If provided, the VM will boot from a newly created volume of that size based on the specified image. If omitted, it boots directly from the image.

### 2. Running the Test Script (`test_openstack_api.py`)

   This script connects to OpenStack, lists existing servers and images, and attempts to create a test VM using the parameters defined within the script.

   Ensure your OpenStack credentials are set (see Setup section).

   Run the script:
   ```bash
   python test_openstack_api.py
   ```
   Review the script's output for connection status, resource lists, and the result of the VM creation attempt.
   **Important:** Modify the `vm_name_to_create`, `image_name_to_use`, `flavor_name_to_use`, `network_name_to_use`, and `volume_size_gb` variables within `test_openstack_api.py` to match your OpenStack environment before running the creation part.