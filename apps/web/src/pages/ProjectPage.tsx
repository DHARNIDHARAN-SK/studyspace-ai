import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  CheckSquare,
  Edit2,
  FileText,
  Folder,
  HelpCircle,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { getProject } from "../lib/api-client";
import { useProjects } from "../features/projects/ProjectContext";
import { ChatTab } from "../features/workspace/ChatTab";
import { SourcesTab } from "../features/workspace/SourcesTab";
import { RevisionTab } from "../features/workspace/RevisionTab";
import { QuizzesTab } from "../features/workspace/QuizzesTab";
import { GuidesTab } from "../features/workspace/GuidesTab";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import type { Project } from "../types";

export function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const { updateExistingProject, deleteExistingProject } = useProjects();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "sources" | "revision" | "quizzes" | "guides">("chat");

  // Edit and Delete Modals
  const [showEditModal, setShowEditModal] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!token || !projectId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    getProject(token, projectId)
      .then((p) => {
        if (isMounted) {
          setProject(p);
          setEditName(p.name);
          setEditDesc(p.description || "");
          setEditSubject(p.subject || "");
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

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !editName.trim()) return;
    setIsUpdating(true);
    try {
      const updated = await updateExistingProject(projectId, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
        subject: editSubject.trim() || undefined,
      });
      setProject(updated);
      setShowEditModal(false);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!projectId) return;
    setIsDeleting(true);
    try {
      await deleteExistingProject(projectId);
      navigate("/projects");
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-slate-400 font-sans">
        Loading project workspace...
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center max-w-lg mx-auto font-sans shadow-xs">
        <h2 className="text-base font-bold text-slate-800">Project Unavailable</h2>
        <p className="text-xs text-slate-500 mt-2">
          {error || "Project could not be found in your authorized workspace."}
        </p>
        <Link
          to="/projects"
          className="mt-4 inline-flex items-center space-x-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Projects</span>
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
        <div className="flex items-center space-x-2 text-xs text-slate-500">
          <Link to="/projects" className="hover:text-slate-900 transition-colors">
            Projects
          </Link>
          <span>/</span>
          <span className="font-semibold text-slate-900 truncate max-w-[200px] sm:max-w-md">
            {project.name}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowEditModal(true)}
            className="inline-flex items-center space-x-1.5 text-xs text-slate-600 hover:text-slate-900 px-2 py-1 rounded-md hover:bg-slate-100 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Edit Details</span>
          </button>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-red-600 px-2 py-1 rounded-md hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Delete</span>
          </button>
        </div>
      </div>

      {/* Project Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold shrink-0">
              <Folder className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">{project.name}</h1>
                {project.subject && <Badge variant="indigo">{project.subject}</Badge>}
              </div>
              {project.description && (
                <p className="text-xs text-slate-500 mt-1">{project.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs text-slate-400 shrink-0">
            <Calendar className="w-3.5 h-3.5" />
            <span>Updated {new Date(project.updated_at).toLocaleDateString()}</span>
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

      {/* Active Tab Content Area */}
      <div>
        {activeTab === "chat" && <ChatTab project={project} />}
        {activeTab === "sources" && <SourcesTab project={project} />}
        {activeTab === "revision" && <RevisionTab project={project} />}
        {activeTab === "quizzes" && <QuizzesTab project={project} />}
        {activeTab === "guides" && <GuidesTab project={project} />}
      </div>

      {/* Edit Project Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Edit Project Details"
        description="Update project name, subject discipline, or description."
      >
        <form onSubmit={handleUpdate} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Project Name *
            </label>
            <input
              type="text"
              required
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Subject / Discipline
            </label>
            <input
              type="text"
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description
            </label>
            <textarea
              rows={3}
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 resize-none"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button type="button" variant="outline" size="sm" onClick={() => setShowEditModal(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" isLoading={isUpdating}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Project"
        description="Are you sure you want to permanently delete this project?"
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            This action cannot be undone. All documents, chunk embeddings, chat history, and quizzes in "{project.name}" will be deleted.
          </div>
          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button type="button" variant="outline" size="sm" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button type="button" variant="danger" size="sm" isLoading={isDeleting} onClick={handleDelete}>
              Confirm Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
