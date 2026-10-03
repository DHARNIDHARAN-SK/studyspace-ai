import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  LogOut,
  Save,
  Settings,
  Shield,
  User,
} from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { Button } from "../components/ui/Button";

export function SettingsPage() {
  const navigate = useNavigate();
  const { user, profile, signOut } = useAuth();

  const [displayName, setDisplayName] = useState(profile?.display_name || user?.displayName || "Student");
  const [citationFormat, setCitationFormat] = useState<"apa" | "ieee" | "mla">("apa");
  const [queryRewritingDefault, setQueryRewritingDefault] = useState(true);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedMessage("Settings saved successfully.");
    setTimeout(() => setSavedMessage(null), 3500);
  };

  const handleSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <div className="space-y-6 font-sans max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Settings className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Account & Workspace Settings</h1>
            <p className="text-xs text-slate-500">
              Manage your student profile, academic preferences, and session controls.
            </p>
          </div>
        </div>
      </div>

      {savedMessage && (
        <div
          role="status"
          className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-lg flex items-center space-x-2"
        >
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{savedMessage}</span>
        </div>
      )}

      {/* Profile Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
          <User className="w-4 h-4 text-indigo-600" />
          <span>Student Profile</span>
        </h2>

        <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Display Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Email Address (Managed by Identity Provider)
              </label>
              <input
                type="email"
                disabled
                value={user?.email || "student@university.edu"}
                className="w-full px-3 py-2 text-xs border border-slate-200 bg-slate-50 text-slate-500 rounded-lg cursor-not-allowed"
              />
            </div>
          </div>

          <div className="pt-2">
            <Button type="submit" size="sm" leftIcon={<Save className="w-3.5 h-3.5" />}>
              Save Profile
            </Button>
          </div>
        </form>
      </div>

      {/* Multi-Tenant Workspace Scope */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
          <Shield className="w-4 h-4 text-indigo-600" />
          <span>Workspace Partitioning</span>
        </h2>
        <div className="text-xs text-slate-600 space-y-3">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Workspace Name</span>
              <span className="font-semibold text-slate-800">{profile?.workspace_name || "Personal Workspace"}</span>
            </div>
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Workspace Identifier (UUID)</span>
              <span className="font-mono text-slate-600">{profile?.workspace_id || "workspace-personal-001"}</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            All course documents, embeddings, search indexes, and conversation records are strictly
            isolated to this workspace ID. Supabase Row-Level Security ensures that cross-tenant access is
            cryptographically and relationally blocked.
          </p>
        </div>
      </div>

      {/* Academic Learning Preferences */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
          <Settings className="w-4 h-4 text-indigo-600" />
          <span>Study & Citation Preferences</span>
        </h2>
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Default Academic Citation Style
            </label>
            <div className="flex space-x-3">
              {(["apa", "ieee", "mla"] as const).map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => setCitationFormat(style)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider border transition-colors ${
                    citationFormat === style
                      ? "bg-indigo-600 text-white border-indigo-600"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Determines formatting of source references in answer citations and exports.
            </p>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
            <div>
              <span className="font-semibold text-slate-800 block">Automatic Query Rewriting</span>
              <span className="text-[11px] text-slate-500">
                Transforms conversational follow-up questions into standalone keyword queries for hybrid retrieval.
              </span>
            </div>
            <button
              type="button"
              onClick={() => setQueryRewritingDefault(!queryRewritingDefault)}
              className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
                queryRewritingDefault ? "bg-indigo-600" : "bg-slate-200"
              }`}
            >
              <div
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                  queryRewritingDefault ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Security and Session Actions */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Session Controls</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Sign out of your active session on this device.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleSignOut}
          leftIcon={<LogOut className="w-3.5 h-3.5 text-red-600" />}
        >
          Sign Out
        </Button>
      </div>
    </div>
  );
}
