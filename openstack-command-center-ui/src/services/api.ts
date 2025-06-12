import { toast } from "@/components/ui/use-toast";

const API_BASE_URL = "http://localhost:5001";

export interface CommandResponse {
  status: string; // 'success', 'error', 'missing_parameters', 'confirmation_required', 'info'
  output?: string[];
  raw_output?: string;
  understood_command?: string;
  error?: string;
  missing_params?: string[] | Record<string, any>;
  message?: string;
  action_details?: string;
  confirmation_id?: string;
}

export interface StatusResponse {
  status: string;
  message: string;
  openstack_connection: string;
  error?: string;
}

export const sendCommand = async (
  query: string,
  additionalParams?: Record<string, any>
): Promise<CommandResponse> => {
  try {
    const payload: { query: string; params?: Record<string, any> } = { query };
    if (additionalParams) {
      payload.params = additionalParams;
    }

    const response = await fetch(`${API_BASE_URL}/api/command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok && !data.status) {
      throw new Error(data.error || data.message || `Request failed with status ${response.status}`);
    }

    // Handle both 2xx and non-2xx responses with valid status
    let finalResponse: CommandResponse;

    if (data.status === "confirmation_required" || data.status === "missing_parameters") {
      // Direct response with status (e.g., confirmation_required, missing_parameters)
      finalResponse = data as CommandResponse;
    } else if (response.ok && data.result) {
      // Successful response with result
      const backendResult = data.result;

      if (typeof backendResult === 'object' && backendResult !== null && backendResult.status) {
        finalResponse = { ...backendResult } as CommandResponse;
        if (backendResult.output && Array.isArray(backendResult.output)) {
          finalResponse.output = backendResult.output.map(String);
        } else if (backendResult.raw_output && typeof backendResult.raw_output !== 'string') {
          finalResponse.raw_output = String(backendResult.raw_output);
        }
      } else {
        finalResponse = { status: "success" };
        if (typeof backendResult === 'object' && backendResult !== null) {
          if (backendResult.understood_command) {
            finalResponse.understood_command = String(backendResult.understood_command);
          }
          if (Array.isArray(backendResult.output)) {
            finalResponse.output = backendResult.output.map(String);
          } else if (backendResult.raw_output !== undefined) {
            finalResponse.raw_output = String(backendResult.raw_output);
          } else {
            const otherData = { ...backendResult };
            delete otherData.understood_command;
            if (Object.keys(otherData).length > 0) {
              finalResponse.raw_output = JSON.stringify(otherData, null, 2);
            }
          }
        } else if (typeof backendResult === 'string') {
          finalResponse.raw_output = backendResult;
        } else if (Array.isArray(backendResult)) {
          finalResponse.output = backendResult.map(String);
        } else if (backendResult === null || backendResult === undefined) {
          finalResponse.raw_output = "Command executed successfully. No output.";
        } else {
          finalResponse.raw_output = String(backendResult);
        }
      }
    } else {
      throw new Error("Unexpected response format from backend.");
    }

    // Ensure default output for edge cases
    if (finalResponse.status === "success" && !finalResponse.output && !finalResponse.raw_output && !finalResponse.error) {
      if (finalResponse.understood_command && Object.keys(finalResponse).length === 2) {
        finalResponse.raw_output = "Command processed.";
      } else if (Object.keys(finalResponse).length === 1 && finalResponse.status === "success") {
        finalResponse.raw_output = "Command executed successfully. No specific output provided.";
      }
    }

    return finalResponse;

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Network error. Please check your connection and try again.";
    console.error("Command error:", errorMessage, error);

    toast({
      title: "Command Error",
      description: errorMessage,
      variant: "destructive",
    });

    return {
      status: "error",
      error: errorMessage,
      message: errorMessage,
    };
  }
};

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