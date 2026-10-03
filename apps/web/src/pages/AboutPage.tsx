import { Link } from "react-router-dom";
import { ArrowLeft, BookOpen, Database, Shield, Target } from "lucide-react";
import { PublicHeader } from "../components/layout/PublicHeader";
import { PublicFooter } from "../components/layout/PublicFooter";
import { Button } from "../components/ui/Button";

export function AboutPage() {
  const principles = [
    {
      title: "Evidence-First Grounding",
      desc: "Generic LLMs fabricate citations, quotes, and statistics. StudySpace AI only generates responses from verified passages retrieved from your uploaded course corpus.",
      icon: Target,
    },
    {
      title: "Strict Multi-Tenant Isolation",
      desc: "Your course notes, exam materials, and conversation transcripts are protected by PostgreSQL Row-Level Security and private object storage partitions.",
      icon: Shield,
    },
    {
      title: "Reproducible Academic Integrity",
      desc: "Every answer links directly to the exact source chunk, page, slide number, or section header. If the material does not contain the answer, the system explicitly abstains.",
      icon: Database,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <PublicHeader />

      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
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
            <BookOpen className="w-3 h-3" />
            <span>Academic Intelligence Mission</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Built for truth, verified citations, and disciplined study.
          </h1>
          <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">
            StudySpace AI was engineered to bridge the trust gap between artificial intelligence
            and rigorous academic education.
          </p>
        </div>

        {/* Content Section */}
        <div className="mt-12 bg-white rounded-xl border border-slate-200 p-8 shadow-xs space-y-6 text-xs sm:text-sm text-slate-600 leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">The Problem with Generic AI in Education</h2>
          <p>
            When students use general-purpose conversational AI for coursework, they are frequently
            misled by confident hallucinations: plausible-sounding mathematical derivations, invented
            historical citations, and fabricated textbook quotes.
          </p>
          <p>
            In university coursework, an uncited or fabricated answer results in failed assignments and
            academic integrity violations. Students need a system that acts not as an omniscient oracle,
            but as a disciplined research assistant bound strictly to the syllabus and course materials.
          </p>

          <h2 className="text-base font-bold text-slate-900 pt-4">Our Three Non-Negotiable Principles</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            {principles.map((p) => {
              const Icon = p.icon;
              return (
                <div key={p.title} className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <div className="w-7 h-7 rounded-md bg-indigo-50 text-indigo-600 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-xs text-slate-900">{p.title}</h3>
                  <p className="text-[11px] text-slate-500 leading-normal">{p.desc}</p>
                </div>
              );
            })}
          </div>

          <h2 className="text-base font-bold text-slate-900 pt-4">Open Infrastructure & Extensibility</h2>
          <p>
            StudySpace AI provides persistent multi-tenant workspaces with PostgreSQL and pgvector,
            structure-aware chunking preserving slide and page provenance, and developer REST APIs
            with cryptographically hashed platform keys for academic research labs.
          </p>
        </div>

        {/* CTA */}
        <div className="mt-8 text-center">
          <Link to="/signup">
            <Button size="md">Start Studying with StudySpace AI</Button>
          </Link>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
