
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

type User = {
  id: number;
  name: string;
  avatar: string;
  status: "online" | "idle" | "offline";
  lastActive: string;
  project?: string;
  projectDetails?: string;
};

const ActiveUsers = () => {
  const [users, setUsers] = useState<User[]>([
    { 
      id: 1, 
      name: "Alex Smith", 
      avatar: "", 
      status: "online", 
      lastActive: "Just now",
      project: "Project #1",
      projectDetails: "OpenStack Command Center"
    },
    { 
      id: 2, 
      name: "Taylor Chen", 
      avatar: "", 
      status: "online", 
      lastActive: "5 min ago",
      project: "Project #2",
      projectDetails: "Network Security Module"
    },
    { 
      id: 3, 
      name: "Jamie Rodriguez", 
      avatar: "", 
      status: "idle", 
      lastActive: "10 min ago",
      project: "Project #1",
      projectDetails: "OpenStack Command Center"
    },
    { 
      id: 4, 
      name: "Morgan Lee", 
      avatar: "", 
      status: "online", 
      lastActive: "2 min ago",
      project: "Project #3",
      projectDetails: "Storage Optimization"
    },
    { 
      id: 5, 
      name: "Casey Johnson", 
      avatar: "", 
      status: "offline", 
      lastActive: "1 hr ago",
      project: "Project #2",
      projectDetails: "Network Security Module"
    }
  ]);

  // Simulate status changes
  useEffect(() => {
    const statusInterval = setInterval(() => {
      setUsers(prevUsers => {
        return prevUsers.map(user => {
          // Random chance to change status
          if (Math.random() > 0.8) {
            const statuses: Array<"online" | "idle" | "offline"> = ["online", "idle", "offline"];
            const newStatus = statuses[Math.floor(Math.random() * statuses.length)];
            
            // Update last active text based on new status
            let newLastActive = user.lastActive;
            if (user.status !== "online" && newStatus === "online") {
              newLastActive = "Just now";
            } else if (user.status === "online" && newStatus !== "online") {
              newLastActive = "A moment ago";
            }
            
            return {
              ...user,
              status: newStatus,
              lastActive: newLastActive
            };
          }
          return user;
        });
      });
    }, 10000); // Every 10 seconds
    
    return () => clearInterval(statusInterval);
  }, []);

  return (
    <div className="bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-white">Active Users</h3>
        <motion.div
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <Badge variant="outline" className="bg-blue-500/20 text-blue-300 border-blue-600/30">
            {users.filter(user => user.status === "online").length} Online
          </Badge>
        </motion.div>
      </div>
      
      <div className="space-y-3">
        <AnimatedUserList users={users} />
      </div>
    </div>
  );
};

const AnimatedUserList = ({ users }: { users: User[] }) => {
  return (
    <>
      {users.map((user) => (
        <motion.div 
          key={user.id} 
          className="flex items-center justify-between"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          whileHover={{ backgroundColor: "rgba(59, 130, 246, 0.05)", borderRadius: "0.375rem" }}
        >
          <div className="flex items-center gap-3">
            <motion.div 
              className="relative"
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring", stiffness: 400, damping: 10 }}
            >
              <Avatar>
                <AvatarImage src={user.avatar} />
                <AvatarFallback className="bg-blue-600/30 text-blue-200">
                  {user.name.split(' ').map(n => n[0]).join('')}
                </AvatarFallback>
              </Avatar>
              <motion.span
                className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-gray-800
                  ${user.status === "online" ? "bg-green-500" : 
                    user.status === "idle" ? "bg-yellow-500" : "bg-gray-500"}`}
                initial={{ scale: 0.8 }}
                animate={{ scale: [0.8, 1, 0.8], opacity: user.status === "online" ? [0.7, 1, 0.7] : 1 }}
                transition={{ 
                  repeat: user.status === "online" ? Infinity : 0,
                  duration: 2
                }}
              />
            </motion.div>
            <div>
              <p className="text-sm font-medium text-gray-200">{user.name}</p>
              <p className="text-xs text-gray-400">{user.lastActive}</p>
            </div>
          </div>
          
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge 
                  variant="outline" 
                  className="cursor-default bg-gray-700/50 text-gray-300 hover:bg-gray-700/80"
                >
                  {user.project}
                </Badge>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p className="text-xs">Working on: {user.projectDetails}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </motion.div>
      ))}
    </>
  );
};

export default ActiveUsers;
