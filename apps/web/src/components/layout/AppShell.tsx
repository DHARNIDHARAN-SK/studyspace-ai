import { useState } from "react";
import { Outlet } from "react-router-dom";
import { BookOpen, Menu } from "lucide-react";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Mobile Topbar */}
      <header className="md:hidden h-14 bg-white border-b border-slate-200 px-4 flex items-center justify-between sticky top-0 z-30">
        <button
          onClick={() => setSidebarOpen(true)}
          className="text-slate-600 hover:text-slate-900 p-1.5 rounded-lg hover:bg-slate-100"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center space-x-2">
          <div className="bg-indigo-600 text-white p-1 rounded-md">
            <BookOpen className="w-4 h-4" />
          </div>
          <span className="font-bold text-sm text-slate-900">StudySpace AI</span>
        </div>
        <div className="w-8" />
      </header>

      {/* Persistent Left Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main App Content Area */}
      <div className="md:pl-64 flex-1 flex flex-col min-h-screen">
        <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200/80 bg-white/50 py-4 px-6 text-center text-[11px] text-slate-400">
          StudySpace AI &bull; Grounded Academic Intelligence &bull; Multi-Tenant Workspace
        </footer>
      </div>
    </div>
  );
}
