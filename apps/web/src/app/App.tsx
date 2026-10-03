import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../features/auth/AuthContext";
import { ProjectProvider } from "../features/projects/ProjectContext";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { AppShell } from "../components/layout/AppShell";
import { LandingPage } from "../pages/LandingPage";
import { AboutPage } from "../pages/AboutPage";
import { FeaturesPage } from "../pages/FeaturesPage";
import { ContactPage } from "../pages/ContactPage";
import { LoginPage } from "../pages/LoginPage";
import { SignUpPage } from "../pages/SignUpPage";
import { DashboardPage } from "../pages/DashboardPage";
import { ProjectsPage } from "../pages/ProjectsPage";
import { ProjectPage } from "../pages/ProjectPage";
import { SettingsPage } from "../pages/SettingsPage";
import { DeveloperPage } from "../pages/DeveloperPage";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ProjectProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignUpPage />} />

            {/* Authenticated Application Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/projects" element={<ProjectsPage />} />
                <Route path="/projects/:projectId" element={<ProjectPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/developer" element={<DeveloperPage />} />
              </Route>
            </Route>

            {/* Catch-all Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ProjectProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
