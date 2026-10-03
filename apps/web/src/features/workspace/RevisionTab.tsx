import React, { useMemo, useState } from "react";
import { CheckSquare, Plus, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import type { Project, RevisionItem, RevisionStatus } from "../../types";

interface RevisionTabProps {
  project: Project;
}

export function RevisionTab({ project }: RevisionTabProps) {
  const [items, setItems] = useState<RevisionItem[]>([
    {
      id: "rev-1",
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: "Asymptotic Notation and Recurrence Relations",
      description: "Master Big-O, Big-Theta bounds and Master Theorem cases for recursive algorithms.",
      status: "revised",
      created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "rev-2",
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: "Graph Traversal: BFS vs DFS Topological Ordering",
      description: "Review edge classification (tree, back, forward, cross) in directed graphs.",
      status: "learning",
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "rev-3",
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: "Dynamic Programming: Optimal Substructure & Overlapping Subproblems",
      description: "Knapsack variations, memoization vs bottom-up tabulation.",
      status: "not_started",
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
      updated_at: new Date().toISOString(),
    },
  ]);

  const [filter, setFilter] = useState<"all" | RevisionStatus>("all");
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const filteredItems = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((i) => i.status === filter);
  }, [items, filter]);

  const revisedCount = items.filter((i) => i.status === "revised").length;
  const progressPercent = items.length > 0 ? Math.round((revisedCount / items.length) * 100) : 0;

  const handleStatusChange = (id: string, newStatus: RevisionStatus) => {
    setItems(items.map((i) => (i.id === id ? { ...i, status: newStatus, updated_at: new Date().toISOString() } : i)));
  };

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const newItem: RevisionItem = {
      id: `rev-${Date.now()}`,
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: newTitle.trim(),
      description: newDesc.trim() || undefined,
      status: "not_started",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    setItems([...items, newItem]);
    setNewTitle("");
    setNewDesc("");
    setShowAddModal(false);
  };

  const handleDeleteItem = (id: string) => {
    setItems(items.filter((i) => i.id !== id));
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
              <span>{revisedCount} of {items.length} topics revised</span>
              <span className="font-semibold text-slate-700">{progressPercent}%</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

        <Button
          onClick={() => setShowAddModal(true)}
          size="sm"
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          Add Topic
        </Button>
      </div>

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
        {filteredItems.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No revision topics in this category.
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
            <Button type="submit" size="sm">
              Add Topic
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
