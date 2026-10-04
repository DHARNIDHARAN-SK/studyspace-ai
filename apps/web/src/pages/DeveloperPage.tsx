import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Code,
  Copy,
  Key,
  Loader2,
  Plus,
  RefreshCw,
  Send,
  Shield,
  Trash2,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { useAuth } from "../features/auth/AuthContext";
import {
  createApiKey,
  listApiKeys,
  revokeApiKey,
  submitDeveloperAccessRequest,
} from "../lib/api-client";
import type { ApiKey, DeveloperAccessRequestInput } from "../types";

export function DeveloperPage() {
  const { token, user } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states:
  // Step 1: Intake/Request Form
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [isSubmittingRequest, setIsSubmittingRequest] = useState(false);
  const [requestData, setRequestData] = useState<DeveloperAccessRequestInput>({
    name: user?.displayName || "",
    organization: "",
    email: user?.email || "",
    phone: "",
    intended_use: "",
    help_needed: "",
    heard_about: "",
    additional_message: "",
  });

  // Step 2: Key Configuration Form
  const [showKeyConfigModal, setShowKeyConfigModal] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["chat:write", "retrieval:read"]);
  const [expiryDays, setExpiryDays] = useState<number>(90);
  const [isCreatingKey, setIsCreatingKey] = useState(false);

  // Step 3: Raw Key Created Display
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      setError(null);
      const fetchedKeys = await listApiKeys(token);
      setKeys(fetchedKeys);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load API keys.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  // Handle Step 1 Submit (Intake Request Form)
  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSubmittingRequest(true);
    setError(null);

    try {
      await submitDeveloperAccessRequest(token, requestData);
      setShowRequestModal(false);
      // Proceed to Step 2: Configure and generate key
      setKeyName(`${requestData.organization || requestData.name} Integration`);
      setShowKeyConfigModal(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit access request.");
    } finally {
      setIsSubmittingRequest(false);
    }
  };

  // Handle Step 2 Submit (Generate Key)
  const handleKeyConfigSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !keyName.trim()) return;
    setIsCreatingKey(true);
    setError(null);

    try {
      const res = await createApiKey(token, {
        name: keyName.trim(),
        scopes: selectedScopes,
        expires_in_days: expiryDays,
      });
      setShowKeyConfigModal(false);
      setCreatedRawKey(res.raw_key);
      await fetchKeys();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate API key.");
    } finally {
      setIsCreatingKey(false);
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (!token) return;
    const confirmRevoke = window.confirm(
      "Are you sure you want to revoke this API key? This action is immediate and cannot be undone."
    );
    if (!confirmRevoke) return;

    setRevokingId(id);
    try {
      await revokeApiKey(token, id);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to revoke API key.");
    } finally {
      setRevokingId(null);
    }
  };

  const handleCopyKey = () => {
    if (createdRawKey) {
      navigator.clipboard.writeText(createdRawKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const toggleScope = (scope: string) => {
    if (selectedScopes.includes(scope)) {
      setSelectedScopes(selectedScopes.filter((s) => s !== scope));
    } else {
      setSelectedScopes([...selectedScopes, scope]);
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
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => fetchKeys()}
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            onClick={() => {
              setError(null);
              setShowRequestModal(true);
            }}
            size="sm"
            leftIcon={<Plus className="w-3.5 h-3.5" />}
          >
            Create API Key
          </Button>
        </div>
      </div>

      {/* Security Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3 text-xs text-amber-800">
        <Shield className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Credential Protection:</span>
          {" "}Platform API keys store only a cryptographic SHA-256 hash server-side and are displayed only once at creation.
          All programmatic requests are rate-limited via Redis and scoped to authorized workspace projects.
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* API Keys Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Active Workspace API Keys ({keys.length})
          </h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
            <span>Loading API keys...</span>
          </div>
        ) : keys.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No active API keys found. Click "Create API Key" to submit an access request and provision a key.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-6 py-3">Key Name</th>
                  <th className="px-6 py-3">Masked Prefix</th>
                  <th className="px-6 py-3">Allowed Scopes</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Created</th>
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
                    <td className="px-6 py-3.5">
                      <Badge variant={k.status === "active" ? "emerald" : "slate"}>
                        {k.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5 text-slate-500">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      {k.status === "active" && (
                        <button
                          onClick={() => handleRevokeKey(k.id)}
                          disabled={revokingId === k.id}
                          className="text-red-500 hover:text-red-700 text-xs font-semibold inline-flex items-center space-x-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Revoke</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Programmatic API Documentation Snippet */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center space-x-2">
          <Code className="w-4 h-4 text-indigo-600" />
          <h3 className="text-sm font-bold text-slate-900">Programmatic API Quickstart</h3>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          Authenticate programmatic requests with your secret key using the <code className="bg-slate-100 px-1 py-0.5 rounded text-indigo-600">X-API-Key</code> header:
        </p>
        <div className="bg-slate-900 rounded-lg p-4 font-mono text-[11px] text-slate-100 overflow-x-auto space-y-2">
          <div className="text-slate-400"># 1. Programmatic Chat Query</div>
          <div>curl -X POST http://localhost:8000/api/v1/dev/chat \</div>
          <div>  -H "X-API-Key: sk_live_your_secret_key" \</div>
          <div>  -H "Content-Type: application/json" \</div>
          <div>{"  -d '{\"message\": \"What is PaaS?\", \"project_id\": \"YOUR_PROJECT_UUID\"}'"}</div>
        </div>
      </div>

      {/* MODAL 1: Professional Developer Access Request Form */}
      <Modal
        isOpen={showRequestModal}
        onClose={() => setShowRequestModal(false)}
        title="Developer API Access Request"
      >
        <form onSubmit={handleRequestSubmit} className="space-y-4 text-xs font-sans">
          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3 text-indigo-800 leading-relaxed text-[11px]">
            Please tell us about your intended integration. Your request details are reviewed by our engineering lead at <span className="font-semibold">karnan284858@gmail.com</span> before issuing production API keys.
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Your Full Name *
              </label>
              <input
                type="text"
                required
                value={requestData.name}
                onChange={(e) => setRequestData({ ...requestData, name: e.target.value })}
                placeholder="Dr. Alan Turing"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Organization / Institution *
              </label>
              <input
                type="text"
                required
                value={requestData.organization}
                onChange={(e) => setRequestData({ ...requestData, organization: e.target.value })}
                placeholder="University Research Lab"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Academic / Contact Email *
              </label>
              <input
                type="email"
                required
                value={requestData.email}
                onChange={(e) => setRequestData({ ...requestData, email: e.target.value })}
                placeholder="developer@institution.edu"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Phone / Contact Details *
              </label>
              <input
                type="tel"
                required
                value={requestData.phone}
                onChange={(e) => setRequestData({ ...requestData, phone: e.target.value })}
                placeholder="+1 555-0199 or 9080284858"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Intended API Use *
            </label>
            <input
              type="text"
              required
              value={requestData.intended_use}
              onChange={(e) => setRequestData({ ...requestData, intended_use: e.target.value })}
              placeholder="e.g. Automated course quiz generation for undergraduate AI syllabus"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              What help or capability do you need? *
            </label>
            <input
              type="text"
              required
              value={requestData.help_needed}
              onChange={(e) => setRequestData({ ...requestData, help_needed: e.target.value })}
              placeholder="e.g. Grounded hybrid RAG endpoints and rate limit allocation"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              How did you hear about StudySpace AI? *
            </label>
            <input
              type="text"
              required
              value={requestData.heard_about}
              onChange={(e) => setRequestData({ ...requestData, heard_about: e.target.value })}
              placeholder="e.g. GitHub repository, LinkedIn, Academic conference, Colleague"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Additional Message or Requirements (Optional)
            </label>
            <textarea
              rows={2}
              value={requestData.additional_message}
              onChange={(e) => setRequestData({ ...requestData, additional_message: e.target.value })}
              placeholder="Any custom token quotas, webhook needs, or project scopes..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div className="pt-2 flex items-center justify-end space-x-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowRequestModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmittingRequest}
              leftIcon={isSubmittingRequest ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : undefined}
              rightIcon={!isSubmittingRequest ? <Send className="w-3.5 h-3.5" /> : undefined}
            >
              {isSubmittingRequest ? "Submitting Request..." : "Submit Request & Continue"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: Key Configuration Form */}
      <Modal
        isOpen={showKeyConfigModal}
        onClose={() => setShowKeyConfigModal(false)}
        title="Configure & Issue API Key"
      >
        <form onSubmit={handleKeyConfigSubmit} className="space-y-4 text-xs font-sans">
          <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3 text-emerald-800 text-[11px] flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>Intake request verified and notified to lead developer. Now configure your key.</span>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              API Key Name *
            </label>
            <input
              type="text"
              required
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              placeholder="e.g. Research Pipeline Integration"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Allowed Scopes *
            </label>
            <div className="space-y-2">
              {[
                { scope: "chat:write", label: "chat:write — Programmatic RAG chat endpoint" },
                { scope: "retrieval:read", label: "retrieval:read — Hybrid document retrieval & search" },
                { scope: "revision:read", label: "revision:read — Read syllabus revision topics" },
              ].map(({ scope, label }) => (
                <label key={scope} className="flex items-center space-x-2 text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedScopes.includes(scope)}
                    onChange={() => toggleScope(scope)}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Expiration
            </label>
            <select
              value={expiryDays}
              onChange={(e) => setExpiryDays(Number(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            >
              <option value={30}>30 Days</option>
              <option value={90}>90 Days (Recommended)</option>
              <option value={180}>180 Days</option>
              <option value={365}>1 Year</option>
            </select>
          </div>

          <div className="pt-2 flex items-center justify-end space-x-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowKeyConfigModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isCreatingKey || !keyName.trim()}
              leftIcon={isCreatingKey ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : undefined}
            >
              {isCreatingKey ? "Generating Key..." : "Generate API Key"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 3: Raw Key Display (Shown ONCE) */}
      <Modal
        isOpen={Boolean(createdRawKey)}
        onClose={() => setCreatedRawKey(null)}
        title="Your Secret API Key"
      >
        <div className="space-y-4 text-xs font-sans">
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px] leading-relaxed">
            <span className="font-bold">Save this key now!</span> For security, StudySpace AI never stores the plaintext secret. You will not be able to view this secret again.
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Secret API Key
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                readOnly
                value={createdRawKey || ""}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 font-mono text-xs select-all focus:outline-none"
              />
              <Button
                type="button"
                onClick={handleCopyKey}
                size="sm"
                variant={copied ? "primary" : "outline"}
                leftIcon={copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              >
                {copied ? "Copied!" : "Copy"}
              </Button>
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <Button size="sm" onClick={() => setCreatedRawKey(null)}>
              I Have Saved My Secret Key
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
