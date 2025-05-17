import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ChevronRight, 
  Code, 
  Database, 
  Terminal as TerminalIcon, 
  Users, 
  Settings, 
  LogOut, 
  User, 
  ChevronDown,
  Cpu,
  Network,
  Shield,
  Cloud,
  PanelRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import ParticleBackground from "@/components/ParticleBackground";
import CodeTester from "@/components/CodeTester";
import ActiveUsers from "@/components/ActiveUsers";
import InstancesOverview from "@/components/InstancesOverview";
import { useToast } from "@/hooks/use-toast";

const Home = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [showSettings, setShowSettings] = useState(false);

  const handleLogout = () => {
    toast({
      title: "Logged out",
      description: "You have been successfully logged out",
    });
    // In a real app, you would clear user session here
    setTimeout(() => navigate("/login"), 1000);
  };

  const handleSettings = () => {
    setShowSettings(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black overflow-hidden relative">
      {/* Particle animation background - now fixed position */}
      <ParticleBackground />
      
      {/* Settings dialog */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="bg-gray-800 border-gray-700 text-white">
          <DialogHeader>
            <DialogTitle className="text-2xl text-gradient-to-r from-blue-400 to-purple-500">Settings</DialogTitle>
            <DialogDescription className="text-gray-300">
              Configure your OpenStack Command Center preferences.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-6 py-4">
            <div className="grid gap-2">
              <h3 className="text-lg font-medium text-gray-200">Appearance</h3>
              <div className="flex items-center justify-between border-b border-gray-700 py-2">
                <span className="text-gray-300">Dark Mode</span>
                <Button variant="ghost" className="hover:bg-gray-700">
                  Always On
                </Button>
              </div>
              <div className="flex items-center justify-between border-b border-gray-700 py-2">
                <span className="text-gray-300">Animations</span>
                <Button variant="ghost" className="hover:bg-gray-700">
                  Enabled
                </Button>
              </div>
            </div>
            
            <div className="grid gap-2">
              <h3 className="text-lg font-medium text-gray-200">Account</h3>
              <div className="flex items-center justify-between border-b border-gray-700 py-2">
                <span className="text-gray-300">Email Notifications</span>
                <Button variant="ghost" className="hover:bg-gray-700">
                  Enabled
                </Button>
              </div>
              <div className="flex items-center justify-between border-b border-gray-700 py-2">
                <span className="text-gray-300">Two-factor Authentication</span>
                <Button variant="ghost" className="hover:bg-gray-700">
                  Enable
                </Button>
              </div>
            </div>
            
            <div className="grid gap-2">
              <h3 className="text-lg font-medium text-gray-200">Terminal</h3>
              <div className="flex items-center justify-between border-b border-gray-700 py-2">
                <span className="text-gray-300">Terminal Font Size</span>
                <Button variant="ghost" className="hover:bg-gray-700">
                  Medium
                </Button>
              </div>
              <div className="flex items-center justify-between border-b border-gray-700 py-2">
                <span className="text-gray-300">Command History Length</span>
                <Button variant="ghost" className="hover:bg-gray-700">
                  100
                </Button>
              </div>
            </div>
            
            <Button onClick={() => setShowSettings(false)} className="mt-4 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Header/Navigation */}
      <nav className="relative z-10 flex justify-between items-center py-4 px-6 md:px-10 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <TerminalIcon className="h-6 w-6 text-blue-400" />
          <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            OpenStack Command Center
          </h2>
        </div>
        
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleSettings}
            className="text-gray-400 hover:text-white hover:bg-gray-800 relative"
          >
            <Settings className="h-5 w-5" />
            <motion.span 
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full"
            />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2 text-gray-300 hover:text-white hover:bg-gray-800">
                <Avatar className="h-7 w-7 mr-1">
                  <AvatarImage src="" />
                  <AvatarFallback className="bg-blue-600/30 text-blue-200">
                    U
                  </AvatarFallback>
                </Avatar>
                <span className="hidden md:inline">User</span>
                <ChevronDown className="h-4 w-4 text-gray-500" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56 bg-gray-900 border-gray-700 text-gray-200">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem 
                className="flex gap-2 cursor-pointer hover:bg-gray-800"
                onClick={() => navigate("/profile")}
              >
                <User className="h-4 w-4" /> Profile
              </DropdownMenuItem>
              <DropdownMenuItem 
                className="flex gap-2 cursor-pointer hover:bg-gray-800"
                onClick={handleSettings}
              >
                <Settings className="h-4 w-4" /> Settings
              </DropdownMenuItem>
              <DropdownMenuItem 
                className="flex gap-2 cursor-pointer hover:bg-gray-800" 
                onClick={() => navigate("/dashboard")}
              >
                <Database className="h-4 w-4" /> Dashboard
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem 
                className="flex gap-2 text-red-400 cursor-pointer hover:bg-gray-800 hover:text-red-300"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" /> Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </nav>

      {/* Hero section */}
      <div className="container mx-auto px-4 pt-16 md:pt-24 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 pt-8 pb-24">
          <motion.div 
            className="flex flex-col justify-center space-y-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <motion.h1 
              className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2 }}
            >
              <span className="block text-white">Control OpenStack with</span>
              <motion.span 
                className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500"
                initial={{ backgroundPosition: "0% 0%" }}
                animate={{ backgroundPosition: "100% 0%" }}
                transition={{ duration: 5, repeat: Infinity, repeatType: "reverse" }}
              >
                Natural Language
              </motion.span>
            </motion.h1>
            <motion.p 
              className="text-lg text-gray-300 max-w-lg"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.4 }}
            >
              Control your OpenStack environment using simple, natural language commands. No complex syntax or technical knowledge required.
            </motion.p>
            <motion.div 
              className="flex flex-col sm:flex-row gap-4 pt-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.6 }}
            >
              <Button
                onClick={() => navigate("/terminal")}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-6 py-6 h-auto text-lg relative overflow-hidden group"
              >
                <motion.span 
                  className="absolute inset-0 bg-white/10 transform translate-y-full"
                  initial={{ y: "100%" }}
                  whileHover={{ y: "0%" }}
                  transition={{ duration: 0.3 }}
                />
                Try It Now <ChevronRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button
                variant="outline"
                className="border-gray-700 text-gray-300 hover:bg-gray-800 px-6 py-6 h-auto text-lg relative overflow-hidden group"
              >
                <motion.span 
                  className="absolute inset-0 bg-gray-700/30 transform translate-y-full"
                  initial={{ y: "100%" }}
                  whileHover={{ y: "0%" }}
                  transition={{ duration: 0.3 }}
                />
                View Demo
              </Button>
            </motion.div>
          </motion.div>

          <motion.div
            className="hidden lg:flex justify-center items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="relative w-full max-w-md">
              <motion.div 
                className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-lg filter blur-xl"
                animate={{ 
                  scale: [1, 1.05, 1],
                  opacity: [0.5, 0.7, 0.5]
                }}
                transition={{ 
                  duration: 4, 
                  repeat: Infinity,
                  repeatType: "reverse"
                }}
              />
              <div className="relative bg-gray-900 border border-gray-800 rounded-lg p-4 shadow-2xl">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex space-x-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  </div>
                  <div className="text-xs text-gray-500">terminal</div>
                </div>
                <div className="font-mono text-sm text-gray-300">
                  <p className="text-green-500">$ <span className="text-gray-300">list all servers</span></p>
                  <p className="mt-2 text-gray-400">ID: 1, Name: vm-alpha, Status: ACTIVE, Image: Ubuntu 20.04</p>
                  <p className="text-gray-400">ID: 2, Name: vm-beta, Status: BUILD, Image: CentOS 8</p>
                  <p className="mt-2 text-green-500">$ <span className="text-gray-300">create new vm with name test-vm image ubuntu</span></p>
                  <p className="mt-1 text-gray-400">Creating VM 'test-vm' with Ubuntu image...</p>
                  <p className="text-gray-400">VM created successfully!</p>
                  <p className="mt-2 text-green-500">$ <span className="text-blue-400 animate-pulse">_</span></p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Testing section */}
      <div className="bg-gray-900 py-20 relative">
        <div className="absolute inset-0 bg-grid-white/5 [mask-image:linear-gradient(to_bottom,transparent,black)]"></div>
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
              Try It Out
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Test our natural language command interface with this interactive demo
            </p>
          </motion.div>

          <div className="max-w-4xl mx-auto">
            <CodeTester />
          </div>
        </div>
      </div>

      {/* User & Instances Section */}
      <div className="bg-gray-800/50 py-20 relative">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
              System Overview
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Monitor your instances and collaborate with team members
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              viewport={{ once: true }}
            >
              <InstancesOverview />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              viewport={{ once: true }}
            >
              <ActiveUsers />
            </motion.div>
          </div>
        </div>
      </div>

      {/* Feature section */}
      <div className="bg-transparent py-20 relative">
        <div className="absolute inset-0 bg-grid-white/5 [mask-image:linear-gradient(to_bottom,transparent,white)]"></div>
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
              Powerful Features
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Everything you need to manage your OpenStack environment efficiently
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {[
              {
                icon: <TerminalIcon className="h-6 w-6" />,
                title: "Natural Language Commands",
                description: "Control your infrastructure using simple, conversational commands in plain English"
              },
              {
                icon: <Code className="h-6 w-6" />,
                title: "Zero Syntax Learning",
                description: "No need to memorize complex OpenStack CLI commands or syntax"
              },
              {
                icon: <Database className="h-6 w-6" />,
                title: "Complete OpenStack Control",
                description: "Manage instances, networks, storage, and all other OpenStack resources"
              },
              {
                icon: <Network className="h-6 w-6" />,
                title: "Network Management",
                description: "Create, modify, and monitor virtual networks with simple language instructions"
              },
              {
                icon: <Cpu className="h-6 w-6" />,
                title: "Resource Optimization",
                description: "AI-powered suggestions to optimize your cloud resource usage and costs"
              },
              {
                icon: <Shield className="h-6 w-6" />,
                title: "Security Controls",
                description: "Enforce security policies and monitor compliance with natural language"
              },
              {
                icon: <Cloud className="h-6 w-6" />,
                title: "Multi-Cloud Support",
                description: "Extend natural language control to AWS, Azure, and GCP resources"
              },
              {
                icon: <Users className="h-6 w-6" />,
                title: "Team Collaboration",
                description: "Share resources and collaborate with team members in real-time"
              },
              {
                icon: <PanelRight className="h-6 w-6" />,
                title: "Custom Dashboards",
                description: "Create personalized dashboards showing the metrics that matter to you"
              }
            ].map((feature, index) => (
              <motion.div
                key={index}
                className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-blue-500/50 transition-all duration-300"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -5, boxShadow: "0 10px 25px -5px rgba(59, 130, 246, 0.1)" }}
              >
                <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 p-3 rounded-full w-fit mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-2 text-white">{feature.title}</h3>
                <p className="text-gray-400">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800 py-10 relative z-10">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center mb-4 md:mb-0">
              <TerminalIcon className="h-6 w-6 text-blue-400 mr-2" />
              <span className="text-lg font-semibold text-white">OpenStack Command Center</span>
            </div>
            <div className="flex space-x-6">
              <a href="#" className="text-gray-400 hover:text-white transition-colors">Documentation</a>
              <a href="#" className="text-gray-400 hover:text-white transition-colors">API</a>
              <a href="#" className="text-gray-400 hover:text-white transition-colors">Support</a>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-500 text-sm mb-4 md:mb-0">&copy; 2025 OpenStack Command Center. All rights reserved.</p>
            <div className="flex space-x-6">
              <a href="#" className="text-gray-500 hover:text-white transition-colors text-sm">Privacy Policy</a>
              <a href="#" className="text-gray-500 hover:text-white transition-colors text-sm">Terms of Service</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;
