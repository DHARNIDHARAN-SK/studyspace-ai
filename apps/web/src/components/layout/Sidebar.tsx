import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpen,
  ChevronDown,
  Folder,
  Home,
  LogOut,
  Plus,
  User,
  X,
} from "lucide-react";
import { useAuth } from "../../features/auth/AuthContext";
import { useProjects } from "../../features/projects/ProjectContext";
import { CreateProjectModal } from "../../features/projects/CreateProjectModal";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, profile, signOut } = useAuth();
  const { projects, activeProject, selectProject } = useProjects();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

  const navItems = [
    { label: "Dashboard", icon: Home, path: "/dashboard" },
    { label: "Projects", icon: Folder, path: "/projects" },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Workspace Brand Header */}
        <div className="h-16 px-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="bg-indigo-600 text-white p-1.5 rounded-lg flex items-center justify-center shadow-sm">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-sm text-slate-900 tracking-tight block">StudySpace AI</span>
              <span className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider">
                {profile?.workspace_name || "Workspace"}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="md:hidden text-slate-400 hover:text-slate-600 p-1 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Project Switcher Bar */}
        <div className="p-3 border-b border-slate-100">
          <div className="relative">
            <button
              onClick={() => setShowProjectDropdown(!showProjectDropdown)}
              className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 transition-colors"
            >
              <div className="flex items-center space-x-2 truncate">
                <Folder className="w-4 h-4 text-indigo-600 shrink-0" />
                <span className="truncate">
                  {activeProject ? activeProject.name : "Select Project..."}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1 shrink-0" />
            </button>

            {/* Dropdown Menu */}
            {showProjectDropdown && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-20 py-1 max-h-56 overflow-y-auto">
                <button
                  onClick={() => {
                    selectProject(null);
                    setShowProjectDropdown(false);
                    navigate("/dashboard");
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 flex items-center space-x-2"
                >
                  <Home className="w-3.5 h-3.5 text-slate-400" />
                  <span>All Projects (Dashboard)</span>
                </button>
                <div className="h-px bg-slate-100 my-1" />
                {projects.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      selectProject(p.id);
                      setShowProjectDropdown(false);
                      navigate(`/projects/${p.id}`);
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs truncate flex items-center space-x-2 ${
                      activeProject?.id === p.id
                        ? "bg-indigo-50 text-indigo-700 font-semibold"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <Folder className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                    <span className="truncate">{p.name}</span>
                  </button>
                ))}
                <div className="h-px bg-slate-100 my-1" />
                <button
                  onClick={() => {
                    setShowProjectDropdown(false);
                    setShowCreateModal(true);
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-indigo-600 hover:bg-indigo-50 font-medium flex items-center space-x-2"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Project</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-600" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}

          {/* Active Projects List Section */}
          <div className="pt-5">
            <div className="flex items-center justify-between px-3 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Your Projects
              </span>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-slate-400 hover:text-indigo-600 p-0.5 rounded transition-colors"
                title="Create Project"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-0.5">
              {projects.length === 0 ? (
                <div className="px-3 py-2 text-[11px] text-slate-400 italic">
                  No projects created
                </div>
              ) : (
                projects.map((p) => {
                  const isCurrent = location.pathname === `/projects/${p.id}`;
                  return (
                    <Link
                      key={p.id}
                      to={`/projects/${p.id}`}
                      onClick={() => {
                        selectProject(p.id);
                        onClose();
                      }}
                      className={`flex items-center space-x-2.5 px-3 py-1.5 rounded-lg text-xs truncate transition-colors ${
                        isCurrent
                          ? "bg-slate-100 text-indigo-700 font-semibold"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                      }`}
                    >
                      <Folder className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{p.name}</span>
                    </Link>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Footer Profile & Logout */}
        <div className="p-3 border-t border-slate-200 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5 truncate">
              <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs shrink-0">
                {profile?.display_name ? profile.display_name.charAt(0).toUpperCase() : <User className="w-4 h-4" />}
              </div>
              <div className="truncate">
                <span className="text-xs font-semibold text-slate-800 block truncate">
                  {profile?.display_name || user?.displayName || "Student"}
                </span>
                <span className="text-[10px] text-slate-500 block truncate">
                  {user?.email || "student@studyspace.ai"}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-red-600 p-1.5 rounded-md hover:bg-red-50 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Project Creation Modal */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={(id) => navigate(`/projects/${id}`)}
      />
    </>
  );
}
