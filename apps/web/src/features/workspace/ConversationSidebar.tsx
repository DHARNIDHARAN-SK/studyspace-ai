import React, { useState } from "react";
import {
  Edit2,
  MessageSquare,
  Pin,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import type { Conversation } from "../../types";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onRename: (id: string, newTitle: string) => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string) => void;
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  onTogglePin,
}: ConversationSidebarProps) {
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  const pinned = filtered.filter((c) => c.is_pinned);
  const recent = filtered.filter((c) => !c.is_pinned);

  const startRename = (e: React.MouseEvent, c: Conversation) => {
    e.stopPropagation();
    setEditingId(c.id);
    setEditTitle(c.title);
  };

  const submitRename = (e: React.FormEvent, id: string) => {
    e.preventDefault();
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }
    setEditingId(null);
  };

  return (
    <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-slate-200 bg-slate-50/50 flex flex-col font-sans shrink-0">
      {/* Top action: New Chat */}
      <div className="p-3 border-b border-slate-200">
        <Button
          onClick={onNewChat}
          size="sm"
          className="w-full"
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          New Chat
        </Button>
      </div>

      {/* Search Bar */}
      <div className="p-3 border-b border-slate-200">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-8 pr-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-3 max-h-[300px] md:max-h-[500px]">
        {/* Pinned section */}
        {pinned.length > 0 && (
          <div>
            <div className="px-2 mb-1 flex items-center space-x-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <Pin className="w-3 h-3 text-indigo-500" />
              <span>Pinned</span>
            </div>
            <div className="space-y-0.5">
              {pinned.map((c) => renderItem(c))}
            </div>
          </div>
        )}

        {/* Recent section */}
        <div>
          <div className="px-2 mb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Recent
          </div>
          {recent.length === 0 && pinned.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-slate-400 italic">
              No conversations yet
            </div>
          ) : (
            <div className="space-y-0.5">
              {recent.map((c) => renderItem(c))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );

  function renderItem(c: Conversation) {
    const isActive = activeId === c.id;
    const isEditing = editingId === c.id;

    if (isEditing) {
      return (
        <form
          key={c.id}
          onSubmit={(e) => submitRename(e, c.id)}
          className="p-1"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="text"
            autoFocus
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={() => setEditingId(null)}
            className="w-full px-2 py-1 text-xs border border-indigo-500 rounded bg-white"
          />
        </form>
      );
    }

    return (
      <div
        key={c.id}
        onClick={() => onSelect(c.id)}
        className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors ${
          isActive
            ? "bg-white text-indigo-700 font-semibold shadow-xs border border-slate-200"
            : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
        }`}
      >
        <div className="flex items-center space-x-2 truncate flex-1 min-w-0">
          <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-indigo-600" : "text-slate-400"}`} />
          <span className="truncate">{c.title}</span>
        </div>

        {/* Hover action menu */}
        <div className="hidden group-hover:flex items-center space-x-1 shrink-0 ml-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onTogglePin(c.id);
            }}
            title={c.is_pinned ? "Unpin chat" : "Pin chat"}
            className="text-slate-400 hover:text-indigo-600 p-0.5 rounded"
          >
            <Pin className={`w-3 h-3 ${c.is_pinned ? "fill-indigo-600 text-indigo-600" : ""}`} />
          </button>
          <button
            onClick={(e) => startRename(e, c)}
            title="Rename chat"
            className="text-slate-400 hover:text-slate-600 p-0.5 rounded"
          >
            <Edit2 className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(c.id);
            }}
            title="Delete chat"
            className="text-slate-400 hover:text-red-600 p-0.5 rounded"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
    );
  }
}
