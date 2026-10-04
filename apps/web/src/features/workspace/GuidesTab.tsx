import { useCallback, useEffect, useState } from "react";
import { BookOpen, Download, Loader2, Plus, Printer, RefreshCw } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import { useAuth } from "../auth/AuthContext";
import {
  exportContent,
  generateStudyGuide,
  listStudyGuides,
} from "../../lib/api-client";
import type { Project, StudyGuide } from "../../types";

interface GuidesTabProps {
  project: Project;
}

export function GuidesTab({ project }: GuidesTabProps) {
  const { token } = useAuth();
  const [guides, setGuides] = useState<StudyGuide[]>([]);
  const [activeGuide, setActiveGuide] = useState<StudyGuide | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [topic, setTopic] = useState(`${project.name} Exam Review`);
  const [guideType, setGuideType] = useState<string>("summary");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const fetchGuides = useCallback(async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      setError(null);
      const res = await listStudyGuides(token, project.id);
      setGuides(res.guides);
      if (res.guides.length > 0) {
        setActiveGuide(res.guides[0]);
      } else {
        setActiveGuide(null);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load study guides");
    } finally {
      setIsLoading(false);
    }
  }, [token, project.id]);

  useEffect(() => {
    fetchGuides();
  }, [fetchGuides]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !topic.trim()) return;
    try {
      setIsGenerating(true);
      setError(null);
      const newGuide = await generateStudyGuide(token, project.id, {
        topic: topic.trim(),
        guide_type: guideType,
      });
      setGuides((prev) => [newGuide, ...prev]);
      setActiveGuide(newGuide);
      setShowCreateModal(false);
    } catch (err: any) {
      setError(err?.message || "Failed to generate study guide");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExport = async (format: "markdown" | "txt") => {
    if (!token || !activeGuide) return;
    try {
      setIsExporting(true);
      const res = await exportContent(token, project.id, {
        source_type: "study_guide",
        source_id: activeGuide.id,
        format,
      });

      if (res.content) {
        const blob = new Blob([res.content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = res.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to export study guide");
    } finally {
      setIsExporting(false);
    }
  };

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
            Structured exam prep summaries, cheat sheets, and conceptual definitions grounded in your sources.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => fetchGuides()}
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />}
          >
            Refresh
          </Button>
          <Button
            onClick={() => setShowCreateModal(true)}
            size="sm"
            leftIcon={<Plus className="w-3.5 h-3.5" />}
          >
            Create Study Guide
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 text-xs bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Guide selector if multiple */}
      {guides.length > 1 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-slate-200 text-xs">
          {guides.map((g) => (
            <button
              key={g.id}
              onClick={() => setActiveGuide(g)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap ${
                activeGuide?.id === g.id
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {g.title}
            </button>
          ))}
        </div>
      )}

      {isLoading && guides.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
          <span>Loading study guides...</span>
        </div>
      ) : activeGuide ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          {/* Guide Toolbar */}
          <div className="px-6 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
            <div>
              <div className="flex items-center space-x-2">
                <Badge variant="indigo">
                  {activeGuide.guide_type ? activeGuide.guide_type.replace("_", " ").toUpperCase() : "STUDY GUIDE"}
                </Badge>
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
                disabled={isExporting}
                onClick={() => handleExport("markdown")}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                {isExporting ? "Exporting..." : "Export Markdown"}
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
          No study guides created for this project yet. Click &quot;Create Study Guide&quot; above to generate one from your documents.
        </div>
      )}

      {/* Create Guide Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Generate Grounded Study Guide"
        description="Synthesizes verified knowledge from your indexed syllabus and documents."
      >
        <form onSubmit={handleGenerate} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Guide Topic *
            </label>
            <input
              type="text"
              required
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Asymptotic Analysis or Dynamic Programming"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Guide Format
            </label>
            <select
              value={guideType}
              onChange={(e) => setGuideType(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white"
            >
              <option value="summary">Executive Summary</option>
              <option value="key_concepts">Key Concepts & Principles</option>
              <option value="formula_sheet">Formulas & Definitions</option>
              <option value="definitions">Glossary</option>
            </select>
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isGenerating}
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isGenerating}
              leftIcon={isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : undefined}
            >
              {isGenerating ? "Synthesizing..." : "Generate"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

