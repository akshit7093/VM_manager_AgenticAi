
import React from "react";
import { Button } from "@/components/ui/button";
import { CommandHistoryItem } from "@/hooks/use-command-history";
import { cn } from "@/lib/utils";
import { 
  Check, 
  X, 
  Clock, 
  Send,
  Trash
} from "lucide-react";

interface CommandHistoryProps {
  history: CommandHistoryItem[];
  onSelect: (command: string) => void;
  onClear: () => void;
}

export const CommandHistory: React.FC<CommandHistoryProps> = ({
  history,
  onSelect,
  onClear,
}) => {
  if (history.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-4 py-2 border-b border-terminal-muted/30 flex justify-between items-center">
          <h3 className="text-sm font-medium text-terminal-foreground/80">Command History</h3>
        </div>
        <div className="flex items-center justify-center h-full text-terminal-muted text-center py-12">
          <p>No commands in history</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <Check className="h-3.5 w-3.5 text-terminal-success" />;
      case "error":
        return <X className="h-3.5 w-3.5 text-terminal-error" />;
      case "pending":
      default:
        return <Clock className="h-3.5 w-3.5 text-terminal-warning" />;
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-terminal-muted/30 flex justify-between items-center">
        <h3 className="text-sm font-medium text-terminal-foreground/80">Command History</h3>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={onClear}
          className="text-terminal-foreground/70 h-7 hover:text-terminal-foreground hover:bg-terminal-muted/20"
          aria-label="Clear history"
        >
          <Trash className="h-3.5 w-3.5 mr-1.5" />
          Clear
        </Button>
      </div>
      <div className="flex-grow overflow-auto">
        <ul className="divide-y divide-terminal-muted/20">
          {history.map((item) => (
            <li 
              key={item.id} 
              className="hover:bg-terminal-muted/10 transition-colors"
            >
              <button
                onClick={() => onSelect(item.query)}
                className="w-full text-left p-3 flex items-start"
                aria-label={`Use command: ${item.query}`}
              >
                <div className="mr-3 pt-0.5">
                  {getStatusIcon(item.status)}
                </div>
                <div className="flex-grow min-w-0">
                  <div className="flex justify-between items-start mb-1">
                    <p className="text-sm font-medium text-terminal-foreground truncate pr-2">
                      {item.query}
                    </p>
                    <span className="text-xs text-terminal-muted flex-shrink-0">
                      {formatTime(item.timestamp)}
                    </span>
                  </div>
                  {item.status === "error" && item.response?.error && (
                    <p className="text-xs text-terminal-error truncate">
                      {item.response.error}
                    </p>
                  )}
                </div>
                <div className="ml-2 flex-shrink-0">
                  <Send className="h-3.5 w-3.5 text-terminal-foreground/50" />
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
