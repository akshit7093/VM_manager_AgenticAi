
import React, { useState, useEffect } from "react";
import { CommandInput } from "./CommandInput";
import { OutputDisplay } from "./OutputDisplay";
import { CommandHistory } from "./CommandHistory";
import { StatusIndicator } from "./StatusIndicator";
import { sendCommand, CommandResponse } from "@/services/api";
import { useCommandHistory } from "@/hooks/use-command-history";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button"; // For potential confirmation buttons
import { Input } from "@/components/ui/input"; // For parameter input
import { Label } from "@/components/ui/label"; // For parameter input labels

interface MissingParamInfo {
  originalCommand: string;
  paramsNeeded: string[] | Record<string, any>;
  message?: string;
}

interface ConfirmationInfo {
  originalCommand: string;
  actionDetails?: string;
  confirmationId?: string;
  message?: string;
}

export const Terminal: React.FC = () => {
  const [response, setResponse] = useState<CommandResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(true);
  const { history, addCommand, updateCommand, clearHistory } = useCommandHistory();

  const [missingParamInfo, setMissingParamInfo] = useState<MissingParamInfo | null>(null);
  const [collectedParams, setCollectedParams] = useState<Record<string, any>>({});
  const [currentParamIndex, setCurrentParamIndex] = useState(0);

  // State for handling confirmation requests
  const [confirmationInfo, setConfirmationInfo] = useState<ConfirmationInfo | null>(null);

  const resetInteractionStates = () => {
    setMissingParamInfo(null);
    setCollectedParams({});
    setCurrentParamIndex(0);
    setConfirmationInfo(null);
  };

  const handleSubmit = async (command: string, additionalParams?: Record<string, any>) => {
    setIsLoading(true);
    if (!additionalParams) { // Only set last command for initial submissions
      setLastCommand(command);
      setResponse(null); // Clear previous response for new primary command
      resetInteractionStates(); // Reset any ongoing interactions
    }
    
    const commandId = addCommand(command);
    let currentIsLoading = true; // Local tracker for isLoading state
    
    try {
      const result = await sendCommand(command, additionalParams);
      
      // If transitioning to a state that requires user input, stop the generic loading spinner.
      if (result.status === "missing_parameters" || result.status === "confirmation_required") {
        setIsLoading(false);
        currentIsLoading = false; // Mark that isLoading was handled for these cases
      }

      setResponse(result); // Set response for OutputDisplay and prompts

      // Update command history (original logic for status)
      updateCommand(commandId, { 
        status: result.status === "error" ? "error" : "success", 
        response: result
      });

      // Handle specific UI states based on result
      if (result.status === "missing_parameters" && result.missing_params) {
        setMissingParamInfo({
          originalCommand: command,
          paramsNeeded: result.missing_params,
          message: result.message
        });
        setCurrentParamIndex(0);
        setCollectedParams({});
      } else if (result.status === "confirmation_required" && result.action_details && result.confirmation_id) {
        setConfirmationInfo({
          originalCommand: command,
          actionDetails: result.action_details,
          confirmationId: result.confirmation_id,
          message: result.message
        });
      } else { 
        // For 'success', 'error', 'info', or other direct outcomes
        resetInteractionStates(); // Clear any pending interaction states
      }

    } finally {
      // If isLoading was not set to false by the specific conditions above, set it now.
      // This covers paths like direct success, direct error from sendCommand, or info.
      if (currentIsLoading) {
        setIsLoading(false);
      }
    }
  };

  const handleMissingParamInputChange = (paramName: string, value: string) => {
    setCollectedParams(prev => ({ ...prev, [paramName]: value }));
  };

  const handleNextMissingParam = () => {
    if (!missingParamInfo) return;

    const paramsArray = Array.isArray(missingParamInfo.paramsNeeded) 
      ? missingParamInfo.paramsNeeded 
      : Object.keys(missingParamInfo.paramsNeeded);

    if (currentParamIndex < paramsArray.length - 1) {
      setCurrentParamIndex(prev => prev + 1);
    } else {
      // All params collected, resubmit the command
      handleSubmit(missingParamInfo.originalCommand, collectedParams);
    }
  };

  const handleCancelMissingParams = () => {
    resetInteractionStates();
    setResponse({
      status: "info",
      raw_output: "Command canceled by user due to missing parameters."
    });
  };

  const handleConfirmAction = (confirmed: boolean) => {
    if (!confirmationInfo) return;

    if (confirmed) {
      // Resubmit the command with confirmation
      handleSubmit(confirmationInfo.originalCommand, { 
        confirmation_id: confirmationInfo.confirmationId, 
        confirmed: true 
      });
    } else {
      // User canceled the action
      setResponse({
        status: "info",
        raw_output: `Action "${confirmationInfo.actionDetails || 'unspecified'}" canceled by user.`,
        message: `Action "${confirmationInfo.actionDetails || 'unspecified'}" canceled by user.`
      });
      resetInteractionStates();
    }
  };

  const handleSelectFromHistory = (command: string) => {
    setLastCommand(command);
    // Just fill the input, don't auto-execute
  };

  const handleClearOutput = () => {
    setResponse(null);
    setLastCommand(null);
  };

  const toggleHistory = () => {
    setShowHistory(prev => !prev);
  };

  // UI for missing parameters prompt
  const renderMissingParameterPrompt = () => {
    if (!missingParamInfo || isLoading || confirmationInfo) return null; // Do not show if confirmation is pending

    const paramsArray = Array.isArray(missingParamInfo.paramsNeeded) 
      ? missingParamInfo.paramsNeeded 
      : Object.keys(missingParamInfo.paramsNeeded);
    
    if (currentParamIndex >= paramsArray.length) return null; // Should not happen if logic is correct

    const currentParamName = paramsArray[currentParamIndex];
    // For Record<string, any>, we might have more details like type or description
    const paramDetails = !Array.isArray(missingParamInfo.paramsNeeded) 
      ? missingParamInfo.paramsNeeded[currentParamName]
      : null;
    const promptLabel = typeof paramDetails === 'string' ? paramDetails : `Enter value for ${currentParamName}:`;

    return (
      <div className="p-4 border-t border-terminal-muted/30 bg-terminal-input-bg">
        <Label htmlFor={`param-input-${currentParamName}`} className="block mb-2 text-sm font-medium text-terminal-foreground">
          {missingParamInfo.message && currentParamIndex === 0 && (
            <p className="mb-2 text-yellow-400">{missingParamInfo.message}</p>
          )}
          {promptLabel}
        </Label>
        <Input 
          id={`param-input-${currentParamName}`}
          type="text" 
          value={collectedParams[currentParamName] || ""}
          onChange={(e) => handleMissingParamInputChange(currentParamName, e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleNextMissingParam()}
          className="w-full p-2 border rounded bg-terminal-input text-terminal-foreground border-terminal-muted focus:ring-blue-500 focus:border-blue-500"
          autoFocus
        />
        <div className="mt-2 flex justify-end space-x-2">
          <Button onClick={handleCancelMissingParams} variant="outline" size="sm">Cancel</Button>
          <Button onClick={handleNextMissingParam} size="sm">
            {currentParamIndex < paramsArray.length - 1 ? "Next Parameter" : "Submit Parameters"}
          </Button>
        </div>
      </div>
    );
  };

  // UI for confirmation prompt
  const renderConfirmationPrompt = () => {
    if (!confirmationInfo || isLoading || missingParamInfo) return null; // Do not show if missing params are pending

    return (
      <div className="p-4 border-t border-terminal-muted/30 bg-terminal-input-bg">
        <Label className="block mb-2 text-lg font-medium text-terminal-foreground">
          {confirmationInfo.message || "Please confirm the following action:"}
        </Label>
        {confirmationInfo.actionDetails && (
          <p className="mb-3 p-2 bg-terminal-muted/20 rounded text-terminal-foreground/90">
            {confirmationInfo.actionDetails}
          </p>
        )}
        <div className="mt-2 flex justify-end space-x-2">
          <Button onClick={() => handleConfirmAction(false)} variant="outline" size="sm">Cancel</Button>
          <Button onClick={() => handleConfirmAction(true)} size="sm" variant="destructive">Confirm</Button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-screen-xl mx-auto rounded-md overflow-hidden border border-terminal-muted bg-terminal">
      <StatusIndicator />
      
      <div className="flex flex-grow overflow-hidden">
        {/* Main terminal area */}
        <div className={cn(
          "flex flex-col flex-grow min-w-0",
          showHistory ? "border-r border-terminal-muted/30" : ""
        )}>
          {/* Output area */}
          <div className="flex-grow overflow-hidden">
            <OutputDisplay 
              response={response} 
              isLoading={isLoading} 
              lastCommand={lastCommand || undefined}
              onClear={handleClearOutput}
            />
          </div>
          
          {/* Parameter Input / Confirmation / Command Input area */}
          {missingParamInfo && !isLoading && !confirmationInfo ? (
            renderMissingParameterPrompt()
          ) : confirmationInfo && !isLoading && !missingParamInfo ? (
            renderConfirmationPrompt()
          ) : (
            <div className="px-4 py-3 border-t border-terminal-muted/30">
              <CommandInput 
                onSubmit={handleSubmit} 
                isLoading={isLoading}
                lastCommand={lastCommand} 
              />
            </div>
          )}
        </div>
        
        {/* History sidebar */}
        {showHistory && (
          <div className="w-80 flex-shrink-0 bg-terminal">
            <CommandHistory 
              history={history} 
              onSelect={handleSelectFromHistory}
              onClear={clearHistory}
            />
          </div>
        )}
      </div>
      
      {/* Toggle history button */}
      <button 
        onClick={toggleHistory}
        className="absolute top-16 right-0 bg-terminal-muted hover:bg-terminal-muted/80 text-terminal-foreground/80 px-2 py-1 text-xs rounded-l-md"
        aria-label={showHistory ? "Hide history" : "Show history"}
      >
        {showHistory ? "Hide History" : "Show History"}
      </button>
    </div>
  );
};
