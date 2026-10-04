import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import { createProject, deleteProject, listProjects, updateProject } from "../../lib/api-client";
import type { Project, ProjectCreateInput, ProjectUpdateInput } from "../../types";

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  loading: boolean;
  refreshProjects: () => Promise<void>;
  selectProject: (projectOrId: string | Project | null) => void;
  createNewProject: (input: ProjectCreateInput) => Promise<Project>;
  updateExistingProject: (projectId: string, input: ProjectUpdateInput) => Promise<Project>;
  deleteExistingProject: (projectId: string) => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const refreshProjects = useCallback(async () => {
    if (!token) {
      setProjects([]);
      setActiveProject(null);
      return;
    }
    setLoading(true);
    try {
      const list = await listProjects(token);
      setProjects(list);
      // Keep active project in sync if it still exists
      if (activeProject) {
        const found = list.find((p) => p.id === activeProject.id);
        setActiveProject(found || null);
      }
    } catch (err) {
      console.error("Failed to load projects:", err);
    } finally {
      setLoading(false);
    }
  }, [token, activeProject]);

  useEffect(() => {
    if (token) {
      refreshProjects();
    } else {
      setProjects([]);
      setActiveProject(null);
    }
  }, [token, user?.id]);

  const selectProject = (projectOrId: string | Project | null) => {
    if (!projectOrId) {
      setActiveProject(null);
      return;
    }
    if (typeof projectOrId === "object") {
      setActiveProject(projectOrId);
      return;
    }
    const found = projects.find((p) => p.id === projectOrId);
    if (found) {
      setActiveProject(found);
    }
  };

  const createNewProject = async (input: ProjectCreateInput): Promise<Project> => {
    if (!token) throw new Error("Must be signed in to create a project.");
    const created = await createProject(token, input);
    setProjects((prev) => [created, ...prev]);
    setActiveProject(created);
    return created;
  };

  const updateExistingProject = async (
    projectId: string,
    input: ProjectUpdateInput
  ): Promise<Project> => {
    if (!token) throw new Error("Must be signed in to update a project.");
    const updated = await updateProject(token, projectId, input);
    setProjects((prev) => prev.map((p) => (p.id === projectId ? updated : p)));
    if (activeProject?.id === projectId) {
      setActiveProject(updated);
    }
    return updated;
  };

  const deleteExistingProject = async (projectId: string): Promise<void> => {
    if (!token) throw new Error("Must be signed in to delete a project.");
    await deleteProject(token, projectId);
    setProjects((prev) => prev.filter((p) => p.id !== projectId));
    if (activeProject?.id === projectId) {
      setActiveProject(null);
    }
  };

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        loading,
        refreshProjects,
        selectProject,
        createNewProject,
        updateExistingProject,
        deleteExistingProject,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjects() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProjects must be used within a ProjectProvider");
  }
  return context;
}
