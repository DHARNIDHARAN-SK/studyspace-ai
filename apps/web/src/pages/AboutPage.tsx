import { Link } from "react-router-dom";
import {
  ArrowLeft,
  BookOpen,
  Database,
  ExternalLink,
  Github,
  Linkedin,
  Mail,
  Phone,
  Shield,
  Target,
  User,
} from "lucide-react";
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

        {/* Developer Profile Card */}
        <div className="mt-8 bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
            <div className="flex items-start space-x-4">
              <div className="w-14 h-14 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                <User className="w-7 h-7" />
              </div>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600">
                  Creator & Lead Developer
                </span>
                <h2 className="text-xl font-bold text-slate-900">Dharanidharan</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Architect and developer of StudySpace AI — high-accuracy academic RAG, structure-aware document parsing, and student mastery tooling.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            {/* Phone */}
            <a
              href="tel:9080284858"
              className="flex items-center space-x-2.5 p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-indigo-50/50 hover:border-indigo-200 transition-colors group"
            >
              <Phone className="w-4 h-4 text-slate-500 group-hover:text-indigo-600" />
              <div>
                <div className="text-[10px] text-slate-400 font-semibold uppercase">Phone</div>
                <div className="text-slate-800 font-medium group-hover:text-indigo-600">9080284858</div>
              </div>
            </a>

            {/* Email */}
            <a
              href="mailto:karnan284858@gmail.com"
              className="flex items-center space-x-2.5 p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-indigo-50/50 hover:border-indigo-200 transition-colors group"
            >
              <Mail className="w-4 h-4 text-slate-500 group-hover:text-indigo-600" />
              <div className="truncate">
                <div className="text-[10px] text-slate-400 font-semibold uppercase">Email</div>
                <div className="text-slate-800 font-medium group-hover:text-indigo-600 truncate">
                  karnan284858@gmail.com
                </div>
              </div>
            </a>

            {/* GitHub */}
            <a
              href="https://github.com/DHARNIDHARAN-SK"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2.5 p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-indigo-50/50 hover:border-indigo-200 transition-colors group"
            >
              <Github className="w-4 h-4 text-slate-500 group-hover:text-indigo-600" />
              <div className="truncate">
                <div className="text-[10px] text-slate-400 font-semibold uppercase">GitHub</div>
                <div className="text-slate-800 font-medium group-hover:text-indigo-600 flex items-center space-x-1">
                  <span>DHARNIDHARAN-SK</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </div>
              </div>
            </a>

            {/* LinkedIn */}
            <a
              href="https://www.linkedin.com/in/sk-dharanidharan-579344362/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2.5 p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-indigo-50/50 hover:border-indigo-200 transition-colors group"
            >
              <Linkedin className="w-4 h-4 text-slate-500 group-hover:text-indigo-600" />
              <div className="truncate">
                <div className="text-[10px] text-slate-400 font-semibold uppercase">LinkedIn</div>
                <div className="text-slate-800 font-medium group-hover:text-indigo-600 flex items-center space-x-1">
                  <span>SK Dharanidharan</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </div>
              </div>
            </a>
          </div>
        </div>

        {/* Content Section */}
        <div className="mt-8 bg-white rounded-xl border border-slate-200 p-8 shadow-xs space-y-6 text-xs sm:text-sm text-slate-600 leading-relaxed">
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
