import React, { useCallback, useEffect, useMemo, useState } from "react";
import { CheckSquare, Loader2, Plus, RefreshCw, Sparkles, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useAuth } from "../auth/AuthContext";
import {
  createRevisionItem,
  deleteRevisionItem,
  generateRevisionTopics,
  listRevisionItems,
  updateRevisionItem,
  type RevisionProgressStats,
} from "../../lib/api-client";
import type { Project, RevisionItem, RevisionStatus } from "../../types";

interface RevisionTabProps {
  project: Project;
}

export function RevisionTab({ project }: RevisionTabProps) {
  const { token } = useAuth();
  const [items, setItems] = useState<RevisionItem[]>([]);
  const [stats, setStats] = useState<RevisionProgressStats>({
    total_items: 0,
    not_started: 0,
    learning: 0,
    revised: 0,
    completion_percentage: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState<"all" | RevisionStatus>("all");
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleGenerateTopics = async () => {
    if (!token || !project.id || isGenerating) return;
    try {
      setIsGenerating(true);
      setError(null);
      const res = await generateRevisionTopics(token, project.id);
      setItems(res.items);
      setStats(res.stats);
    } catch (err: any) {
      setError(err?.message || "Failed to generate revision topics from course materials.");
    } finally {
      setIsGenerating(false);
    }
  };

  const fetchItems = useCallback(async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      setError(null);
      const res = await listRevisionItems(token, project.id, filter);
      setItems(res.items);
      setStats(res.stats);
    } catch (err: any) {
      setError(err?.message || "Failed to load revision topics");
    } finally {
      setIsLoading(false);
    }
  }, [token, project.id, filter]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const filteredItems = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((i) => i.status === filter);
  }, [items, filter]);

  const handleStatusChange = async (id: string, newStatus: RevisionStatus) => {
    if (!token) return;
    // Optimistic update
    setItems((prev) =>
      prev.map((i) => (i.id === id ? { ...i, status: newStatus, updated_at: new Date().toISOString() } : i))
    );
    try {
      await updateRevisionItem(token, project.id, id, { status: newStatus });
      fetchItems();
    } catch (err: any) {
      setError(err?.message || "Failed to update topic status");
      fetchItems();
    }
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !token) return;
    try {
      setIsSubmitting(true);
      await createRevisionItem(token, project.id, {
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        status: "not_started",
      });
      setNewTitle("");
      setNewDesc("");
      setShowAddModal(false);
      await fetchItems();
    } catch (err: any) {
      setError(err?.message || "Failed to create revision topic");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteItem = async (id: string) => {
    if (!token) return;
    try {
      setItems((prev) => prev.filter((i) => i.id !== id));
      await deleteRevisionItem(token, project.id, id);
      fetchItems();
    } catch (err: any) {
      setError(err?.message || "Failed to delete revision topic");
      fetchItems();
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header and Progress Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <CheckSquare className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Syllabus Revision Checklist
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Track syllabus concepts and exam readiness with linked course evidence.
          </p>

          {/* Progress bar */}
          <div className="mt-3 max-w-sm">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span>{stats.revised} of {stats.total_items} topics revised</span>
              <span className="font-semibold text-slate-700">{stats.completion_percentage.toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                style={{ width: `${stats.completion_percentage}%` }}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            onClick={handleGenerateTopics}
            disabled={isGenerating}
            variant="outline"
            size="sm"
            leftIcon={
              isGenerating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              )
            }
          >
            {isGenerating ? "Analyzing Course..." : "Generate Topics"}
          </Button>
          <Button
            onClick={() => fetchItems()}
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />}
          >
            Refresh
          </Button>
          <Button
            onClick={() => setShowAddModal(true)}
            size="sm"
            leftIcon={<Plus className="w-3.5 h-3.5" />}
          >
            Add Topic
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 text-xs bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-2 overflow-x-auto text-xs">
        {(
          [
            { id: "all", label: "All Topics" },
            { id: "not_started", label: "Not Started" },
            { id: "learning", label: "In Progress" },
            { id: "revised", label: "Revised" },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              filter === tab.id
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Items List */}
      <div className="space-y-3">
        {isLoading && items.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
            <span>Loading revision topics...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500 space-y-3">
            <p>No revision topics found for this filter.</p>
            {items.length === 0 && (
              <div className="flex justify-center pt-2">
                <Button
                  onClick={handleGenerateTopics}
                  disabled={isGenerating}
                  size="sm"
                  leftIcon={
                    isGenerating ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-white" />
                    )
                  }
                >
                  {isGenerating ? "Analyzing Course Materials..." : "Auto-Generate from Course Materials"}
                </Button>
              </div>
            )}
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  checked={item.status === "revised"}
                  onChange={(e) =>
                    handleStatusChange(item.id, e.target.checked ? "revised" : "learning")
                  }
                  className="w-4 h-4 rounded text-indigo-600 mt-1 cursor-pointer"
                />
                <div>
                  <h3
                    className={`text-xs font-bold ${
                      item.status === "revised"
                        ? "line-through text-slate-400"
                        : "text-slate-900"
                    }`}
                  >
                    {item.title}
                  </h3>
                  {item.description && (
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                      {item.description}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-3 self-end sm:self-center shrink-0">
                <select
                  value={item.status}
                  onChange={(e) => handleStatusChange(item.id, e.target.value as RevisionStatus)}
                  className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="not_started">Not Started</option>
                  <option value="learning">In Progress</option>
                  <option value="revised">Revised</option>
                </select>

                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="text-slate-400 hover:text-red-600 p-1 rounded transition-colors"
                  title="Delete topic"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add Topic Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add Revision Topic"
        description="Add a course subject concept or formula to track exam readiness."
      >
        <form onSubmit={handleAddItem} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Topic Name *
            </label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Master Theorem or Dijkstra's Algorithm"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description / Learning Goal
            </label>
            <textarea
              rows={3}
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="Key proofs or definitions to remember..."
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 resize-none"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button type="button" variant="outline" size="sm" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting}>
              {isSubmitting ? "Adding..." : "Add Topic"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
