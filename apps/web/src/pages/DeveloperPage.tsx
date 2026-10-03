import React, { useState } from "react";
import {
  AlertCircle,
  Check,
  Code,
  Copy,
  Key,
  Plus,
  Shield,
  Trash2,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import type { ApiKey } from "../types";

export function DeveloperPage() {
  const [keys, setKeys] = useState<ApiKey[]>([
    {
      id: "key-dev-101",
      workspace_id: "workspace-personal-001",
      name: "Research Notebook Integration",
      key_prefix: "sk_live_9a7b...",
      scopes: ["query:read", "projects:read"],
      status: "active",
      last_used_at: new Date(Date.now() - 3600000 * 24).toISOString(),
      created_at: new Date(Date.now() - 3600000 * 24 * 7).toISOString(),
    },
  ]);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    const rawSecret = `sk_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
    const newEntry: ApiKey = {
      id: `key-dev-${Date.now()}`,
      workspace_id: "workspace-personal-001",
      name: newKeyName.trim(),
      key_prefix: rawSecret.substring(0, 12) + "...",
      scopes: ["query:read", "projects:read"],
      status: "active",
      created_at: new Date().toISOString(),
    };

    setKeys([newEntry, ...keys]);
    setNewKeyName("");
    setShowCreateModal(false);
    setCreatedRawKey(rawSecret);
  };

  const handleRevokeKey = (id: string) => {
    setKeys(keys.filter((k) => k.id !== id));
  };

  const handleCopyKey = () => {
    if (createdRawKey) {
      navigator.clipboard.writeText(createdRawKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6 font-sans max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <Key className="w-5 h-5 text-indigo-600" />
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              Developer Platform API
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Programmatic access to your workspace documents, search indexes, and grounded RAG endpoints.
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          size="md"
          leftIcon={<Plus className="w-4 h-4" />}
        >
          Create API Key
        </Button>
      </div>

      {/* Security Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3 text-xs text-amber-800">
        <Shield className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Credential Protection (Master Architecture Page 7):</span>
          {" "}Platform API keys store only a cryptographic hash server-side and are displayed only once at creation.
          Server-side provider credentials (Gemini API keys, database passwords) are strictly protected and never exposed.
        </div>
      </div>

      {/* API Keys Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Active Workspace API Keys ({keys.length})
          </h2>
        </div>

        {keys.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No active API keys found. Create a key to access the REST API.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-6 py-3">Key Name</th>
                  <th className="px-6 py-3">Prefix / Hash</th>
                  <th className="px-6 py-3">Allowed Scopes</th>
                  <th className="px-6 py-3">Created</th>
                  <th className="px-6 py-3">Last Used</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {keys.map((k) => (
                  <tr key={k.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-3.5 font-semibold text-slate-900">{k.name}</td>
                    <td className="px-6 py-3.5 font-mono text-slate-600">{k.key_prefix}</td>
                    <td className="px-6 py-3.5">
                      <div className="flex flex-wrap gap-1">
                        {k.scopes.map((s) => (
                          <Badge key={s} variant="indigo">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-slate-500">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-3.5 text-slate-500">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <button
                        onClick={() => handleRevokeKey(k.id)}
                        className="text-slate-400 hover:text-red-600 p-1 rounded-md transition-colors"
                        title="Revoke API key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Code Examples Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Code className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Example API Query Request
            </h3>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">POST /api/v1/query</span>
        </div>

        <div className="bg-slate-900 text-slate-200 rounded-lg p-4 font-mono text-xs overflow-x-auto leading-relaxed">
          <pre>{`curl -X POST "http://localhost:8000/api/v1/query" \\
  -H "Authorization: Bearer sk_live_your_platform_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "project_id": "7b3b4b5e-...",
    "query": "What are the primary principles of quantum superposition?",
    "top_k": 5
  }'`}</pre>
        </div>
      </div>

      {/* Create Key Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Platform API Key"
        description="Name your key and assign programmatic access permissions."
      >
        <form onSubmit={handleCreateKey} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Key Name *
            </label>
            <input
              type="text"
              required
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="e.g. Python CLI Analysis Script"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Permitted Scope
            </label>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5 text-slate-600">
              <label className="flex items-center space-x-2">
                <input type="checkbox" defaultChecked disabled className="rounded text-indigo-600" />
                <span>query:read (Execute grounded RAG queries within workspace)</span>
              </label>
              <label className="flex items-center space-x-2">
                <input type="checkbox" defaultChecked disabled className="rounded text-indigo-600" />
                <span>projects:read (List workspace projects & sources)</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm">
              Generate Key
            </Button>
          </div>
        </form>
      </Modal>

      {/* Raw Key Display Modal */}
      <Modal
        isOpen={!!createdRawKey}
        onClose={() => setCreatedRawKey(null)}
        title="Save Your Platform API Key"
        description="Make sure to copy your API key now as you will not be able to view it again."
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
            <span>Store this key securely. Anyone with access to this token can query your workspace documents.</span>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="text"
              readOnly
              value={createdRawKey || ""}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 border border-slate-300 rounded-lg select-all"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyKey}
              leftIcon={copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
            >
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Button type="button" size="sm" onClick={() => setCreatedRawKey(null)}>
              Done
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
