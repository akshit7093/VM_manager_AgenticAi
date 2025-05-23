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
  const [copied, setCopied] = useState(false);
  const [animatedUnderstoodCommand, setAnimatedUnderstoodCommand] = useState("");

  useEffect(() => {
    if (response?.understood_command) {
      setAnimatedUnderstoodCommand("");
      let i = 0;
      const text = response.understood_command;
      const intervalId = setInterval(() => {
        if (i < text.length) {
          setAnimatedUnderstoodCommand((prev) => prev + text.charAt(i));
          i++;
        } else {
          clearInterval(intervalId);
        }
      }, 30);
      return () => clearInterval(intervalId);
    } else {
      setAnimatedUnderstoodCommand("");
    }
  }, [response?.understood_command]);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [response, isLoading]);

  const handleCopyOutput = async () => {
    if (!response) return;
    let textToCopy = response.raw_output ?? response.output?.join("\n") ?? "";
    if (!textToCopy) return;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const renderUnderstood = () =>
    response?.understood_command ? (
      <div className="bg-slate-100 border-l-4 border-slate-400 p-3 mb-4 rounded shadow-sm">
        <p className="text-sm italic text-slate-700">
          Interpreted as:{" "}
          <code className="bg-slate-200 px-1 rounded font-mono text-slate-900">
            {animatedUnderstoodCommand || response.understood_command}
          </code>
        </p>
      </div>
    ) : null;

  const renderError = () => (
    <div className="bg-red-100 border border-red-300 text-red-900 p-4 rounded-md shadow-sm">
      <h4 className="font-semibold mb-1">Error</h4>
      <p>{response?.error ?? response?.message ?? "An unspecified error occurred."}</p>
    </div>
  );

  const renderInfo = () => (
    <div className="bg-cyan-100 border border-cyan-300 text-cyan-900 p-4 rounded-md shadow-sm">
      <h4 className="font-semibold mb-1">Information</h4>
      <p>{response?.message ?? response?.raw_output ?? "Information message."}</p>
    </div>
  );

  const renderMissingParams = () => {
    if (!response || response.status !== 'missing_parameters') return null;
    return (
      <div className="bg-yellow-100 border border-yellow-300 text-yellow-900 p-4 rounded-md shadow-sm">
        <h4 className="font-semibold mb-1">Missing Information</h4>
        <p>{response.message || "The command requires additional information."}</p>
        {response.missing_params && Array.isArray(response.missing_params) && response.missing_params.length > 0 && (
          <div className="mt-2">
            <p className="text-sm">Parameters needed:</p>
            <ul className="list-disc list-inside text-sm font-mono">
              {response.missing_params.map((param, index) => (
                <li key={index}>{typeof param === 'string' ? param : JSON.stringify(param)}</li>
              ))}
            </ul>
          </div>
        )}
        {response.missing_params && typeof response.missing_params === 'object' && !Array.isArray(response.missing_params) && Object.keys(response.missing_params).length > 0 && (
          <div className="mt-2">
            <p className="text-sm">Details:</p>
            <pre className="text-xs bg-yellow-200 p-2 rounded mt-1 font-mono whitespace-pre-wrap">{JSON.stringify(response.missing_params, null, 2)}</pre>
          </div>
        )}
      </div>
    );
  };

  const renderConfirmationRequired = () => {
    if (!response || response.status !== 'confirmation_required') return null;
    return (
      <div className="bg-orange-100 border border-orange-300 text-orange-900 p-4 rounded-md shadow-sm">
        <h4 className="font-semibold mb-1">Confirmation Required</h4>
        <p>{response.message || "Please confirm the following action."}</p>
        {response.action_details && (
          <div className="mt-2">
            <p className="text-sm font-medium">Action Details:</p>
            <p className="text-sm bg-orange-200 p-2 rounded mt-1 font-mono">{response.action_details}</p>
          </div>
        )}
      </div>
    );
  };

  const renderRaw = () => (
    <pre className="bg-zinc-100 text-zinc-800 p-4 rounded font-mono overflow-x-auto whitespace-pre-wrap shadow-sm">
      {response!.raw_output}
    </pre>
  );

  const renderArray = () => (
    <div className="space-y-1">
      {response!.output!.map((line, i) => (
        <div key={i} className="bg-slate-100 text-slate-800 p-2 rounded font-mono shadow-sm">
          {line}
        </div>
      ))}
    </div>
  );

  const renderSuccessNoOutput = () => (
    <div className="text-green-700 italic">Command succeeded (no output).</div>
  );

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <Loader className="animate-spin h-8 w-8 mb-2" />
          <p>Processing...</p>
          {lastCommand && <p className="text-sm mt-1">"{lastCommand}"</p>}
        </div>
      );
    }

    if (!response) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400 italic">
          <p>Enter a command to see output here.</p>
        </div>
      );
    }

    return (
      <>
        {renderUnderstood()}
        {response.status === "error" || response.error ? (
          renderError()
        ) : response.status === "missing_parameters" ? (
          renderMissingParams()
        ) : response.status === "confirmation_required" ? (
          renderConfirmationRequired()
        ) : response.status === "info" ? (
          renderInfo()
        ) : response.raw_output ? (
          renderRaw()
        ) : response.output && response.output.length > 0 ? (
          renderArray()
        ) : response.status === "success" ? (
          renderSuccessNoOutput()
        ) : (
          <div className="text-gray-400 italic">
            <p>No displayable content.</p>
          </div>
        )}
      </>
    );
  };

  return (
    <div className="flex flex-col h-full border border-slate-200 rounded-lg overflow-hidden bg-white shadow-md">
      {/* Header */}
      <div className="flex justify-between items-center bg-slate-50 px-4 py-2 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-800">Output</h3>
        <div className="flex space-x-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={handleCopyOutput}
            disabled={!response || isLoading}
            className="h-7"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onClear}
            disabled={!response || isLoading}
            className="h-7"
          >
            Clear
          </Button>
        </div>
      </div>

      {/* Body */}
      <div
        ref={outputRef}
        className={cn(
          "flex-grow overflow-auto p-4 bg-white text-sm font-sans",
          "scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent"
        )}
      >
        {renderContent()}
      </div>
    </div>
  );
};
