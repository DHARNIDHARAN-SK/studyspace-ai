import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  CheckCircle,
  FileCheck2,
  FileText,
  HelpCircle,
  Layers,
  Lock,
  Search,
  Shield,
  Sparkles,
} from "lucide-react";
import { PublicHeader } from "../components/layout/PublicHeader";
import { PublicFooter } from "../components/layout/PublicFooter";
import { Button } from "../components/ui/Button";

export function LandingPage() {
  const capabilities = [
    {
      title: "Grounded Page & Slide Citations",
      description:
        "Every claim links directly to the underlying document chunk, page number, slide index, or section path. Never guess whether an answer is factual.",
      icon: FileCheck2,
    },
    {
      title: "Multimodal Document Intelligence",
      description:
        "Upload course syllabi, lecture slides, textbooks, and research papers up to 500 pages (.pdf, .docx, .pptx, .txt, .md) with structure-aware chunking.",
      icon: FileText,
    },
    {
      title: "Hybrid Vector + Lexical Search",
      description:
        "Combines 768-dimensional dense vector embeddings with PostgreSQL full-text search and reciprocal rank fusion for pinpoint recall of formulas and terms.",
      icon: Search,
    },
    {
      title: "Structured Revision Checklists",
      description:
        "Track study progress from not-started to learning and revised. Direct link to related source passages ensures comprehensive syllabus coverage.",
      icon: Layers,
    },
    {
      title: "Source-Grounded Practice Quizzes",
      description:
        "Generate targeted multiple-choice, short-answer, and challenge questions. Answer keys and explanations remain strictly protected until attempt submission.",
      icon: HelpCircle,
    },
    {
      title: "Tenant-Isolated Private Workspaces",
      description:
        "Engineered with Supabase Row-Level Security and private object storage paths. Your academic files and notes are never exposed to another student.",
      icon: Shield,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <PublicHeader />

      {/* Hero Section */}
      <section className="py-16 sm:py-24 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto text-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 text-xs font-semibold mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Grounded Academic Intelligence for Students</span>
        </div>

        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
          Master course material with{" "}
          <span className="text-indigo-600">verifiable evidence.</span>
        </h1>

        <p className="mt-6 text-sm sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          StudySpace AI transforms large textbooks, lecture slides, and notes into an interactive
          study partner with traceable page-level citations, practice quizzes, and structured revision tracking.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link to="/signup">
            <Button size="lg" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Get Started Free
            </Button>
          </Link>
          <Link to="/features">
            <Button variant="outline" size="lg">
              Explore Architecture
            </Button>
          </Link>
        </div>

        <div className="mt-8 flex items-center justify-center space-x-6 text-xs text-slate-500 font-medium">
          <span className="flex items-center">
            <CheckCircle className="w-4 h-4 text-emerald-600 mr-1.5" /> No hallucinated answers
          </span>
          <span className="flex items-center">
            <Lock className="w-4 h-4 text-emerald-600 mr-1.5" /> Row-Level Security
          </span>
          <span className="flex items-center">
            <BookOpen className="w-4 h-4 text-emerald-600 mr-1.5" /> 500-page target
          </span>
        </div>
      </section>

      {/* Architecture Highlights Grid */}
      <section className="py-16 bg-white border-y border-slate-200/80">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              Core Architecture
            </h2>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 mt-2 tracking-tight">
              Built for academic rigor, not generic chatbots.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {capabilities.map((c) => {
              const Icon = c.icon;
              return (
                <div
                  key={c.title}
                  className="bg-slate-50/60 rounded-xl border border-slate-200/80 p-6 hover:border-indigo-300 hover:bg-slate-50 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mb-4">
                      <Icon className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 tracking-tight">{c.title}</h3>
                    <p className="text-xs text-slate-500 mt-2 leading-relaxed">{c.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Call to action */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-center">
        <div className="bg-gradient-to-b from-indigo-50/80 to-white rounded-2xl border border-indigo-100 p-8 sm:p-12 shadow-xs">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Ready to organize your academic semester?
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 mt-3 max-w-lg mx-auto leading-relaxed">
            Create an isolated study workspace, organize projects by course or subject, and prepare with source-grounded answers.
          </p>
          <div className="mt-6 flex justify-center">
            <Link to="/signup">
              <Button size="md" rightIcon={<ArrowRight className="w-4 h-4" />}>
                Create Your Account
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
