
import { Terminal } from "@/components/Terminal";

const Index = () => {
  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <header className="mb-4 text-center">
        <h1 className="text-2xl font-bold text-white">OpenStack Command Center</h1>
        <p className="text-gray-400">Control your OpenStack environment using natural language commands</p>
      </header>
      <Terminal />
    </div>
  );
};

export default Index;
