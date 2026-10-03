import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
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
import { useAuth } from "../auth/AuthContext";
import {
  getConversationMessages,
  listConversations,
  sendChatMessage,
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

  const [inputQuery, setInputQuery] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [inspectingCitation, setInspectingCitation] = useState<Citation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [retrievalMode, setRetrievalMode] = useState<"advanced" | "baseline">("advanced");

  // Fetch project conversations on mount
  const fetchConversations = useCallback(async () => {
    if (!token) return;
    try {
      const convList = await listConversations(token, project.id);
      setConversations(convList);
      if (convList.length > 0 && !activeConvId) {
        setActiveConvId(convList[0].id);
      }
    } catch (err) {
      console.warn("Could not load conversations:", err);
    }
  }, [token, project.id, activeConvId]);

  useEffect(() => {
    fetchConversations();
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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isSending || !token) return;

    const userText = inputQuery.trim();
    setInputQuery("");
    setChatError(null);

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConvId || "pending",
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsSending(true);

    try {
      const validConvId = UUID_REGEX.test(activeConvId) ? activeConvId : undefined;
      const resp = await sendChatMessage(token, project.id, {
        query: userText,
        conversation_id: validConvId,
        top_k: 5,
        mode: retrievalMode,
      });

      // Update active conversation ID if newly created
      if (!validConvId && resp.conversation_id) {
        setActiveConvId(resp.conversation_id);
        fetchConversations();
      }

      // Append assistant message
      setMessages((prev) => [...prev, resp.message]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute baseline RAG query.";
      setChatError(msg);
      // Remove temporary pending user message or keep it with error note
    } finally {
      setIsSending(false);
    }
  };

  const handleNewChat = () => {
    setActiveConvId("");
    setMessages([]);
    setChatError(null);
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
    "Summarize the key cloud service models and their differences",
    "Explain virtualization and hypervisors in cloud computing",
    "What are the main security risks and mitigation strategies in cloud storage?",
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden flex flex-col md:flex-row min-h-[580px]">
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
            <span>Scope: <strong className="text-slate-700">Project Course Materials</strong></span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-400">
              Index: {retrievalMode === "advanced" ? "pgvector HNSW + FTS (RRF + Rerank)" : "pgvector HNSW (768d)"}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setRetrievalMode((prev) => (prev === "advanced" ? "baseline" : "advanced"))}
              className={`px-2 py-0.5 rounded text-[11px] font-medium border transition-colors flex items-center space-x-1 ${
                retrievalMode === "advanced"
                  ? "bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100"
                  : "bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200"
              }`}
              title="Click to toggle between Advanced Hybrid RAG and Baseline Vector RAG"
            >
              <Sparkles className="w-3 h-3 text-indigo-500" />
              <span>{retrievalMode === "advanced" ? "Mode: Advanced Hybrid (RRF)" : "Mode: Baseline Vector"}</span>
            </button>
            <Badge variant="indigo" className="font-mono text-[10px]">
              phi4-mini:latest
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
                <h3 className="text-sm font-bold text-slate-900">Baseline RAG Study Session</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Ask questions about your uploaded course materials. Every response is strictly
                  grounded using local vector retrieval with real page citations.
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
                      <div className="flex items-center space-x-2">
                        <span>{m.latency_ms ? `${m.latency_ms} ms` : "Grounded response"}</span>
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
                <span>Executing vector retrieval & generating grounded answer with phi4-mini...</span>
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
