import { useEffect, useRef, useState, useCallback } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import { useAuth } from "../auth/AuthContext";
import { deleteDocument, listDocuments, retryDocument, uploadDocument } from "../../lib/api-client";
import type { Project, ProjectDocument } from "../../types";

interface SourcesTabProps {
  project: Project;
}

const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".pptx", ".txt", ".md"];
const MAX_BYTES = 50 * 1024 * 1024; // 50 MB

export function SourcesTab({ project }: SourcesTabProps) {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [retryingDocId, setRetryingDocId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch documents from backend
  const fetchDocs = useCallback(async () => {
    if (!token) return;
    try {
      const docs = await listDocuments(token, project.id);
      setDocuments(docs);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load project documents.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [token, project.id]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Polling when any document is processing/queued/extracting/chunking
  useEffect(() => {
    const hasActiveJobs = documents.some((d) =>
      ["queued", "uploaded", "extracting", "chunking", "processing"].includes(d.ingestion_status)
    );

    if (!hasActiveJobs || !token) return;

    const interval = setInterval(() => {
      fetchDocs();
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, token, fetchDocs]);

  const formatBytes = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: ProjectDocument["ingestion_status"]) => {
    switch (status) {
      case "indexed":
        return (
          <Badge variant="emerald" className="flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Indexed & Searchable
          </Badge>
        );
      case "extracting":
      case "chunking":
      case "processing":
        return (
          <Badge variant="indigo" className="flex items-center gap-1 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" /> Ingesting ({status})
          </Badge>
        );
      case "queued":
      case "uploaded":
        return (
          <Badge variant="slate" className="flex items-center gap-1">
            <Clock className="w-3 h-3" /> Queued for Worker
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="red" className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Ingestion Failed
          </Badge>
        );
      default:
        return <Badge variant="slate">{status}</Badge>;
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    setUploadSuccess(null);
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      setUploadError(`Unsupported format '${ext}'. Allowed: ${SUPPORTED_EXTENSIONS.join(", ")}`);
      return;
    }

    if (file.size > MAX_BYTES) {
      setUploadError("File size exceeds 50 MB limit.");
      return;
    }

    setSelectedFile(file);
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile || !token) return;
    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await uploadDocument(token, project.id, selectedFile);
      setUploadSuccess(res.message || `Uploaded "${selectedFile.name}" successfully! Ingestion queued.`);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      await fetchDocs();
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(null);
      }, 1200);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed. Please try again.";
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!token) return;
    const confirmDelete = window.confirm("Are you sure you want to remove this document from the project?");
    if (!confirmDelete) return;

    try {
      await deleteDocument(token, project.id, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete document.");
    }
  };

  const handleRetry = async (docId: string) => {
    if (!token) return;
    setRetryingDocId(docId);
    try {
      const updated = await retryDocument(token, project.id, docId);
      setDocuments((prev) => prev.map((d) => (d.id === docId ? updated : d)));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to retry document.");
    } finally {
      setRetryingDocId(null);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Sources Overview Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">
            Course Sources & Documents ({documents.length})
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Materials in this project are parsed, chunked, and indexed with pgvector for grounded retrieval.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => fetchDocs()}
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            onClick={() => {
              setUploadError(null);
              setUploadSuccess(null);
              setSelectedFile(null);
              setShowUploadModal(true);
            }}
            size="sm"
            leftIcon={<Upload className="w-3.5 h-3.5" />}
          >
            Add Course Documents
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={fetchDocs}>
            Retry
          </Button>
        </div>
      )}

      {/* Documents List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Project Documents
          </span>
          <span className="text-[11px] text-slate-400">
            Target capacity: Up to 500 pages per document
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400 space-y-2">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-indigo-600" />
            <p className="text-xs">Loading project documents from database...</p>
          </div>
        ) : documents.length === 0 ? (
          /* Empty State */
          <div className="p-12 text-center max-w-md mx-auto space-y-3">
            <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">No documents added to this project yet</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Upload textbook PDFs, lecture slide decks (.pptx), Word summaries (.docx), or Markdown (.md) to ground
              your course workspace.
            </p>
            <div className="pt-2">
              <Button size="sm" onClick={() => setShowUploadModal(true)}>
                Upload Course Materials
              </Button>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between hover:bg-slate-50/50 transition-colors gap-3"
              >
                <div className="flex items-start space-x-3 truncate">
                  <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 mt-0.5">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <h4 className="text-xs font-bold text-slate-900 truncate">
                      {doc.original_filename}
                    </h4>
                    <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-1">
                      <span>{formatBytes(doc.byte_size)}</span>
                      {doc.page_count !== undefined && doc.page_count !== null && (
                        <span>&bull; {doc.page_count} pages / slides</span>
                      )}
                      {doc.chunk_count !== undefined && doc.chunk_count !== null && (
                        <span>&bull; {doc.chunk_count} chunks</span>
                      )}
                      <span>&bull; {new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                    {doc.ingestion_status === "failed" && doc.ingestion_error_message && (
                      <p className="text-[11px] text-red-600 mt-1 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 shrink-0" />
                        {doc.ingestion_error_message}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-3 shrink-0 self-end sm:self-center">
                  {getStatusBadge(doc.ingestion_status)}

                  {doc.ingestion_status === "failed" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRetry(doc.id)}
                      disabled={retryingDocId === doc.id}
                      leftIcon={
                        retryingDocId === doc.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3 h-3" />
                        )
                      }
                    >
                      Retry
                    </Button>
                  )}

                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="text-slate-400 hover:text-red-600 p-1.5 rounded transition-colors"
                    title="Remove document from project"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Real Upload Modal */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => {
          if (!isUploading) {
            setShowUploadModal(false);
          }
        }}
        title="Upload Course Documents"
        description="Select an academic document to store, parse, chunk, and index for verifiable study."
      >
        <div className="space-y-4 text-xs font-sans">
          {uploadError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          {uploadSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>{uploadSuccess}</span>
            </div>
          )}

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 hover:border-indigo-400 rounded-xl p-8 text-center bg-slate-50/50 hover:bg-indigo-50/20 transition-all cursor-pointer space-y-2"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.pptx,.txt,.md"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
            <Upload className="w-8 h-8 text-slate-400 mx-auto" />
            <span className="font-semibold text-slate-700 block">
              {selectedFile ? selectedFile.name : "Click to select a course document"}
            </span>
            <span className="text-[11px] text-slate-400 block">
              {selectedFile
                ? `${formatBytes(selectedFile.size)} selected`
                : "Supported: PDF, DOCX, PPTX, TXT, MD (Max 50 MB, up to 500 pages)"}
            </span>
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowUploadModal(false)}
              disabled={isUploading}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleUploadSubmit}
              disabled={!selectedFile || isUploading}
              isLoading={isUploading}
              leftIcon={<Upload className="w-3.5 h-3.5" />}
            >
              {isUploading ? "Uploading..." : "Upload & Ingest"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
