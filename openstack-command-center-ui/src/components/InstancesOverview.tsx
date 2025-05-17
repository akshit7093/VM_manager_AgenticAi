
import { Server, CloudOff, Activity } from "lucide-react";
import { Progress } from "@/components/ui/progress";

const instances = [
  {
    id: "vm-01",
    name: "production-api",
    status: "running",
    usage: 76,
    ip: "10.0.0.5",
    image: "Ubuntu 22.04",
    flavor: "medium"
  },
  {
    id: "vm-02",
    name: "db-primary",
    status: "running",
    usage: 82,
    ip: "10.0.0.6",
    image: "CentOS 8",
    flavor: "large"
  },
  {
    id: "vm-03",
    name: "test-env",
    status: "stopped",
    usage: 0,
    ip: "10.0.0.7",
    image: "Debian 11",
    flavor: "small"
  }
];

const InstancesOverview = () => {
  return (
    <div className="bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-white">My Instances</h3>
        <span className="text-sm text-gray-400">Total: {instances.length}</span>
      </div>
      
      <div className="space-y-4">
        {instances.map((instance) => (
          <div key={instance.id} className="border border-gray-700 rounded-md p-3 bg-gray-900/50">
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2">
                {instance.status === "running" ? (
                  <Server className="h-4 w-4 text-green-400" />
                ) : (
                  <CloudOff className="h-4 w-4 text-gray-500" />
                )}
                <span className="font-medium text-white">{instance.name}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                instance.status === "running" 
                  ? "bg-green-900/30 text-green-400"
                  : "bg-gray-900/30 text-gray-400"
              }`}>
                {instance.status}
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-3 text-xs text-gray-400">
              <div>
                <span className="block text-gray-500">ID</span>
                {instance.id}
              </div>
              <div>
                <span className="block text-gray-500">IP</span>
                {instance.ip}
              </div>
              <div>
                <span className="block text-gray-500">Image</span>
                {instance.image}
              </div>
              <div>
                <span className="block text-gray-500">Size</span>
                {instance.flavor}
              </div>
            </div>
            
            {instance.status === "running" && (
              <div className="mt-3">
                <div className="flex justify-between items-center mb-1 text-xs">
                  <div className="flex items-center gap-1">
                    <Activity className="h-3 w-3 text-blue-400" />
                    <span className="text-gray-400">CPU Usage</span>
                  </div>
                  <span className={`
                    ${instance.usage > 80 ? "text-red-400" : 
                      instance.usage > 60 ? "text-yellow-400" : "text-green-400"}
                  `}>
                    {instance.usage}%
                  </span>
                </div>
                <Progress 
                  value={instance.usage} 
                  className="h-1.5 bg-gray-700" 
                  indicatorClassName={`
                    ${instance.usage > 80 ? "bg-red-500" : 
                      instance.usage > 60 ? "bg-yellow-500" : "bg-green-500"}
                  `}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default InstancesOverview;
