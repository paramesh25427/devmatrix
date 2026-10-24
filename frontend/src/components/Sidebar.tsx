import React from 'react';
import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  CheckSquare,
  ListTree,
  Calculator,
  ShieldAlert,
  Users,
  Activity,
  BarChart3,
  FileDown,
  Settings,
  LogOut,
  Sparkles,
} from 'lucide-react';
import { UserProfile } from '../types/auth';
import { HealthIndicator } from './HealthIndicator';

export type ActiveTab =
  | 'dashboard'
  | 'projects'
  | 'documents'
  | 'requirements'
  | 'wbs'
  | 'estimation'
  | 'risks'
  | 'workforce'
  | 'execution'
  | 'analytics'
  | 'reports'
  | 'admin';

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  currentUser: UserProfile | null;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  currentUser,
  onLogout,
}) => {
  const navItems = [
    { id: 'dashboard' as ActiveTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects' as ActiveTab, label: 'Projects & Intake', icon: FolderKanban },
    { id: 'documents' as ActiveTab, label: 'Document Vault', icon: FileText },
    { id: 'requirements' as ActiveTab, label: 'Requirements Baseline', icon: CheckSquare },
    { id: 'wbs' as ActiveTab, label: 'WBS & Planning', icon: ListTree },
    { id: 'estimation' as ActiveTab, label: 'Effort & Schedule', icon: Calculator },
    { id: 'risks' as ActiveTab, label: 'Risks & Feasibility', icon: ShieldAlert },
    { id: 'workforce' as ActiveTab, label: 'Workforce Intelligence', icon: Users },
    { id: 'execution' as ActiveTab, label: 'Execution & Progress', icon: Activity },
    { id: 'analytics' as ActiveTab, label: 'Delivery Analytics', icon: BarChart3 },
    { id: 'reports' as ActiveTab, label: 'PDF Reports', icon: FileDown },
    { id: 'admin' as ActiveTab, label: 'Administration & Audit', icon: Settings },
  ];

  const roleLabels: Record<string, string> = {
    tenant_admin: 'Tenant Admin',
    delivery_manager: 'Delivery Manager',
    project_lead: 'Project Lead',
    contributor: 'Contributor',
  };

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col h-screen select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-white text-base tracking-tight leading-none">DevMatrix AI</h1>
            <p className="text-[11px] text-indigo-400 font-medium tracking-wide mt-1">Delivery Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1 scrollbar-thin scrollbar-thumb-slate-800">
        <div className="px-3 pb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Planning & Delivery
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Backend Health Check */}
      <div className="px-4 py-3 border-t border-slate-900 bg-slate-950/80">
        <HealthIndicator />
      </div>

      {/* User Session Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <p className="text-xs font-semibold text-slate-200 truncate">
              {currentUser?.full_name || 'Alex Morgan'}
            </p>
            <p className="text-[11px] text-indigo-400 font-medium truncate">
              {currentUser?.role ? roleLabels[currentUser.role] || currentUser.role : 'Delivery Manager'}
            </p>
          </div>
          <button
            onClick={onLogout}
            title="Sign Out"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
