
import { useEffect, useState } from "react";
import { getStatus, StatusResponse } from "@/services/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { RefreshCw, Check, X, Loader, AlertTriangle } from "lucide-react";

export const StatusIndicator = () => {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const response = await getStatus();
      setStatus(response);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();

    // Poll status every 30 seconds
    const intervalId = setInterval(fetchStatus, 30000);
    return () => clearInterval(intervalId);
  }, []);

  const getConnectionIcon = () => {
    if (loading) return <Loader className="h-4 w-4 animate-spin" />;
    if (!status) return <X className="h-4 w-4 text-terminal-error" />;
    // If API status is unavailable, OpenStack connection status is also effectively unavailable/unknown
    if (status.status === "unavailable") {
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />; // Using yellow-500 for warning
    }
    if (status.openstack_connection === "Connected") {
      return <Check className="h-4 w-4 text-terminal-success" />;
    }
    // For "Disconnected", "Error", or other "Unknown" states from backend
    return <X className="h-4 w-4 text-terminal-error" />;
  };

  const getApiIcon = () => {
    if (loading) return <Loader className="h-4 w-4 animate-spin" />;
    if (!status || status.status === "error") {
      return <X className="h-4 w-4 text-terminal-error" />;
    }
    if (status.status === "unavailable") {
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />; // Using yellow-500 for warning
    }
    // status.status === "ok"
    return <Check className="h-4 w-4 text-terminal-success" />;
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-terminal-header to-terminal-header-gradient text-white rounded-t-md">
      <div className="flex items-center space-x-6 text-sm">
        <div className="flex items-center gap-2">
          <span>API:</span>
          <span className={cn(
            "flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium",
            loading || !status ? "bg-gray-500/20 text-gray-400" : // Neutral for loading/initial error
            status.status === "ok" ? "bg-terminal-success/20 text-terminal-success" :
            status.status === "unavailable" ? "bg-yellow-500/20 text-yellow-500" : // Warning style
            "bg-terminal-error/20 text-terminal-error" // Error style for status.status === "error"
          )}>
            {getApiIcon()}
            {loading ? "Checking..." : !status ? "Error" : status.status === "ok" ? "Running" : status.status === "unavailable" ? "N/A" : status.message || "Error"}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <span>OpenStack:</span>
          <span className={cn(
            "flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium",
            loading || !status ? "bg-gray-500/20 text-gray-400" : // Neutral for loading/initial error
            status.status === "unavailable" ? "bg-yellow-500/20 text-yellow-500" : // Warning if API is unavailable
            status.openstack_connection === "Connected" ? "bg-terminal-success/20 text-terminal-success" :
            "bg-terminal-error/20 text-terminal-error" // Error for other states
          )}>
            {getConnectionIcon()}
            {loading ? "Checking..." : !status ? "Unknown" : status.status === "unavailable" ? "N/A" : status.openstack_connection || "Unknown"}
          </span>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        {lastUpdated && (
          <span className="text-xs text-terminal-foreground/70">
            Updated: {lastUpdated.toLocaleTimeString()}
          </span>
        )}
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={fetchStatus}
          disabled={loading}
          className="text-terminal-foreground h-7 w-7"
          aria-label="Refresh status"
        >
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </div>
    </div>
  );
};
