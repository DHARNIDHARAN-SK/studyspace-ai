import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckSquare,
  Cpu,
  FileCheck2,
  FileText,
  HelpCircle,
  Search,
  ShieldCheck,
} from "lucide-react";
import { PublicHeader } from "../components/layout/PublicHeader";
import { PublicFooter } from "../components/layout/PublicFooter";
import { Button } from "../components/ui/Button";

export function FeaturesPage() {
  const featureList = [
    {
      title: "1. Multi-Format Academic Ingestion",
      tag: "500-Page Scale Target",
      desc: "Native format parsing for PDF, DOCX, PPTX, TXT, and Markdown. Preserves slide numbers, chapter headings, and page boundaries throughout chunking.",
      icon: FileText,
    },
    {
      title: "2. Hybrid Retrieval Architecture",
      tag: "pgvector + tsvector",
      desc: "Dense semantic vector search (768-dim embeddings) executed in parallel with PostgreSQL full-text search, fused via Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking.",
      icon: Search,
    },
    {
      title: "3. Grounded Chat with Page Citations",
      tag: "Zero-Hallucination Policy",
      desc: "Every claim cited by the assistant links to an immutable stored passage. Source drawer displays the exact quoted passage and page location.",
      icon: FileCheck2,
    },
    {
      title: "4. Student Revision Tracker",
      tag: "Active Recall",
      desc: "Project-scoped revision checklist with status tracking (Not Started, Learning, Revised) linked directly to course sources and conversation history.",
      icon: CheckSquare,
    },
    {
      title: "5. Source-Grounded Practice Quizzes",
      tag: "Protected Answers",
      desc: "Generate multiple-choice, short-answer, and challenge questions directly from course slides. Answers and detailed explanations remain protected until attempt submission.",
      icon: HelpCircle,
    },
    {
      title: "6. Tenant Isolation & Developer REST API",
      tag: "Row-Level Security",
      desc: "Complete multi-tenant workspace isolation at the PostgreSQL layer. Programmatic REST API with hashed platform keys for research pipelines.",
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <PublicHeader />

      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <Link
          to="/"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>

        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-[11px] font-semibold">
            <Cpu className="w-3 h-3" />
            <span>Platform Capabilities</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Engineered for comprehensive syllabus mastery.
          </h1>
          <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">
            Explore the six core pillars of StudySpace AI, designed strictly according to the Master Architecture.
          </p>
        </div>

        {/* Feature Grid */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
          {featureList.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                      {f.tag}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{f.title}</h3>
                  <p className="text-xs text-slate-500 mt-2 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom CTA */}
        <div className="mt-12 text-center bg-white rounded-xl border border-slate-200 p-8 shadow-xs">
          <h3 className="text-base font-bold text-slate-900">Experience Grounded Course Intelligence</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Create an academic workspace and start organizing your courses today.
          </p>
          <div className="mt-5">
            <Link to="/signup">
              <Button size="md">Get Started with Free Workspace</Button>
            </Link>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
