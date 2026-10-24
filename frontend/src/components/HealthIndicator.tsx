import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { HealthStatus } from '../types/document';
import { Activity, Database } from 'lucide-react';

export const HealthIndicator: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<boolean>(false);

  const fetchHealth = async () => {
    try {
      const data = await api.checkHealth();
      setHealth(data);
      setError(false);
    } catch {
      setError(true);
      setHealth(null);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center space-x-3 text-xs">
      {error ? (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-medium">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-rose-500 animate-pulse"></span>
          Backend Offline
        </span>
      ) : health ? (
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
            <Activity className="w-3.5 h-3.5 mr-1.5" />
            API Connected
          </span>
          <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
            <Database className="w-3.5 h-3.5 mr-1.5" />
            SQLite {health.database}
          </span>
        </div>
      ) : (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-medium">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-slate-500 animate-pulse"></span>
          Checking Health...
        </span>
      )}
    </div>
  );
};
