import { useState } from "react";
import {
  FileText,
  Info,
  Trash2,
  Upload,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import type { Project, ProjectDocument } from "../../types";

interface SourcesTabProps {
  project: Project;
}

export function SourcesTab({ project }: SourcesTabProps) {
  // Mock active documents in the project
  const [documents, setDocuments] = useState<ProjectDocument[]>([
    {
      id: "doc-1",
      project_id: project.id,
      workspace_id: project.workspace_id,
      original_filename: `${project.name} Syllabus & Core Textbook.pdf`,
      extension: ".pdf",
      mime_type: "application/pdf",
      byte_size: 14589200, // 14.5MB
      page_count: 320,
      ingestion_status: "indexed",
      created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
    },
    {
      id: "doc-2",
      project_id: project.id,
      workspace_id: project.workspace_id,
      original_filename: "Lecture 03 - Architecture Foundations.pptx",
      extension: ".pptx",
      mime_type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      byte_size: 4200100, // 4.2MB
      page_count: 45,
      ingestion_status: "indexed",
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
  ]);

  const [showUploadModal, setShowUploadModal] = useState(false);

  const formatBytes = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: ProjectDocument["ingestion_status"]) => {
    switch (status) {
      case "indexed":
        return <Badge variant="emerald">Indexed & Searchable</Badge>;
      case "processing":
        return <Badge variant="amber">Processing (Celery)</Badge>;
      case "uploaded":
        return <Badge variant="slate">Uploaded</Badge>;
      case "failed":
        return <Badge variant="red">Failed</Badge>;
    }
  };

  const handleDelete = (id: string) => {
    setDocuments(documents.filter((d) => d.id !== id));
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
        <Button
          onClick={() => setShowUploadModal(true)}
          size="sm"
          leftIcon={<Upload className="w-3.5 h-3.5" />}
        >
          Add Course Documents
        </Button>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Indexed Project Files
          </span>
          <span className="text-[11px] text-slate-400">
            Target capacity: Up to 500 pages per file
          </span>
        </div>

        {documents.length === 0 ? (
          /* Empty State */
          <div className="p-12 text-center max-w-md mx-auto space-y-3">
            <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">No documents added to this project</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Upload textbook PDFs, lecture slide decks (.pptx), or Word summaries (.docx) to ground
              your project study sessions.
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
                      {doc.page_count && <span>&bull; {doc.page_count} pages / slides</span>}
                      <span>&bull; {new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3 shrink-0 self-end sm:self-center">
                  {getStatusBadge(doc.ingestion_status)}
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

      {/* Upload Modal (With Phase 5 Roadmap notice) */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title="Add Course Documents"
        description="Upload course materials to index them for grounded question-answering."
      >
        <div className="space-y-4 text-xs">
          <div className="p-4 bg-indigo-50/60 border border-indigo-200/80 rounded-xl space-y-2">
            <div className="flex items-center space-x-2 text-indigo-700 font-bold">
              <Info className="w-4 h-4 shrink-0" />
              <span>Phase 5 Ingestion Pipeline Boundary</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Full background Celery worker processing, PDF text extraction, scanned page OCR, and structure-aware chunking activate in Phase 5 according to the roadmap.
            </p>
          </div>

          <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center bg-slate-50/50 space-y-2">
            <Upload className="w-8 h-8 text-slate-400 mx-auto" />
            <span className="font-semibold text-slate-700 block">
              Drag and drop course documents here
            </span>
            <span className="text-[11px] text-slate-400 block">
              Supported formats: .pdf, .docx, .pptx, .txt, .md (Max 50 MB, up to 500 pages)
            </span>
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Button size="sm" onClick={() => setShowUploadModal(false)}>
              Got it
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
