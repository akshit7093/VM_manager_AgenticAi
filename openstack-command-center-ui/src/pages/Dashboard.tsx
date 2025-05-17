
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { 
  Terminal, Activity, Server, HardDrive, Cpu, Globe, Cloud, 
  RefreshCcw, Settings, Calendar, Info, AlertTriangle
} from "lucide-react";
import { useNavigate } from "react-router-dom";

// Mock data for the charts
const instanceData = [
  { name: "Jan", active: 40, stopped: 24 },
  { name: "Feb", active: 30, stopped: 13 },
  { name: "Mar", active: 20, stopped: 8 },
  { name: "Apr", active: 27, stopped: 10 },
  { name: "May", active: 18, stopped: 7 },
  { name: "Jun", active: 23, stopped: 11 },
  { name: "Jul", active: 34, stopped: 15 },
];

const cpuUsageData = [
  { name: "00:00", usage: 30 },
  { name: "03:00", usage: 25 },
  { name: "06:00", usage: 20 },
  { name: "09:00", usage: 45 },
  { name: "12:00", usage: 65 },
  { name: "15:00", usage: 70 },
  { name: "18:00", usage: 60 },
  { name: "21:00", usage: 50 },
];

const storageData = [
  { name: "Volume 1", value: 400, color: "#3b82f6" },
  { name: "Volume 2", value: 300, color: "#8b5cf6" },
  { name: "Volume 3", value: 200, color: "#ec4899" },
  { name: "Volume 4", value: 100, color: "#22c55e" },
];

const networkData = [
  { name: "Mon", inbound: 24, outbound: 18 },
  { name: "Tue", inbound: 30, outbound: 22 },
  { name: "Wed", inbound: 42, outbound: 30 },
  { name: "Thu", inbound: 28, outbound: 20 },
  { name: "Fri", inbound: 36, outbound: 25 },
  { name: "Sat", inbound: 20, outbound: 15 },
  { name: "Sun", inbound: 15, outbound: 10 },
];

// Alert mock data
const alertsData = [
  {
    id: 1,
    severity: "high",
    message: "Instance vm-alpha CPU usage above 90%",
    time: "10 minutes ago"
  },
  {
    id: 2,
    severity: "medium",
    message: "Storage volume nearly full (85%)",
    time: "1 hour ago"
  },
  {
    id: 3,
    severity: "low",
    message: "Network latency increased on public network",
    time: "3 hours ago"
  }
];

const instancesStatusData = [
  { name: "Active", value: 65, color: "#22c55e" },
  { name: "Building", value: 10, color: "#3b82f6" },
  { name: "Error", value: 5, color: "#ef4444" },
  { name: "Stopped", value: 20, color: "#6b7280" },
];

const Dashboard = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    // Simulate loading data
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Terminal className="h-6 w-6 text-blue-400" />
            <h1 className="text-xl font-bold text-white">OpenStack Dashboard</h1>
          </div>
          <nav className="hidden md:flex space-x-2">
            <Button 
              variant={activeTab === "overview" ? "secondary" : "ghost"} 
              size="sm" 
              className="text-gray-300"
              onClick={() => setActiveTab("overview")}
            >
              Overview
            </Button>
            <Button 
              variant={activeTab === "instances" ? "secondary" : "ghost"} 
              size="sm" 
              className="text-gray-300"
              onClick={() => setActiveTab("instances")}
            >
              Instances
            </Button>
            <Button 
              variant={activeTab === "storage" ? "secondary" : "ghost"} 
              size="sm" 
              className="text-gray-300"
              onClick={() => setActiveTab("storage")}
            >
              Storage
            </Button>
            <Button 
              variant={activeTab === "network" ? "secondary" : "ghost"} 
              size="sm" 
              className="text-gray-300"
              onClick={() => setActiveTab("network")}
            >
              Network
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-gray-300"
              onClick={() => navigate("/terminal")}
            >
              Terminal
            </Button>
          </nav>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-white hover:bg-gray-800"
              onClick={handleRefresh}
            >
              <RefreshCcw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-white hover:bg-gray-800"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Dashboard content */}
      <div className="container mx-auto p-4">
        <Tabs defaultValue="overview" className="space-y-6" onValueChange={setActiveTab} value={activeTab}>
          <div className="flex justify-between items-center">
            <TabsList className="bg-gray-800 border border-gray-700">
              <TabsTrigger value="overview" className="data-[state=active]:bg-gray-700">
                <Activity className="h-4 w-4 mr-2" /> Overview
              </TabsTrigger>
              <TabsTrigger value="instances" className="data-[state=active]:bg-gray-700">
                <Server className="h-4 w-4 mr-2" /> Instances
              </TabsTrigger>
              <TabsTrigger value="storage" className="data-[state=active]:bg-gray-700">
                <HardDrive className="h-4 w-4 mr-2" /> Storage
              </TabsTrigger>
              <TabsTrigger value="network" className="data-[state=active]:bg-gray-700">
                <Globe className="h-4 w-4 mr-2" /> Network
              </TabsTrigger>
            </TabsList>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Calendar className="h-4 w-4" />
              <span>Last updated: {new Date().toLocaleTimeString()}</span>
            </div>
          </div>

          {/* Overview tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {[
                { title: "Total Instances", value: "42", icon: Server, color: "blue" },
                { title: "CPU Usage", value: "65%", icon: Cpu, color: "purple" },
                { title: "Storage Used", value: "1.8 TB", icon: HardDrive, color: "pink" },
                { title: "Networks", value: "5", icon: Globe, color: "green" }
              ].map((stat, index) => (
                <motion.div
                  key={stat.title}
                  className={`bg-gray-800 border border-gray-700 rounded-lg overflow-hidden shadow-lg`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.1 * index }}
                >
                  <div className="px-4 py-5 sm:p-6 flex justify-between items-center">
                    <div>
                      <p className="text-sm font-medium text-gray-400">{stat.title}</p>
                      <p className="text-2xl font-semibold text-white">{stat.value}</p>
                    </div>
                    <div className={`p-3 rounded-full bg-${stat.color}-500/20`}>
                      <stat.icon className={`h-6 w-6 text-${stat.color}-500`} />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.2 }}
              >
                <Card className="bg-gray-800 border-gray-700 shadow-lg h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-white text-lg flex items-center">
                      <Activity className="h-5 w-5 mr-2 text-blue-400" /> 
                      Instance Statistics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {isLoading ? (
                      <div className="flex justify-center items-center h-64">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={instanceData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                          <defs>
                            <linearGradient id="colorActive" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id="colorStopped" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#6b7280" stopOpacity={0.8}/>
                              <stop offset="95%" stopColor="#6b7280" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="name" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#f9fafb" }} />
                          <Legend />
                          <Line type="monotone" dataKey="active" stroke="#3b82f6" strokeWidth={2} activeDot={{ r: 8 }} />
                          <Line type="monotone" dataKey="stopped" stroke="#6b7280" strokeWidth={2} />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.3 }}
              >
                <Card className="bg-gray-800 border-gray-700 shadow-lg h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-white text-lg flex items-center">
                      <Cpu className="h-5 w-5 mr-2 text-purple-400" /> 
                      CPU Usage Trends
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {isLoading ? (
                      <div className="flex justify-center items-center h-64">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height={240}>
                        <AreaChart data={cpuUsageData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                          <defs>
                            <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="name" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#f9fafb" }} />
                          <Area type="monotone" dataKey="usage" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorUsage)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.4 }}
                className="lg:col-span-1"
              >
                <Card className="bg-gray-800 border-gray-700 shadow-lg h-full">
                  <CardHeader>
                    <CardTitle className="text-white text-lg flex items-center">
                      <AlertTriangle className="h-5 w-5 mr-2 text-amber-400" /> 
                      Recent Alerts
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {isLoading ? (
                      <div className="flex justify-center items-center h-[232px]">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-500"></div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {alertsData.map((alert) => (
                          <div 
                            key={alert.id} 
                            className="p-3 rounded-lg border bg-gray-800 border-gray-700 flex items-start gap-3"
                          >
                            <div className={`p-2 rounded-full ${
                              alert.severity === "high" 
                                ? "bg-red-500/20 text-red-500" 
                                : alert.severity === "medium" 
                                ? "bg-amber-500/20 text-amber-500" 
                                : "bg-blue-500/20 text-blue-500"
                            }`}>
                              <Info className="h-4 w-4" />
                            </div>
                            <div className="flex-1">
                              <p className="text-sm text-white font-medium">{alert.message}</p>
                              <p className="text-xs text-gray-400">{alert.time}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.5 }}
                className="lg:col-span-2"
              >
                <Card className="bg-gray-800 border-gray-700 shadow-lg h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-white text-lg flex items-center">
                      <Server className="h-5 w-5 mr-2 text-green-400" /> 
                      Instance Status Distribution
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 flex items-center justify-center">
                    {isLoading ? (
                      <div className="flex justify-center items-center h-[210px]">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-500"></div>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 w-full">
                        <div>
                          <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                              <Pie
                                data={instancesStatusData}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                outerRadius={80}
                                innerRadius={50}
                                fill="#8884d8"
                                dataKey="value"
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                              >
                                {instancesStatusData.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                              </Pie>
                              <Tooltip 
                                formatter={(value, name) => [`${value} instances`, name]}
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#f9fafb" }}
                              />
                            </PieChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex flex-col justify-center">
                          <div className="space-y-2">
                            {instancesStatusData.map((item) => (
                              <div key={item.name} className="flex items-center">
                                <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: item.color }}></div>
                                <span className="text-sm text-gray-300">{item.name}</span>
                                <span className="ml-auto text-sm font-medium text-white">{item.value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </TabsContent>

          {/* Instances tab */}
          <TabsContent value="instances">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="space-y-6"
            >
              <Card className="bg-gray-800 border-gray-700 shadow-lg">
                <CardHeader>
                  <CardTitle className="text-white text-lg flex items-center">
                    <Server className="h-5 w-5 mr-2 text-blue-400" /> 
                    Instance Activities
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4">
                  {isLoading ? (
                    <div className="flex justify-center items-center h-80">
                      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={instanceData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                        <defs>
                          <linearGradient id="colorBar1" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.4}/>
                          </linearGradient>
                          <linearGradient id="colorBar2" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6b7280" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#6b7280" stopOpacity={0.4}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" />
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#f9fafb" }} />
                        <Legend />
                        <Bar dataKey="active" name="Active Instances" fill="url(#colorBar1)" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="stopped" name="Stopped Instances" fill="url(#colorBar2)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </TabsContent>

          {/* Storage tab */}
          <TabsContent value="storage">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="space-y-6"
            >
              <Card className="bg-gray-800 border-gray-700 shadow-lg">
                <CardHeader>
                  <CardTitle className="text-white text-lg flex items-center">
                    <HardDrive className="h-5 w-5 mr-2 text-purple-400" /> 
                    Storage Allocation
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4">
                  {isLoading ? (
                    <div className="flex justify-center items-center h-80">
                      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={storageData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          outerRadius={100}
                          fill="#8884d8"
                          dataKey="value"
                          label={({ name, value }) => `${name}: ${value} GB`}
                        >
                          {storageData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#f9fafb" }} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </TabsContent>

          {/* Network tab */}
          <TabsContent value="network">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="space-y-6"
            >
              <Card className="bg-gray-800 border-gray-700 shadow-lg">
                <CardHeader>
                  <CardTitle className="text-white text-lg flex items-center">
                    <Globe className="h-5 w-5 mr-2 text-green-400" /> 
                    Network Traffic
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4">
                  {isLoading ? (
                    <div className="flex justify-center items-center h-80">
                      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-500"></div>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={networkData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorInbound" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="colorOutbound" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" />
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#f9fafb" }} />
                        <Legend />
                        <Area type="monotone" dataKey="inbound" stroke="#22c55e" fillOpacity={1} fill="url(#colorInbound)" />
                        <Area type="monotone" dataKey="outbound" stroke="#3b82f6" fillOpacity={1} fill="url(#colorOutbound)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;
