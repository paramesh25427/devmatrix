import React, { useState } from 'react';
import { Shield, Sparkles, AlertCircle, Lock, Mail, X, User } from 'lucide-react';
import { api } from '../services/api';
import { UserProfile } from '../types/auth';

interface LoginModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onLoginSuccess: (user: UserProfile) => void;
}

const PRESET_ACCOUNTS = [
  {
    role: 'delivery_manager',
    label: 'Delivery Manager',
    email: 'manager@devmatrix.local',
    name: 'Alex Morgan',
    badge: 'Workforce & WBS Full Access',
    color: 'border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10',
  },
  {
    role: 'tenant_admin',
    label: 'Tenant Administrator',
    email: 'admin@devmatrix.local',
    name: 'Sarah Connor',
    badge: 'Admin Console & Audit',
    color: 'border-purple-500/30 text-purple-300 hover:bg-purple-500/10',
  },
  {
    role: 'project_lead',
    label: 'Project Lead',
    email: 'lead@devmatrix.local',
    name: 'David Chen',
    badge: 'Planning & Baselines',
    color: 'border-blue-500/30 text-blue-300 hover:bg-blue-500/10',
  },
  {
    role: 'contributor',
    label: 'Contributor',
    email: 'contributor@devmatrix.local',
    name: 'Elena Rostova',
    badge: 'Task Delivery & Evidence',
    color: 'border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10',
  },
];

export const LoginModal: React.FC<LoginModalProps> = ({
  isOpen,
  onClose,
  onLoginSuccess,
}) => {
  const [email, setEmail] = useState<string>('manager@devmatrix.local');
  const [password, setPassword] = useState<string>('DevMatrix2026!');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  if (!isOpen) return null;

  const handleLogin = async (e?: React.FormEvent, customEmail?: string, customPass?: string) => {
    if (e) e.preventDefault();
    const loginEmail = customEmail || email;
    const loginPass = customPass || password;

    setLoading(true);
    setErrorMsg('');
    try {
      await api.login(loginEmail, loginPass);
      const profile = await api.getProfile();
      onLoginSuccess(profile);
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (presetEmail: string) => {
    setEmail(presetEmail);
    setPassword('DevMatrix2026!');
    handleLogin(undefined, presetEmail, 'DevMatrix2026!');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 my-8 relative">
        {/* Close Button if user can cancel */}
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white transition cursor-pointer p-1"
          >
            <X className="h-5 w-5" />
          </button>
        )}

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center mx-auto shadow-lg shadow-indigo-500/25">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Sign In to DevMatrix AI</h2>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            Access workforce intelligence, deterministic scheduling, and executive delivery reporting.
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-lg text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={(e) => handleLogin(e)} className="space-y-3.5 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1.5">Email Address</label>
            <div className="relative">
              <Mail className="h-4 w-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="manager@devmatrix.local"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1.5">Password</label>
            <div className="relative">
              <Lock className="h-4 w-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
            <span className="text-[10px] text-slate-500 mt-1 block">Default password for demo accounts is <strong>DevMatrix2026!</strong></span>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/20 transition cursor-pointer flex items-center justify-center gap-2 mt-2"
          >
            {loading ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <Shield className="h-4 w-4" />
                <span>Sign In</span>
              </>
            )}
          </button>
        </form>

        {/* Quick Role Switcher */}
        <div className="pt-3 border-t border-slate-800">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 text-center">
            Or Click a Demo Account to Sign In:
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {PRESET_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                onClick={() => handleSelectPreset(acc.email)}
                className={`p-2.5 bg-slate-950 border rounded-lg text-left transition cursor-pointer ${acc.color}`}
              >
                <div className="flex items-center gap-1 font-semibold text-white">
                  <User className="h-3 w-3 text-slate-400" />
                  <span className="truncate">{acc.name}</span>
                </div>
                <div className="text-[10px] text-slate-400 truncate mt-0.5">{acc.label}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
