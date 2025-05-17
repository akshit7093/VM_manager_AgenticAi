
import React, { useState } from "react";
import { CommandInput } from "./CommandInput";
import { OutputDisplay } from "./OutputDisplay";
import { CommandHistory } from "./CommandHistory";
import { StatusIndicator } from "./StatusIndicator";
import { sendCommand, CommandResponse } from "@/services/api";
import { useCommandHistory } from "@/hooks/use-command-history";
import { cn } from "@/lib/utils";

export const Terminal: React.FC = () => {
  const [response, setResponse] = useState<CommandResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(true);
  const { history, addCommand, updateCommand, clearHistory } = useCommandHistory();

  const handleSubmit = async (command: string) => {
    setIsLoading(true);
    setLastCommand(command);
    setResponse(null);
    
    // Add to history
    const commandId = addCommand(command);
    
    try {
      const result = await sendCommand(command);
      setResponse(result);
      
      // Update history
      updateCommand(commandId, { 
        status: result.status === "error" ? "error" : "success",
        response: result
      });
    } finally {
      setIsLoading(false);
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
          
          {/* Input area */}
          <div className="px-4 py-3 border-t border-terminal-muted/30">
            <CommandInput 
              onSubmit={handleSubmit} 
              isLoading={isLoading}
              lastCommand={lastCommand} 
            />
          </div>
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
