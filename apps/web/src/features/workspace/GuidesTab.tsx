import { useState } from "react";
import { BookOpen, Download, Plus, Printer } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import type { Project, StudyGuide } from "../../types";

interface GuidesTabProps {
  project: Project;
}

export function GuidesTab({ project }: GuidesTabProps) {
  const [guides] = useState<StudyGuide[]>([
    {
      id: "guide-1",
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: `${project.name} — High-Yield Exam Review Guide`,
      guide_type: "exam_prep",
      content: `## Executive Overview

This study guide synthesizes key course topics from your verified syllabus materials.

### 1. Foundational Architecture & Ingestion
- Multimodal parsing supports **PDF**, **DOCX**, **PPTX**, and **Markdown** up to 500 pages per file.
- Structure-aware chunking preserves slide titles, page boundaries, and section hierarchies.

### 2. Retrieval Rigor
- Dense semantic vector search (768-dim embeddings) operates in parallel with PostgreSQL full-text search.
- Reciprocal Rank Fusion (RRF) reconciles vector distance with exact technical vocabulary.

### 3. Verification & Anti-Hallucination
- All statements link directly to the underlying document chunk ID.
- Abstention occurs automatically when evidence threshold is unsatisfied.`,
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
  ]);

  const [activeGuide] = useState<StudyGuide | null>(guides[0]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [exportNotice, setExportNotice] = useState(false);

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Course Study Guides
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Structured exam prep summaries, cheat sheets, and conceptual definitions.
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          size="sm"
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          Create Study Guide
        </Button>
      </div>

      {activeGuide ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          {/* Guide Toolbar */}
          <div className="px-6 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
            <div>
              <div className="flex items-center space-x-2">
                <Badge variant="indigo">Comprehensive Exam Prep</Badge>
                <span className="text-[11px] text-slate-400">
                  Created {new Date(activeGuide.created_at).toLocaleDateString()}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-1">{activeGuide.title}</h3>
            </div>

            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setExportNotice(true)}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                Export PDF
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.print()}
                leftIcon={<Printer className="w-3.5 h-3.5" />}
              >
                Print
              </Button>
            </div>
          </div>

          {/* Guide Document Canvas */}
          <div className="p-6 sm:p-8 max-w-3xl mx-auto prose prose-slate prose-xs leading-relaxed">
            <div className="whitespace-pre-wrap text-xs sm:text-sm text-slate-800 font-sans leading-relaxed">
              {activeGuide.content}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500">
          No study guides created for this project yet.
        </div>
      )}

      {/* Export Engine Roadmap Modal */}
      <Modal
        isOpen={exportNotice}
        onClose={() => setExportNotice(false)}
        title="Export Engine Integration Notice"
        description="PDF & DOCX document generation belongs to Phase 7."
      >
        <div className="space-y-3 text-xs text-slate-600">
          <p>
            Per the Master Implementation Plan, the dedicated multi-format export engine (with page limit bounding, clean CSS formatting, and private storage delivery) will activate in <strong>Phase 7</strong>.
          </p>
          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Button size="sm" onClick={() => setExportNotice(false)}>
              Got it
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Guide Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Generate Study Guide"
        description="Select synthesis type and scope."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Guide Title *
            </label>
            <input
              type="text"
              defaultValue={`${project.name} Review Guide`}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Guide Format
            </label>
            <select className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white">
              <option value="exam_prep">Comprehensive Exam Prep</option>
              <option value="summary">Executive Syllabus Summary</option>
              <option value="definitions">Glossary of Formulas & Definitions</option>
            </select>
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => setShowCreateModal(false)}>
              Generate
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
