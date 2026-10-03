import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  CheckSquare,
  FileText,
  Folder,
  HelpCircle,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { getProject } from "../lib/api-client";
import { useProjects } from "../features/projects/ProjectContext";
import type { Project } from "../types";

export function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const { deleteExistingProject } = useProjects();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "sources" | "revision" | "quizzes" | "guides">("chat");

  useEffect(() => {
    if (!token || !projectId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    getProject(token, projectId)
      .then((p) => {
        if (isMounted) {
          setProject(p);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load project");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [token, projectId]);

  const handleDelete = async () => {
    if (!projectId) return;
    if (confirm("Are you sure you want to delete this project? All associated resources will be permanently removed.")) {
      await deleteExistingProject(projectId);
      navigate("/dashboard");
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-xs text-slate-400">Loading project workspace...</div>;
  }

  if (error || !project) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center max-w-lg mx-auto">
        <h2 className="text-base font-bold text-slate-800">Project Unavailable</h2>
        <p className="text-xs text-slate-500 mt-2">{error || "Project could not be found in your authorized workspace."}</p>
        <Link
          to="/dashboard"
          className="mt-4 inline-flex items-center space-x-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
      </div>
    );
  }

  const tabs = [
    { id: "chat", label: "Grounded Chat", icon: MessageSquare },
    { id: "sources", label: "Sources & Documents", icon: FileText },
    { id: "revision", label: "Revision Checklist", icon: CheckSquare },
    { id: "quizzes", label: "Quizzes", icon: HelpCircle },
    { id: "guides", label: "Study Guides", icon: BookOpen },
  ] as const;

  return (
    <div className="space-y-6 font-sans">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between">
        <Link
          to="/dashboard"
          className="inline-flex items-center space-x-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>All Projects</span>
        </Link>
        <button
          onClick={handleDelete}
          className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-red-600 px-2 py-1 rounded transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Delete Project</span>
        </button>
      </div>

      {/* Project Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              <Folder className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">{project.name}</h1>
                {project.subject && (
                  <span className="text-[10px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-full border border-slate-200">
                    {project.subject}
                  </span>
                )}
              </div>
              {project.description && (
                <p className="text-xs text-slate-500 mt-1">{project.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <Calendar className="w-3.5 h-3.5" />
            <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Workspace Sub-Navigation Tabs */}
        <div className="mt-6 border-b border-slate-200 flex space-x-6 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-3 border-b-2 text-xs font-semibold whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content Workspace Placeholder */}
      <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm text-center">
        <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-500 mx-auto flex items-center justify-center mb-3">
          <BookOpen className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
          {tabs.find((t) => t.id === activeTab)?.label}
        </h3>
        <p className="text-xs text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
          Phase 2 verified: User authentication, workspace context, and project CRUD are active.
          Document upload, Celery ingestion, and RAG pipelines unlock in upcoming phases per the master roadmap.
        </p>
      </div>
    </div>
  );
}
