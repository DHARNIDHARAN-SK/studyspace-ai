import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Calendar,
  Edit2,
  Folder,
  FolderPlus,
  Layers,
  Search,
  Trash2,
} from "lucide-react";
import { useProjects } from "../features/projects/ProjectContext";
import { CreateProjectModal } from "../features/projects/CreateProjectModal";
import { Modal } from "../components/ui/Modal";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import type { Project } from "../types";

export function ProjectsPage() {
  const navigate = useNavigate();
  const { projects, loading, updateExistingProject, deleteExistingProject } = useProjects();

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSubject, setSelectedSubject] = useState<string>("All");
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Edit Project State
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  // Delete Project State
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Extract unique subjects
  const subjects = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => {
      if (p.subject) set.add(p.subject);
    });
    return ["All", ...Array.from(set)];
  }, [projects]);

  // Filter projects
  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      const matchesSearch =
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesSubject = selectedSubject === "All" || p.subject === selectedSubject;
      return matchesSearch && matchesSubject;
    });
  }, [projects, searchQuery, selectedSubject]);

  const openEditModal = (p: Project) => {
    setEditingProject(p);
    setEditName(p.name);
    setEditDescription(p.description || "");
    setEditSubject(p.subject || "");
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject) return;
    setIsUpdating(true);
    try {
      await updateExistingProject(editingProject.id, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
        subject: editSubject.trim() || undefined,
      });
      setEditingProject(null);
    } finally {
      setIsUpdating(false);
    }
  };

  const confirmDelete = async () => {
    if (!deletingProject) return;
    setIsDeleting(true);
    try {
      await deleteExistingProject(deletingProject.id);
      setDeletingProject(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-indigo-600" />
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              Academic Projects
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage your courses, uploaded materials, and grounded study sessions.
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          size="md"
          leftIcon={<FolderPlus className="w-4 h-4" />}
        >
          New Project
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search projects by name or description..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
          />
        </div>

        {/* Subject Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
          {subjects.map((sub) => (
            <button
              key={sub}
              onClick={() => setSelectedSubject(sub)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                selectedSubject === sub
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              {sub}
            </button>
          ))}
        </div>
      </div>

      {/* Projects List / Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading projects...</div>
      ) : projects.length === 0 ? (
        /* Zero Projects Empty State */
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 mx-auto flex items-center justify-center mb-3">
            <FolderPlus className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">No projects in this workspace</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Create your first academic project to start organizing course textbooks, slides, and study notes.
          </p>
          <div className="mt-5">
            <Button onClick={() => setShowCreateModal(true)} size="sm">
              Create First Project
            </Button>
          </div>
        </div>
      ) : filteredProjects.length === 0 ? (
        /* Zero Search Results */
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500">
          No projects matched your search criteria "{searchQuery}".
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((p) => (
            <div
              key={p.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:shadow-md hover:border-indigo-300 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                    <Folder className="w-5 h-5" />
                  </div>
                  {p.subject && <Badge variant="indigo">{p.subject}</Badge>}
                </div>

                <Link to={`/projects/${p.id}`} className="block group">
                  <h3 className="text-sm font-bold text-slate-900 mt-3 group-hover:text-indigo-600 transition-colors">
                    {p.name}
                  </h3>
                </Link>

                {p.description && (
                  <p className="text-xs text-slate-500 mt-1.5 line-clamp-2 leading-relaxed">
                    {p.description}
                  </p>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(p.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => openEditModal(p)}
                    className="text-slate-400 hover:text-slate-700 p-1 rounded-md transition-colors"
                    title="Edit project details"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setDeletingProject(p)}
                    className="text-slate-400 hover:text-red-600 p-1 rounded-md transition-colors"
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={(id) => navigate(`/projects/${id}`)}
      />

      {/* Edit Project Modal */}
      <Modal
        isOpen={!!editingProject}
        onClose={() => setEditingProject(null)}
        title="Edit Project"
        description="Update project name, subject, or description."
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
              placeholder="e.g. Computer Science, Neuroscience"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description
            </label>
            <textarea
              rows={3}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              placeholder="Brief course summary or goals..."
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 resize-none"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button type="button" variant="outline" size="sm" onClick={() => setEditingProject(null)}>
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
        isOpen={!!deletingProject}
        onClose={() => setDeletingProject(null)}
        title="Confirm Project Deletion"
        description="Are you sure you want to delete this project? All associated course materials, chat history, and study guides will be permanently removed."
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            <span className="font-bold">Warning:</span> Project "{deletingProject?.name}" and all private document chunks will be deleted immediately.
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button type="button" variant="outline" size="sm" onClick={() => setDeletingProject(null)}>
              Cancel
            </Button>
            <Button type="button" variant="danger" size="sm" isLoading={isDeleting} onClick={confirmDelete}>
              Delete Project Permanently
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
