import React, { useState } from "react";
import {
  BookOpen,
  Bot,
  Copy,
  ExternalLink,
  FileCheck2,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from "lucide-react";
import { ConversationSidebar } from "./ConversationSidebar";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import type { Citation, Conversation, Message, Project } from "../../types";

interface ChatTabProps {
  project: Project;
}

export function ChatTab({ project }: ChatTabProps) {
  // State for conversations list
  const [conversations, setConversations] = useState<Conversation[]>([
    {
      id: "conv-1",
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: "Core Concepts & Fundamentals",
      is_pinned: true,
      status: "active",
      created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
      updated_at: new Date().toISOString(),
    },
  ]);

  const [activeConvId, setActiveConvId] = useState<string>("conv-1");

  // State for messages in the active conversation
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg-1",
      conversation_id: "conv-1",
      role: "user",
      content: "Can you summarize the primary principles covered in this project's materials?",
      created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    },
    {
      id: "msg-2",
      conversation_id: "conv-1",
      role: "assistant",
      content:
        "Based on your course materials, the fundamental principles consist of:\n\n1. **Grounded Retrieval**: Generating responses strictly derived from verified syllabus chunks rather than external memorization.\n2. **Multi-Tenant Isolation**: Ensuring private study workspaces are isolated at the database layer via Row-Level Security.\n3. **Verifiable Citations**: Tracing every statement to its exact source document, slide number, and page range.",
      citations: [
        {
          id: "cit-1",
          document_id: "doc-1",
          document_title: `${project.name} Syllabus & Reference.pdf`,
          page_start: 3,
          page_end: 4,
          section_path: "Section 1.2 — Architecture Foundations",
          snippet:
            "Coursework intelligence must strictly bind generated answers to verified uploaded context with immutable page-level provenance.",
        },
      ],
      created_at: new Date(Date.now() - 3600000 * 2 + 1000).toISOString(),
      latency_ms: 820,
    },
  ]);

  const [inputQuery, setInputQuery] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [queryRewriterEnabled, setQueryRewriterEnabled] = useState(true);
  const [inspectingCitation, setInspectingCitation] = useState<Citation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isSending) return;

    const userText = inputQuery.trim();
    setInputQuery("");

    const newMsg: Message = {
      id: `msg-${Date.now()}`,
      conversation_id: activeConvId,
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, newMsg]);
    setIsSending(true);

    // Simulated grounded response for Phase 4 UI verification
    // (Master Architecture: real RAG pipeline connects in Phase 6)
    setTimeout(() => {
      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        conversation_id: activeConvId,
        role: "assistant",
        content: `I have analyzed your query regarding "${userText}". In Phase 6, the hybrid retrieval engine (dense vector search + BM25 lexical search) will execute against your indexed documents and provide a grounded response with page-level citations.`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsSending(false);
    }, 700);
  };

  const handleNewChat = () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: "New Conversation",
      is_pinned: false,
      status: "active",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setConversations([newConv, ...conversations]);
    setActiveConvId(newConv.id);
    setMessages([]);
  };

  const handleRename = (id: string, newTitle: string) => {
    setConversations(
      conversations.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
    );
  };

  const handleDelete = (id: string) => {
    setConversations(conversations.filter((c) => c.id !== id));
    if (activeConvId === id) {
      const remaining = conversations.filter((c) => c.id !== id);
      if (remaining.length > 0) {
        setActiveConvId(remaining[0].id);
      } else {
        handleNewChat();
      }
    }
  };

  const handleTogglePin = (id: string) => {
    setConversations(
      conversations.map((c) => (c.id === id ? { ...c, is_pinned: !c.is_pinned } : c))
    );
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const starterPrompts = [
    "Summarize the key takeaways and formulas",
    "Explain the core principles in simple terms",
    "What are the main potential exam topics?",
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden flex flex-col md:flex-row min-h-[560px]">
      {/* Conversation Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={setActiveConvId}
        onNewChat={handleNewChat}
        onRename={handleRename}
        onDelete={handleDelete}
        onTogglePin={handleTogglePin}
      />

      {/* Main Chat Canvas */}
      <div className="flex-1 flex flex-col justify-between bg-white font-sans">
        {/* Chat Control Subheader */}
        <div className="px-4 py-2.5 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between text-xs gap-2">
          <div className="flex items-center space-x-2 text-slate-500">
            <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
            <span>Scope: <strong className="text-slate-700">All Project Documents</strong></span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setQueryRewriterEnabled(!queryRewriterEnabled)}
              className={`flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold transition-colors ${
                queryRewriterEnabled
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                  : "bg-slate-100 text-slate-500 border border-slate-200"
              }`}
              title="Query rewriter contextualizes follow-up questions"
            >
              <Sparkles className="w-3 h-3" />
              <span>Query Rewriting: {queryRewriterEnabled ? "ON" : "OFF"}</span>
            </button>
          </div>
        </div>

        {/* Message History Area */}
        <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-5 max-h-[500px]">
          {messages.length === 0 ? (
            /* Empty State */
            <div className="py-12 text-center max-w-md mx-auto space-y-4">
              <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Start a grounded study session</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Ask questions about your uploaded textbooks, slide decks, and lecture notes.
                  Every answer will include verifiable page citations.
                </p>
              </div>

              {/* Starter Prompt Buttons */}
              <div className="space-y-1.5 pt-2">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setInputQuery(prompt)}
                    className="w-full text-left p-2.5 text-xs text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50/50 border border-slate-200/80 rounded-lg transition-colors flex items-center justify-between"
                  >
                    <span>{prompt}</span>
                    <Sparkles className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 text-xs leading-relaxed ${
                  m.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {/* Assistant Avatar */}
                {m.role === "assistant" && (
                  <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                {/* Message Content Bubble */}
                <div
                  className={`max-w-[85%] rounded-xl p-4 shadow-2xs ${
                    m.role === "user"
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-50/80 border border-slate-200/90 text-slate-800"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>

                  {/* Citations Box (Assistant only) */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-1.5">
                      <div className="flex items-center space-x-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        <FileCheck2 className="w-3 h-3 text-indigo-600" />
                        <span>Verified Source Citations</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {m.citations.map((c) => (
                          <button
                            key={c.id}
                            onClick={() => setInspectingCitation(c)}
                            className="inline-flex items-center space-x-1 px-2 py-1 bg-white hover:bg-indigo-50 border border-slate-200 rounded-md text-[11px] text-slate-700 transition-colors"
                          >
                            <span className="font-semibold text-indigo-600">
                              [Page {c.page_start || 1}]
                            </span>
                            <span className="truncate max-w-[150px]">{c.document_title}</span>
                            <ExternalLink className="w-3 h-3 text-slate-400" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Action row (Assistant only) */}
                  {m.role === "assistant" && (
                    <div className="mt-2.5 pt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span>{m.latency_ms ? `${m.latency_ms} ms` : "Grounded response"}</span>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleCopy(m.id, m.content)}
                          className="hover:text-slate-600 flex items-center space-x-1"
                        >
                          <Copy className="w-3 h-3" />
                          <span>{copiedId === m.id ? "Copied" : "Copy"}</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* User Avatar */}
                {m.role === "user" && (
                  <div className="w-7 h-7 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {isSending && (
            <div className="flex gap-3 text-xs justify-start items-center">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                <Bot className="w-4 h-4 animate-pulse" />
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-slate-500 flex items-center space-x-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                <span>Retrieving grounded course passages...</span>
              </div>
            </div>
          )}
        </div>

        {/* Composer Form */}
        <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-200 bg-slate-50/50">
          <div className="flex items-end gap-2 bg-white border border-slate-300 rounded-xl p-2 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-600">
            <textarea
              rows={2}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder={`Ask a question about ${project.name}... (Press Enter to send)`}
              className="flex-1 text-xs border-0 focus:outline-none resize-none p-1 text-slate-800 placeholder-slate-400"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!inputQuery.trim() || isSending}
              leftIcon={<Send className="w-3.5 h-3.5" />}
            >
              Send
            </Button>
          </div>
        </form>
      </div>

      {/* Citation Inspector Modal */}
      <Modal
        isOpen={!!inspectingCitation}
        onClose={() => setInspectingCitation(null)}
        title="Source Citation Verification"
        description={inspectingCitation?.document_title || "Document Citation"}
      >
        {inspectingCitation && (
          <div className="space-y-3 text-xs">
            <div className="flex items-center space-x-2">
              <Badge variant="indigo">
                Page {inspectingCitation.page_start} - {inspectingCitation.page_end || inspectingCitation.page_start}
              </Badge>
              {inspectingCitation.section_path && (
                <span className="text-[11px] text-slate-500">{inspectingCitation.section_path}</span>
              )}
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 italic leading-relaxed">
              "{inspectingCitation.snippet}"
            </div>

            <p className="text-[11px] text-slate-400">
              This passage was retrieved directly from the verified course source file.
              The model is constrained to construct claims exclusively from stored evidence.
            </p>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <Button type="button" size="sm" onClick={() => setInspectingCitation(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
