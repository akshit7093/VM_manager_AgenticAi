
import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandInputProps {
  onSubmit: (command: string) => void;
  isLoading: boolean;
  lastCommand?: string | null;
}

export const CommandInput: React.FC<CommandInputProps> = ({
  onSubmit,
  isLoading,
  lastCommand,
}) => {
  const [command, setCommand] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      onSubmit(command);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (command.trim() && !isLoading) {
        onSubmit(command);
      }
    }
  };

  const clearInput = () => {
    setCommand("");
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  useEffect(() => {
    // Auto resize the textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [command]);

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex items-start">
        <div className="relative flex-grow">
          <span className="absolute left-3 top-3 text-terminal-command select-none">$</span>
          <Textarea
            ref={textareaRef}
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your OpenStack command (e.g., list all servers, create a new vm...)"
            className={cn(
              "min-h-[60px] pl-7 pr-10 py-2 bg-terminal/70 text-terminal-foreground border-terminal-muted resize-none",
              "focus:ring-1 focus:ring-terminal-command/50 focus:border-terminal-command",
              isLoading && "opacity-70"
            )}
            disabled={isLoading}
            rows={1}
          />
          {command && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={clearInput}
              className="absolute right-2 top-2 h-6 w-6 text-terminal-muted hover:text-terminal-foreground"
              aria-label="Clear input"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
        <Button
          type="submit"
          className={cn(
            "ml-2 bg-terminal-command hover:bg-terminal-command/80 text-white",
            isLoading && "opacity-70"
          )}
          disabled={!command.trim() || isLoading}
          aria-label="Send command"
        >
          <Send className="h-4 w-4 mr-2" />
          Send
        </Button>
      </div>
    </form>
  );
};
