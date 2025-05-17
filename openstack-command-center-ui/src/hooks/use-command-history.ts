
import { useState, useEffect } from 'react';

export interface CommandHistoryItem {
  id: string;
  query: string;
  timestamp: Date;
  status: 'pending' | 'success' | 'error';
  response?: any;
}

export const useCommandHistory = (maxSize = 50) => {
  const [history, setHistory] = useState<CommandHistoryItem[]>([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem('commandHistory');
      if (savedHistory) {
        const parsedHistory = JSON.parse(savedHistory).map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp)
        }));
        setHistory(parsedHistory);
      }
    } catch (error) {
      console.error('Error loading command history:', error);
    }
  }, []);

  // Save history to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem('commandHistory', JSON.stringify(history));
    } catch (error) {
      console.error('Error saving command history:', error);
    }
  }, [history]);

  // Add a new command to history
  const addCommand = (query: string): string => {
    const id = Date.now().toString();
    const newCommand: CommandHistoryItem = {
      id,
      query,
      timestamp: new Date(),
      status: 'pending'
    };

    setHistory(prev => {
      const updated = [newCommand, ...prev].slice(0, maxSize);
      return updated;
    });

    return id;
  };

  // Update a command in the history
  const updateCommand = (id: string, updates: Partial<CommandHistoryItem>) => {
    setHistory(prev => 
      prev.map(item => 
        item.id === id ? { ...item, ...updates } : item
      )
    );
  };

  // Clear all history
  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('commandHistory');
  };

  return {
    history,
    addCommand,
    updateCommand,
    clearHistory
  };
};
