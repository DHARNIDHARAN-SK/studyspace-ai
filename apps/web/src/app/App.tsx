import { useEffect, useState } from "react";
import { Activity, BookOpen, CheckCircle, Database, Server, Shield } from "lucide-react";
import { checkBackendHealth } from "../lib/api-client";
import type { HealthResponse } from "../types";

export function App() {
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    checkBackendHealth()
      .then((data) => {
        if (isMounted) {
          setBackendHealth(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Unable to reach backend API");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Navigation Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-indigo-600 text-white p-2 rounded-lg flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg text-slate-900 tracking-tight">StudySpace AI</span>
              <span className="ml-2 text-xs font-medium px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full border border-slate-200">
                Phase 1 Baseline
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>System Initialized</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-10 space-y-8">
        {/* Hero Section */}
        <section className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Academic Document Intelligence Platform
          </h1>
          <p className="mt-3 text-base text-slate-600 max-w-3xl leading-relaxed">
            Phase 1 Foundation established. Multi-tenant document intelligence SaaS for students and independent learners,
            enforcing strict source-grounded answering, verified citations, private data isolation, and provider independence.
          </p>
        </section>

        {/* Health Check & Verification Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Frontend Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <span className="text-sm font-semibold text-slate-700">Frontend Service</span>
              <Activity className="w-5 h-5 text-indigo-600" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex items-center space-x-2 text-sm text-emerald-700">
                <CheckCircle className="w-4 h-4" />
                <span className="font-medium">Vite + React + TypeScript Operational</span>
              </div>
              <p className="text-xs text-slate-500">Tailwind CSS & design tokens ready</p>
            </div>
          </div>

          {/* Backend Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <span className="text-sm font-semibold text-slate-700">Backend API (FastAPI)</span>
              <Server className="w-5 h-5 text-indigo-600" />
            </div>
            <div className="mt-4 space-y-2">
              {loading && <p className="text-xs text-slate-400">Pinging /api/v1/health...</p>}
              {backendHealth && (
                <div className="space-y-1">
                  <div className="flex items-center space-x-2 text-sm text-emerald-700">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-medium">Status: {backendHealth.status}</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Version: {backendHealth.version} ({backendHealth.environment})
                  </p>
                </div>
              )}
              {error && (
                <div className="space-y-1">
                  <div className="text-sm text-amber-700 font-medium">Backend Inactive or Disconnected</div>
                  <p className="text-xs text-slate-500">Run backend on port 8000: <code className="bg-slate-100 px-1 py-0.5 rounded">uvicorn app.main:app</code></p>
                </div>
              )}
            </div>
          </div>

          {/* Database & Migrations Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <span className="text-sm font-semibold text-slate-700">Database & RLS</span>
              <Database className="w-5 h-5 text-indigo-600" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex items-center space-x-2 text-sm text-emerald-700">
                <CheckCircle className="w-4 h-4" />
                <span className="font-medium">18 Entities & Migrations Defined</span>
              </div>
              <p className="text-xs text-slate-500">pgvector (768-dim), RLS, lexical search</p>
            </div>
          </div>
        </section>

        {/* Architecture Principles Bar */}
        <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4 flex items-center space-x-2">
            <Shield className="w-4 h-4 text-indigo-600" />
            <span>Master Architecture Guarantees</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs text-slate-600">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="font-semibold text-slate-800 block mb-1">Evidence First</span>
              Grounded answers strictly require cited source evidence; explicit abstention otherwise.
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="font-semibold text-slate-800 block mb-1">Private by Default</span>
              Multi-tenant isolation enforced via workspace scoping and Row-Level Security.
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="font-semibold text-slate-800 block mb-1">Provider Independent</span>
              Decoupled provider adapters for Ollama, Gemini, embeddings, and rerankers.
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="font-semibold text-slate-800 block mb-1">Measurable Quality</span>
              Retrieval and answer generation benchmarked against versioned evaluation sets.
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center text-xs text-slate-500">
          StudySpace AI — Master Architecture Baseline v0.1.0 &copy; 2026
        </div>
      </footer>
    </div>
  );
}
