
import React, { useRef, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { CommandResponse } from "@/services/api";

interface OutputDisplayProps {
  response: CommandResponse | null;
  isLoading: boolean;
  lastCommand?: string;
  onClear: () => void;
}

export const OutputDisplay: React.FC<OutputDisplayProps> = ({
  response,
  isLoading,
  lastCommand,
  onClear,
}) => {
  const outputRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = React.useState(false);
  const [animatedUnderstoodCommand, setAnimatedUnderstoodCommand] = useState<string>("");

  // Typing animation for understood command
  useEffect(() => {
    if (response?.understood_command) {
      setAnimatedUnderstoodCommand(""); // Reset before starting
      let i = 0;
      const text = response.understood_command;
      const intervalId = setInterval(() => {
        if (i < text.length) {
          setAnimatedUnderstoodCommand((prev) => prev + text.charAt(i));
          i++;
        } else {
          clearInterval(intervalId);
        }
      }, 50); // Adjust typing speed here
      return () => clearInterval(intervalId);
    } else {
      setAnimatedUnderstoodCommand(""); // Clear if no understood command
    }
  }, [response?.understood_command]);

  // Auto-scroll to bottom when output changes
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [response, isLoading]);

  const handleCopyOutput = async () => {
    if (!response) return;
    
    let textToCopy = "";
    
    if (response.output) {
      textToCopy = response.output.join("\n");
    } else if (response.raw_output) {
      textToCopy = response.raw_output;
    }
    
    if (textToCopy) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error("Failed to copy output:", err);
      }
    }
  };

  const renderOutput = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center h-full py-12 text-terminal-muted">
          <Loader className="animate-spin h-8 w-8 mb-2" />
          <p>Processing command...</p>
          {lastCommand && <p className="text-sm mt-1">"{lastCommand}"</p>}
        </div>
      );
    }

    // If no response object at all (and not loading, due to check above)
    if (!response) { 
      return (
        <div className="flex items-center justify-center h-full text-terminal-muted text-center py-12">
          <p>Enter a command to see the output here</p>
        </div>
      );
    }

    // From here, 'response' is guaranteed to be non-null.
    // 'isLoading' is false because the first 'if' block would have returned.
    const understoodCommandDisplay = response.understood_command && animatedUnderstoodCommand ? (
      <div className="px-2 py-1 mb-2 border-b border-terminal-muted/20">
        <p className="text-xs text-terminal-muted italic">
          Interpreted as: <span className="text-terminal-foreground/90 font-mono">{animatedUnderstoodCommand}</span>
        </p>
      </div>
    ) : null;

    if (response.status === "error" || response.error) {
      return (
        <>
          {understoodCommandDisplay}
          <div className="text-terminal-error p-2">
            <p className="font-bold mb-1">Error:</p>
            <p>{response.error || "An unspecified error occurred."}</p>
          </div>
        </>
      );
    }

    if (response.raw_output) {
      return (
        <>
          {understoodCommandDisplay}
          <pre className="whitespace-pre-wrap break-words">{response.raw_output}</pre>
        </>
      );
    }

    if (response.output && response.output.length > 0) {
      return (
        <>
          {understoodCommandDisplay}
          <div>
            {response.output.map((line, index) => (
              <div key={index} className="py-0.5">{line}</div>
            ))}
          </div>
        </>
      );
    }
    
    if (response.status === "success") {
        // If there's an understood_command in the response, we prioritize showing that.
        // The understoodCommandDisplay variable handles the animation.
        if (response.understood_command) {
            // This will render the animated command.
            // If animatedUnderstoodCommand is empty initially, understoodCommandDisplay is null,
            // so nothing is rendered here until animation starts.
            return <>{understoodCommandDisplay}</>;
        } else {
            // Only show "Command executed successfully with no output."
            // if there was no understood_command to begin with and no other output.
            return <p className="text-terminal-muted">Command executed successfully with no output.</p>;
        }
    }

    // Fallback: If we have an understood_command, and no other specific content matched (e.g. not error, not success, no raw/array output), show it.
    // This covers cases where status might be something else, or missing, but an interpretation was made.
    if (understoodCommandDisplay) {
        return understoodCommandDisplay;
    }

    // Final fallback: If response exists, but it didn't match any of the above categories
    // (e.g. no error, no raw_output, no array_output, status not 'success', and no understood_command).
    // This indicates an unusual or truly empty response from the backend.
    return (
        <div className="p-2 text-terminal-muted">
            <p>Received a response, but it contains no displayable information.</p>
        </div>
    );
  };

  return (
    <div className="relative flex flex-col h-full">
      <div className="flex justify-between items-center px-4 py-2 border-b border-terminal-muted/30">
        <h3 className="text-sm font-medium text-terminal-foreground/80">Output</h3>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopyOutput}
            disabled={!response || isLoading || (response.status === "error")}
            className="text-terminal-foreground/80 h-7 hover:text-terminal-foreground hover:bg-terminal-muted/20"
            aria-label="Copy output to clipboard"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 mr-1.5" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 mr-1.5" />
                Copy
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClear}
            disabled={!response || isLoading}
            className="text-terminal-foreground/80 h-7 hover:text-terminal-foreground hover:bg-terminal-muted/20"
            aria-label="Clear output"
          >
            Clear
          </Button>
        </div>
      </div>
      
      <div 
        ref={outputRef}
        className={cn(
          "flex-grow overflow-auto p-4 text-terminal-foreground",
          "scrollbar-thin scrollbar-thumb-terminal-muted/30 scrollbar-track-transparent"
        )}
      >
        {renderOutput()}
      </div>
    </div>
  );
};
