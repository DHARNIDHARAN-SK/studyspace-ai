import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white font-sans text-xs text-slate-500">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Col */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-md bg-indigo-600 text-white flex items-center justify-center">
                <BookOpen className="w-3.5 h-3.5" />
              </div>
              <span className="font-bold text-sm text-slate-900">StudySpace AI</span>
            </div>
            <p className="text-xs text-slate-500 max-w-sm leading-relaxed">
              Academic document intelligence platform engineered for verifiable citations,
              zero hallucination, and privacy-isolated multi-tenant study workspaces.
            </p>
          </div>

          {/* Links 1 */}
          <div>
            <h4 className="font-semibold text-slate-800 uppercase tracking-wider text-[11px] mb-3">
              Platform
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/features" className="hover:text-indigo-600 transition-colors">
                  Features
                </Link>
              </li>
              <li>
                <Link to="/about" className="hover:text-indigo-600 transition-colors">
                  About Mission
                </Link>
              </li>
              <li>
                <Link to="/contact" className="hover:text-indigo-600 transition-colors">
                  Contact Support
                </Link>
              </li>
            </ul>
          </div>

          {/* Links 2 */}
          <div>
            <h4 className="font-semibold text-slate-800 uppercase tracking-wider text-[11px] mb-3">
              Account
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/login" className="hover:text-indigo-600 transition-colors">
                  Sign In
                </Link>
              </li>
              <li>
                <Link to="/signup" className="hover:text-indigo-600 transition-colors">
                  Create Account
                </Link>
              </li>
              <li>
                <Link to="/dashboard" className="hover:text-indigo-600 transition-colors">
                  Student Dashboard
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-400 gap-4">
          <p>&copy; {new Date().getFullYear()} StudySpace AI. Built strictly to master architecture specification.</p>
          <div className="flex space-x-6">
            <span>PostgreSQL &bull; pgvector</span>
            <span>Row-Level Security</span>
            <span>Evidence-First RAG</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
