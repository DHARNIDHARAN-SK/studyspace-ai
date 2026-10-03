import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Calendar,
  Folder,
  FolderPlus,
  Layers,
  Shield,
  Trash2,
} from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { useProjects } from "../features/projects/ProjectContext";
import { CreateProjectModal } from "../features/projects/CreateProjectModal";

export function DashboardPage() {
  const { user, profile } = useAuth();
  const { projects, loading, deleteExistingProject } = useProjects();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (e: React.MouseEvent, projectId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this project?")) {
      setDeletingId(projectId);
      try {
        await deleteExistingProject(projectId);
      } finally {
        setDeletingId(null);
      }
    }
  };

  return (
    <div className="space-y-8 font-sans">
      {/* Greeting Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Welcome back, {profile?.display_name || user?.displayName || "Student"}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Workspace: <span className="font-semibold text-slate-700">{profile?.workspace_name || "Personal Workspace"}</span>
            {" "}&bull; All materials and chats are private to this workspace.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors shrink-0"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Grid Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-600">
              Your Academic Projects ({projects.length})
            </h2>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400">Loading workspace projects...</div>
        ) : projects.length === 0 ? (
          /* Empty State */
          <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center shadow-sm">
            <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 mx-auto flex items-center justify-center mb-3">
              <FolderPlus className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-800">No projects created yet</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Create your first project to start organizing subject textbooks, lecture slides, notes, and study sessions.
            </p>
            <div className="mt-5">
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
              >
                <FolderPlus className="w-4 h-4" />
                <span>Create Your First Project</span>
              </button>
            </div>
          </div>
        ) : (
          /* Project Cards Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="group bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                      <Folder className="w-5 h-5" />
                    </div>
                    {p.subject && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full border border-slate-200">
                        {p.subject}
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 mt-3 group-hover:text-indigo-600 transition-colors">
                    {p.name}
                  </h3>

                  {p.description && (
                    <p className="text-xs text-slate-500 mt-1.5 line-clamp-2 leading-relaxed">
                      {p.description}
                    </p>
                  )}
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                  <div className="flex items-center space-x-1.5">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Updated {new Date(p.updated_at).toLocaleDateString()}</span>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, p.id)}
                    disabled={deletingId === p.id}
                    className="text-slate-400 hover:text-red-600 p-1 rounded transition-colors"
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Tenant Privacy Notice */}
      <div className="bg-slate-100/70 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 text-xs text-slate-600">
        <Shield className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-800">Multi-Tenant Isolation Enforced:</span>
          {" "}All projects, documents, and chats are strictly partitioned by workspace ID and protected by Supabase Row-Level Security. Another student or external user cannot view or query your project data.
        </div>
      </div>

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
}
