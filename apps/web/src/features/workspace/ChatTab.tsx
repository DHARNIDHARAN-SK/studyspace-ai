import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Bot,
  Copy,
  ExternalLink,
  FileCheck2,
  HelpCircle,
  RefreshCw,
  Send,
  Sparkles,
  User,
  Zap,
} from "lucide-react";
import { ConversationSidebar } from "./ConversationSidebar";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import { useAuth } from "../auth/AuthContext";
import {
  createConversation,
  getConversationMessages,
  listConversations,
  previewQueryRewrite,
  sendChatMessage,
  type RewritePreviewResponse,
} from "../../lib/api-client";
import type { Citation, Conversation, Message, Project } from "../../types";

interface ChatTabProps {
  project: Project;
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function ChatTab({ project }: ChatTabProps) {
  const { token } = useAuth();

  // State for conversations list
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isCreatingConv, setIsCreatingConv] = useState(false);
  const composerInputRef = React.useRef<HTMLTextAreaElement>(null);

  const [inputQuery, setInputQuery] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [inspectingCitation, setInspectingCitation] = useState<Citation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Dynamic Effort System (Simple / Medium / Hard)
  const [effort, setEffort] = useState<"simple" | "medium" | "hard">("medium");
  const [rewriteEnabled, setRewriteEnabled] = useState<boolean>(true);
  const [showEffortHelpModal, setShowEffortHelpModal] = useState<boolean>(false);

  // Pre-flight rewrite preview state
  const [isPreviewingRewrite, setIsPreviewingRewrite] = useState(false);
  const [rewritePreview, setRewritePreview] = useState<RewritePreviewResponse | null>(null);

  const initialLoadDoneRef = React.useRef(false);

  // Fetch project conversations on mount
  const fetchConversations = useCallback(async (selectFirst = false) => {
    if (!token) return;
    try {
      const convList = await listConversations(token, project.id);
      setConversations(convList);
      if (selectFirst && convList.length > 0) {
        setActiveConvId(convList[0].id);
      }
    } catch (err) {
      console.warn("Could not load conversations:", err);
    }
  }, [token, project.id]);

  useEffect(() => {
    if (!initialLoadDoneRef.current) {
      initialLoadDoneRef.current = true;
      fetchConversations(true);
    } else {
      fetchConversations(false);
    }
  }, [fetchConversations]);

  // Fetch messages when active conversation changes
  useEffect(() => {
    if (!token || !activeConvId || !UUID_REGEX.test(activeConvId)) {
      setMessages([]);
      return;
    }

    let isMounted = true;
    const loadMessages = async () => {
      setIsLoadingHistory(true);
      try {
        const history = await getConversationMessages(token, project.id, activeConvId);
        if (isMounted) {
          setMessages(history);
        }
      } catch (err) {
        console.warn("Failed to load message history:", err);
      } finally {
        if (isMounted) {
          setIsLoadingHistory(false);
        }
      }
    };

    loadMessages();
    return () => {
      isMounted = false;
    };
  }, [token, project.id, activeConvId]);

  const executeSend = async (
    queryText: string,
    overrideSelectedQuery?: string,
    rewriteAccepted?: boolean
  ) => {
    if (!queryText.trim() || isSending || !token) return;

    setInputQuery("");
    setChatError(null);

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConvId || "pending",
      role: "user",
      content: queryText.trim(),
      selected_query: overrideSelectedQuery,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsSending(true);

    try {
      const validConvId = UUID_REGEX.test(activeConvId) ? activeConvId : undefined;
      const resp = await sendChatMessage(token, project.id, {
        query: queryText.trim(),
        conversation_id: validConvId,
        top_k: 5,
        effort: effort,
        rewrite_enabled: rewriteEnabled,
        selected_query: overrideSelectedQuery,
        rewrite_accepted: rewriteAccepted,
        multi_query_enabled: effort === "hard",
      });

      if (!validConvId && resp.conversation_id) {
        setActiveConvId(resp.conversation_id);
        await fetchConversations(false);
      }

      setMessages((prev) => [...prev, resp.message]);
      const currentConv = conversations.find((c) => c.id === resp.conversation_id);
      if (!currentConv || currentConv.title === "New Chat" || currentConv.title === "New Conversation") {
        await fetchConversations(false);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute academic query.";
      setChatError(msg);
    } finally {
      setIsSending(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isSending || !token) return;
    await executeSend(inputQuery.trim());
  };

  const handlePreviewRewrite = async () => {
    if (!inputQuery.trim() || !token || isPreviewingRewrite) return;
    setIsPreviewingRewrite(true);
    setChatError(null);
    try {
      const validConvId = UUID_REGEX.test(activeConvId) ? activeConvId : undefined;
      const preview = await previewQueryRewrite(token, project.id, {
        query: inputQuery.trim(),
        conversation_id: validConvId,
      });

      if (!preview.was_rewritten) {
        // Query is already specific/clear, execute directly
        await executeSend(inputQuery.trim());
      } else {
        setRewritePreview(preview);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to preview rewrite.";
      setChatError(msg);
    } finally {
      setIsPreviewingRewrite(false);
    }
  };

  const handleNewChat = async () => {
    if (!token || !project.id || isCreatingConv) return;
    setIsCreatingConv(true);
    setChatError(null);
    setRewritePreview(null);
    try {
      const newConv = await createConversation(token, project.id, "New Chat");
      setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setTimeout(() => {
        composerInputRef.current?.focus();
      }, 50);
    } catch (err: unknown) {
      console.error("Failed to create new conversation:", err);
      setChatError(err instanceof Error ? err.message : "Failed to create new chat.");
    } finally {
      setIsCreatingConv(false);
    }
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
    `What are the core concepts covered in ${project.name}?`,
    "Explain the primary architecture differences mentioned in the course documents.",
    "Give me an exam-style summary of key definitions with citations.",
  ];

  return (
    <div className="flex flex-col md:flex-row h-[750px] bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden font-sans">
      {/* Sidebar of Conversations */}
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConvId || null}
        onSelect={(id) => setActiveConvId(id)}
        onNewChat={handleNewChat}
        onRename={handleRename}
        onDelete={handleDelete}
        onTogglePin={handleTogglePin}
        isCreating={isCreatingConv}
      />

      {/* Main Chat Workspace */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Chat Control Toolbar */}
        <div className="p-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
            <span>Scope: <strong className="text-slate-700">Course Materials</strong></span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-500">
              {effort === "simple" && "Fast Vector Search"}
              {effort === "medium" && "Hybrid Dense + Lexical Search"}
              {effort === "hard" && "Conversational Multi-Query Expansion"}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            {/* Dynamic Effort Selector */}
            <div className="flex items-center space-x-1.5">
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Effort:
              </label>
              <select
                value={effort}
                onChange={(e) => setEffort(e.target.value as any)}
                className="text-xs font-semibold bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 shadow-2xs"
              >
                <option value="simple">Simple</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <button
                type="button"
                onClick={() => setShowEffortHelpModal(true)}
                className="text-slate-400 hover:text-indigo-600 transition-colors p-0.5"
                title="About Retrieval Effort Levels"
              >
                <HelpCircle className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Query Rewrite Toggle */}
            <div className="flex items-center space-x-1.5 border-l border-slate-200 pl-3">
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Rewrite:
              </label>
              <button
                type="button"
                onClick={() => setRewriteEnabled(!rewriteEnabled)}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition-colors ${
                  rewriteEnabled
                    ? "bg-indigo-50 border-indigo-200 text-indigo-700"
                    : "bg-slate-100 border-slate-200 text-slate-400"
                }`}
                title="Toggle conversational query rewriting"
              >
                {rewriteEnabled ? "ON" : "OFF"}
              </button>
            </div>

            <Badge variant="indigo" className="font-mono text-[10px]">
              phi4-mini
            </Badge>
          </div>
        </div>

        {/* Error notification banner */}
        {chatError && (
          <div className="px-4 py-2 bg-rose-50 border-b border-rose-200 text-rose-700 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{chatError}</span>
            </div>
            <button
              onClick={() => setChatError(null)}
              className="text-rose-500 hover:text-rose-800 text-[11px] font-semibold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Message History Area */}
        <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-5 max-h-[520px]">
          {isLoadingHistory ? (
            <div className="py-12 text-center text-slate-400 text-xs flex items-center justify-center space-x-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" />
              <span>Loading conversation history...</span>
            </div>
          ) : messages.length === 0 ? (
            /* Empty State */
            <div className="py-12 text-center max-w-md mx-auto space-y-4">
              <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">StudySpace AI Session</h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Ask questions about your uploaded documents or chat naturally.
                  Study queries use grounded citations, while casual questions are answered directly without retrieval.
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

                  {/* User Rewritten Query Info */}
                  {m.role === "user" && m.selected_query && m.selected_query !== m.content && (
                    <div className="mt-2 pt-2 border-t border-indigo-500/30 text-[11px] text-indigo-100 flex items-center space-x-1">
                      <Sparkles className="w-3 h-3 text-indigo-200 shrink-0" />
                      <span>Searched as: <em>"{m.selected_query}"</em></span>
                    </div>
                  )}

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
                      <div className="flex items-center space-x-2">
                        {m.cache_hit && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium space-x-1">
                            <Zap className="w-3 h-3 text-emerald-600" />
                            <span>Cache Hit</span>
                          </span>
                        )}
                        <span>{m.latency_ms ? `${m.latency_ms} ms` : "Response"}</span>
                        <span>•</span>
                        <span className="font-mono">{m.model || "phi4-mini:latest"}</span>
                      </div>
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
                <span>
                  {effort === "hard"
                    ? "Resolving context, executing multi-query retrieval & generating answer..."
                    : effort === "medium"
                    ? "Executing hybrid retrieval & generating grounded answer..."
                    : "Executing fast dense vector retrieval & generating grounded answer..."}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Composer Form */}
        <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-200 bg-slate-50/50">
          <div className="flex items-end gap-2 bg-white border border-slate-300 rounded-xl p-2 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-600">
            <textarea
              ref={composerInputRef}
              rows={2}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder={`Ask a question or study topic about ${project.name}... (Press Enter to send)`}
              className="flex-1 text-xs border-0 focus:outline-none resize-none p-1 text-slate-800 placeholder-slate-400"
            />
            {rewriteEnabled && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handlePreviewRewrite}
                disabled={!inputQuery.trim() || isSending || isPreviewingRewrite}
                title="Preview how this query will be reformulated using conversation history"
                leftIcon={
                  isPreviewingRewrite ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  )
                }
              >
                Preview Rewrite
              </Button>
            )}
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

      {/* Query Rewrite Preview Modal */}
      <Modal
        isOpen={!!rewritePreview}
        onClose={() => setRewritePreview(null)}
        title="Query Formulation Preview"
        description="Inspect or choose how your question will be formulated for textbook retrieval."
      >
        {rewritePreview && (
          <div className="space-y-4 text-xs font-sans">
            <div className="space-y-1">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                Original Query
              </span>
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono">
                {rewritePreview.original_query}
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wide flex items-center space-x-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Suggested Search Query</span>
                </span>
                <span className="text-[10px] text-slate-400">
                  {rewritePreview.latency_ms} ms
                </span>
              </div>
              <div className="p-2.5 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-950 font-medium">
                {rewritePreview.rewritten_query}
              </div>
              {rewritePreview.reason && (
                <p className="text-[11px] text-slate-500 italic mt-1">
                  Reasoning: {rewritePreview.reason}
                </p>
              )}
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const original = rewritePreview.original_query;
                  setRewritePreview(null);
                  executeSend(original, original, false);
                }}
              >
                Keep Original Query
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={() => {
                  const original = rewritePreview.original_query;
                  const rewritten = rewritePreview.rewritten_query;
                  setRewritePreview(null);
                  executeSend(original, rewritten, true);
                }}
              >
                Use Rewritten Query
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* About Effort Help Modal */}
      <Modal
        isOpen={showEffortHelpModal}
        onClose={() => setShowEffortHelpModal(false)}
        title="About Retrieval Effort Levels"
      >
        <div className="space-y-4 text-xs font-sans text-slate-600 leading-relaxed">
          <p>
            StudySpace AI allows you to adjust the retrieval effort for every message. Conversation history is preserved across all effort levels:
          </p>

          <div className="space-y-3">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="font-bold text-slate-900 flex items-center space-x-1.5">
                <Badge variant="slate">Simple</Badge>
                <span>Fast Retrieval</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Fast retrieval for straightforward questions. Uses pgvector HNSW dense vector search directly against course document chunks.
              </p>
            </div>

            <div className="p-3 bg-indigo-50/50 border border-indigo-100 rounded-lg">
              <div className="font-bold text-slate-900 flex items-center space-x-1.5">
                <Badge variant="indigo">Medium</Badge>
                <span>Deeper Hybrid Retrieval</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Deeper retrieval for technical or detailed questions. Combines dense vector search with PostgreSQL lexical full-text search, Reciprocal Rank Fusion (RRF), and deterministic local passage reranking.
              </p>
            </div>

            <div className="p-3 bg-indigo-50/50 border border-indigo-100 rounded-lg">
              <div className="font-bold text-slate-900 flex items-center space-x-1.5">
                <Badge variant="indigo">Hard</Badge>
                <span>Maximum Multi-Query Retrieval</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Maximum retrieval effort for complex, ambiguous, or multi-part questions. Decomposes questions, generates multiple retrieval angles in parallel, performs provenance merging, reranking, and Redis semantic caching.
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Button size="sm" onClick={() => setShowEffortHelpModal(false)}>
              Got It
            </Button>
          </div>
        </div>
      </Modal>

      {/* Citation Inspector Modal */}
      <Modal
        isOpen={!!inspectingCitation}
        onClose={() => setInspectingCitation(null)}
        title="Source Citation Verification"
        description={inspectingCitation?.document_title || "Document Citation"}
      >
        {inspectingCitation && (
          <div className="space-y-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="indigo">
                Page {inspectingCitation.page_start} - {inspectingCitation.page_end || inspectingCitation.page_start}
              </Badge>
              {inspectingCitation.retrieval_method && (
                <Badge variant="slate" className="capitalize">
                  {inspectingCitation.retrieval_method}
                </Badge>
              )}
              {inspectingCitation.section_path && (
                <span className="text-[11px] text-slate-500">{inspectingCitation.section_path}</span>
              )}
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 italic leading-relaxed">
              "{inspectingCitation.snippet}"
            </div>

            {/* Retrieval Provenance Breakdown */}
            {(inspectingCitation.dense_rank || inspectingCitation.lexical_rank || inspectingCitation.rrf_score) && (
              <div className="p-2.5 bg-indigo-50/50 border border-indigo-100 rounded-lg grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                {inspectingCitation.dense_rank !== undefined && (
                  <div>
                    <span className="text-slate-500 block">Dense Rank</span>
                    <strong className="text-indigo-900 font-mono">#{inspectingCitation.dense_rank}</strong>
                  </div>
                )}
                {inspectingCitation.lexical_rank !== undefined && (
                  <div>
                    <span className="text-slate-500 block">Lexical Rank</span>
                    <strong className="text-indigo-900 font-mono">#{inspectingCitation.lexical_rank}</strong>
                  </div>
                )}
                {inspectingCitation.rrf_score !== undefined && (
                  <div>
                    <span className="text-slate-500 block">RRF Score</span>
                    <strong className="text-indigo-900 font-mono">{inspectingCitation.rrf_score.toFixed(4)}</strong>
                  </div>
                )}
                {inspectingCitation.rerank_score !== undefined && (
                  <div>
                    <span className="text-slate-500 block">Rerank Score</span>
                    <strong className="text-indigo-900 font-mono">{inspectingCitation.rerank_score.toFixed(4)}</strong>
                  </div>
                )}
              </div>
            )}

            <p className="text-[11px] text-slate-400">
              This passage was verified from the project's ingested course material via multi-path hybrid retrieval.
              The response was generated strictly from grounded evidence.
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
