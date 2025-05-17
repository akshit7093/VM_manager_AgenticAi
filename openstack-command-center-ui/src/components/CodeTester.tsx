
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChevronRight, Code, Play, Terminal as TerminalIcon } from "lucide-react";

const CodeTester = () => {
  const [code, setCode] = useState(`// Test your OpenStack commands here
list all servers
create new vm with name test-vm image ubuntu
resize vm test-vm to medium`);
  const [output, setOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const runCode = () => {
    setIsLoading(true);
    // Simulate execution with a timed response
    setTimeout(() => {
      setOutput(`> list all servers
ID: 1, Name: vm-alpha, Status: ACTIVE, Image: Ubuntu 20.04
ID: 2, Name: vm-beta, Status: BUILD, Image: CentOS 8

> create new vm with name test-vm image ubuntu
Creating VM 'test-vm' with Ubuntu image...
VM created successfully!
ID: 3, Name: test-vm, Status: ACTIVE, Image: Ubuntu 20.04

> resize vm test-vm to medium
Resizing VM 'test-vm'...
VM successfully resized to flavor 'medium'
`);
      setIsLoading(false);
    }, 1500);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden shadow-xl">
      <div className="flex items-center justify-between bg-gray-900 px-4 py-2 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Code className="h-4 w-4 text-blue-400" />
          <h3 className="font-medium text-gray-200">OpenStack Command Tester</h3>
        </div>
        <div className="flex space-x-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
        </div>
      </div>
      
      <Tabs defaultValue="code" className="w-full">
        <TabsList className="bg-gray-900 border-b border-gray-700 w-full justify-start rounded-none px-4">
          <TabsTrigger value="code" className="data-[state=active]:bg-gray-800 data-[state=active]:text-white">
            <Code className="h-4 w-4 mr-2" /> Code
          </TabsTrigger>
          <TabsTrigger value="output" className="data-[state=active]:bg-gray-800 data-[state=active]:text-white">
            <TerminalIcon className="h-4 w-4 mr-2" /> Output
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="code" className="p-0 m-0">
          <div className="relative">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-64 bg-gray-900 text-gray-300 p-4 font-mono text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
              spellCheck="false"
            />
            <Button
              size="sm"
              onClick={runCode}
              disabled={isLoading}
              className="absolute bottom-4 right-4 bg-blue-600 hover:bg-blue-700"
            >
              {isLoading ? (
                "Running..."
              ) : (
                <>
                  <Play className="h-4 w-4 mr-1" /> Run
                </>
              )}
            </Button>
          </div>
        </TabsContent>
        
        <TabsContent value="output" className="p-0 m-0">
          <pre className="w-full h-64 bg-gray-900 text-green-400 p-4 font-mono text-sm overflow-auto">
            {output || "Run your code to see the output here..."}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CodeTester;
