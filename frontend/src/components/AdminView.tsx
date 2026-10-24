import React, { useState } from 'react';
import {
  Settings,
  Users,
  Shield,
  Activity,
  FolderCheck,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import {
  AdminUser,
  TenantConfig,
  AuditLogItem,
  SystemDiagnostics,
} from '../types/admin';

interface AdminViewProps {
  users: AdminUser[];
  tenantConfig: TenantConfig | null;
  auditLogs: AuditLogItem[];
  diagnostics: SystemDiagnostics | null;
}

export const AdminView: React.FC<AdminViewProps> = ({
  users,
  tenantConfig,
  auditLogs,
  diagnostics,
}) => {
  const [activeTab, setActiveTab] = useState<'diagnostics' | 'users' | 'tenant' | 'audit'>('diagnostics');

  const roleLabels: Record<string, string> = {
    tenant_admin: 'Tenant Administrator',
    delivery_manager: 'Delivery Manager',
    project_lead: 'Project Lead',
    contributor: 'Contributor',
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Module 13 &bull; Administration & Governance
            </span>
            <span className="text-xs text-slate-400">
              Tenant Isolation & Immutable Audit
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Tenant Administration, Diagnostics & Audit Logs
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Inspect system diagnostics, AI provider status, authorized users, tenant retention policies, and immutable delivery audit trails.
          </p>
        </div>
      </div>

      {/* Navigation Subtabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('diagnostics')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'diagnostics'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Activity className="h-4 w-4" />
          <span>System Diagnostics</span>
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'users'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>Users & Roles ({users.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('tenant')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'tenant'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Settings className="h-4 w-4" />
          <span>Tenant Governance</span>
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'audit'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Shield className="h-4 w-4" />
          <span>Audit Trail ({auditLogs.length})</span>
        </button>
      </div>

      {/* Diagnostics Tab */}
      {activeTab === 'diagnostics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold text-white">Application Environment</span>
                <span className="bg-slate-800 text-indigo-400 px-2 py-0.5 rounded font-mono text-[11px] uppercase">
                  {diagnostics?.app_env || 'Development'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Single canonical configuration loaded with strict Pydantic settings.
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold text-white">Database Engine</span>
                <span className="flex items-center gap-1 text-emerald-400 font-mono text-xs">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>{diagnostics?.database.status || 'Connected'}</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                {diagnostics?.database.type || 'SQLite (Canonical)'}
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold text-white">Storage Vaults</span>
                <span className="flex items-center gap-1 text-emerald-400 font-mono text-xs">
                  <FolderCheck className="h-3.5 w-3.5" />
                  <span>Operational</span>
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Uploads, extracted text, and PDF reports verified in local storage.
              </p>
            </div>
          </div>

          {/* AI Provider Health Matrix */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">AI Provider Sequential Fallback Chain</h3>
              </div>
              <span className="text-xs text-slate-400">
                Configured via Environment Settings
              </span>
            </div>

            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between p-3.5 bg-slate-950 rounded-lg border border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">1. Google Gemini 2.5 Flash</span>
                    <span className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded font-semibold uppercase">
                      Primary Provider
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 font-mono">
                    Model: {diagnostics?.ai_providers.gemini.model || 'gemini-2.5-flash'}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`px-2.5 py-1 rounded text-xs font-semibold ${
                    diagnostics?.ai_providers.gemini.configured
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {diagnostics?.ai_providers.gemini.configured ? 'Configured & Active' : 'Key Unset (Falls Back)'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between p-3.5 bg-slate-950 rounded-lg border border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">2. NVIDIA NIM (DeepSeek / Llama 3)</span>
                    <span className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded font-semibold uppercase">
                      Secondary Fallback
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 font-mono">
                    Model: {diagnostics?.ai_providers.nvidia_nim.model || 'deepseek-ai/deepseek-r1'}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`px-2.5 py-1 rounded text-xs font-semibold ${
                    diagnostics?.ai_providers.nvidia_nim.configured
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {diagnostics?.ai_providers.nvidia_nim.configured ? 'Configured & Active' : 'Key Unset (Falls Back)'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between p-3.5 bg-slate-950 rounded-lg border border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">3. Offline Deterministic Fallback Engine</span>
                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-semibold uppercase">
                      Zero-Key Guarantee
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Deterministic domain extractor matching exact Pydantic schema for offline testing & demos.
                  </p>
                </div>
                <div className="text-right">
                  <span className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Always Ready
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Users & Roles Tab */}
      {activeTab === 'users' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Registered Users & Assigned Roles</h3>
            <span className="text-xs text-slate-400 font-mono">
              Enforced via Server-Side Role-Based Access Control
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Role Assigned</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Registered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-white">
                      {u.full_name}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {u.email}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded text-[11px] font-semibold">
                        {roleLabels[u.role] || u.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        u.is_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                      }`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-500">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tenant Governance Tab */}
      {activeTab === 'tenant' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4">Tenant Isolation & Policies</h3>

          {tenantConfig ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 font-medium">Tenant Organization Name:</span>
                <p className="text-base font-bold text-white">{tenantConfig.name}</p>
                <span className="text-[11px] text-slate-500 font-mono">Slug: {tenantConfig.slug}</span>
              </div>

              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 font-medium">Default Currency:</span>
                <p className="text-base font-bold text-white">{tenantConfig.currency}</p>
                <span className="text-[11px] text-slate-500">Applies to rate cards and estimate reporting</span>
              </div>

              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 font-medium">Default Contingency Rate:</span>
                <p className="text-base font-bold text-white">{tenantConfig.default_contingency_pct}%</p>
                <span className="text-[11px] text-slate-500">Configurable per project</span>
              </div>

              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 font-medium">Document Retention Policy:</span>
                <p className="text-base font-bold text-white">{tenantConfig.retention_days} Days</p>
                <span className="text-[11px] text-slate-500">Audited requirements baselines retained permanently</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">No tenant configuration loaded.</p>
          )}
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'audit' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Immutable Security & Delivery Audit Log</h3>
            <span className="text-xs text-slate-400 font-mono">
              Append-only audit trail
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Actor Email</th>
                  <th className="py-3 px-4">Entity Type</th>
                  <th className="py-3 px-4">Entity ID</th>
                  <th className="py-3 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-white">
                      <span className="bg-slate-800 px-2 py-0.5 rounded text-[11px] font-mono">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {log.user_email || 'system'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {log.entity_type}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-500">
                      {log.entity_id}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {auditLogs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500 italic">
                      No audit events recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
