
import { toast } from "@/components/ui/use-toast";

const API_BASE_URL = "http://localhost:5000"; // Update this to your actual API base URL

export interface CommandResponse {
  status: string;
  output?: string[];
  raw_output?: string;
  understood_command?: string; // Added for AI's interpretation
  error?: string;
}

export interface StatusResponse {
  status: string;
  message: string;
  openstack_connection: string;
  error?: string;
}

// Send a command to the OpenStack agent
export const sendCommand = async (query: string): Promise<CommandResponse> => {
  try {
    // Removed client-side empty command check; let backend handle it.

    const response = await fetch(`${API_BASE_URL}/api/command`, { // Endpoint changed to /api/command
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: query }), // Payload key changed to query
    });

    const data = await response.json(); // data will be { result: ... } or { error: ... }

    if (!response.ok) { // Handles non-2xx responses, data should be { error: ... }
      throw new Error(data.error || "An unexpected error occurred while processing the command.");
    }

    // If response is ok, data is { result: ActualBackendOutput }
    const backendResult = data.result;

    // Map backendResult to CommandResponse structure
    let finalResponse: CommandResponse = { status: "success" };

    if (typeof backendResult === 'object' && backendResult !== null && !Array.isArray(backendResult)) {
      // This is the case where backendResult is an object, potentially containing output, raw_output, and understood_command.
      if (backendResult.understood_command && typeof backendResult.understood_command === 'string') {
        finalResponse.understood_command = backendResult.understood_command;
      }

      if (Array.isArray(backendResult.output)) {
        finalResponse.output = backendResult.output.map(item =>
          typeof item === 'string' ? item : JSON.stringify(item, null, 2)
        );
      } else if (typeof backendResult.raw_output === 'string') {
        finalResponse.raw_output = backendResult.raw_output;
      } else {
        // If neither .output nor .raw_output is directly present,
        // stringify the remaining parts of backendResult (if any) as raw_output,
        // excluding already processed fields.
        const otherData = { ...backendResult };
        delete otherData.understood_command;
        delete otherData.output;
        delete otherData.raw_output;

        if (Object.keys(otherData).length > 0) {
          finalResponse.raw_output = JSON.stringify(otherData, null, 2);
        }
      }
    } else if (typeof backendResult === 'string') {
      finalResponse.raw_output = backendResult;
    } else if (Array.isArray(backendResult)) {
      finalResponse.output = backendResult.map(item =>
        typeof item === 'string' ? item : JSON.stringify(item, null, 2)
      );
    } else if (backendResult === null || backendResult === undefined) {
      // Explicitly no output from backend
      finalResponse.raw_output = "Command executed successfully. No output.";
    } else {
      // For other primitive types like boolean or number
      finalResponse.raw_output = String(backendResult);
    }

    // Ensure a default message if no output fields were populated but the command was successful
    if (finalResponse.status === "success" && !finalResponse.output && !finalResponse.raw_output && !finalResponse.error) {
      if (finalResponse.understood_command) {
        finalResponse.raw_output = "Command processed."; // If understood_command is present, this is a minimal confirmation.
      } else {
        finalResponse.raw_output = "Command executed successfully. No specific output provided.";
      }
    }
    
    return finalResponse;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Network error. Please check your connection and try again.";
    console.error("Command error:", errorMessage);
    
    toast({
      title: "Command Error",
      description: errorMessage,
      variant: "destructive",
    });
    
    return {
      status: "error",
      error: errorMessage,
    };
  }
};

// Get the status of the API and OpenStack connection
export const getStatus = async (): Promise<StatusResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/status`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || data.error || "Failed to fetch status.");
    }

    return {
      status: data.status,
      message: data.message,
      openstack_connection: data.openstack_connection,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Network error or backend unavailable.";
    console.error("Get status error:", errorMessage);
    toast({
      title: "Status Error",
      description: errorMessage,
      variant: "destructive",
    });
    return {
      status: "error",
      message: "Failed to retrieve status from the backend.",
      openstack_connection: "Unknown",
      error: errorMessage,
    };
  }
};
