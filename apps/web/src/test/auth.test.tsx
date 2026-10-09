import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { formatAuthError } from "../features/auth/authErrors";
import { LoginPage } from "../pages/LoginPage";
import { SignUpPage } from "../pages/SignUpPage";
import { ForgotPasswordPage } from "../pages/ForgotPasswordPage";
import { ResetPasswordPage } from "../pages/ResetPasswordPage";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { PublicAuthRoute } from "../features/auth/PublicAuthRoute";
import { getAuthRedirectUrl } from "../lib/supabase";
import * as AuthContextModule from "../features/auth/AuthContext";

// Mock AuthContext
const mockSignInWithEmail = vi.fn();
const mockSignUpWithEmail = vi.fn();
const mockSignInWithOAuth = vi.fn();
const mockResetPasswordForEmail = vi.fn();
const mockUpdatePassword = vi.fn();
const mockSignOut = vi.fn();

const defaultAuthContextValue = {
  user: null,
  session: null,
  profile: null,
  token: null,
  loading: false,
  isConfigured: true,
  isRecoveryMode: false,
  signInWithEmail: mockSignInWithEmail,
  signUpWithEmail: mockSignUpWithEmail,
  signInWithOAuth: mockSignInWithOAuth,
  resetPasswordForEmail: mockResetPasswordForEmail,
  updatePassword: mockUpdatePassword,
  signOut: mockSignOut,
};

describe("Authentication Error Formatting", () => {
  it("formats invalid login credentials properly", () => {
    const msg = formatAuthError({ message: "Invalid login credentials" });
    expect(msg).toContain("Incorrect email or password");
  });

  it("formats user already registered properly", () => {
    const msg = formatAuthError({ message: "User already registered" });
    expect(msg).toContain("An account with this email address already exists");
  });

  it("formats email not confirmed error properly", () => {
    const msg = formatAuthError({ message: "Email not confirmed" });
    expect(msg).toContain("verify your email address");
  });

  it("formats password length requirement properly", () => {
    const msg = formatAuthError({ message: "Password should be at least 6 characters" });
    expect(msg).toContain("Password must be at least 8 characters long");
  });

  it("formats rate limit error properly", () => {
    const msg = formatAuthError({ message: "For security purposes, you can only request this once every 60 seconds" });
    expect(msg).toContain("Too many requests");
  });

  it("formats expired token / link error properly", () => {
    const msg = formatAuthError({ message: "Token has expired or is invalid" });
    expect(msg).toContain("invalid or has expired");
  });
});

describe("LoginPage UI & Flows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
    });
  });

  it("renders email, password, remember me, forgot password, and OAuth buttons", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByPlaceholderText(/student@university.edu/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument();
    expect(screen.getByText(/Remember this device/i)).toBeInTheDocument();
    expect(screen.getByText(/Forgot password\?/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Sign In$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Google/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /GitHub/i })).toBeInTheDocument();
    expect(screen.getByText(/Create student account/i)).toBeInTheDocument();
  });

  it("calls signInWithEmail when submitting the login form", async () => {
    mockSignInWithEmail.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/student@university.edu/i), {
      target: { value: "test@university.edu" },
    });
    fireEvent.change(screen.getByPlaceholderText(/••••••••/i), {
      target: { value: "SecurePass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^Sign In$/i }));

    await waitFor(() => {
      expect(mockSignInWithEmail).toHaveBeenCalledWith("test@university.edu", "SecurePass123!");
    });
  });

  it("calls signInWithOAuth when clicking Google button", async () => {
    mockSignInWithOAuth.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("button", { name: /Google/i }));
    expect(mockSignInWithOAuth).toHaveBeenCalledWith("google");
  });

  it("calls signInWithOAuth when clicking GitHub button", async () => {
    mockSignInWithOAuth.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("button", { name: /GitHub/i }));
    expect(mockSignInWithOAuth).toHaveBeenCalledWith("github");
  });
});

describe("SignUpPage UI & Flows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
    });
  });

  it("renders display name, email, password, confirm password, and OAuth buttons", () => {
    render(
      <MemoryRouter initialEntries={["/signup"]}>
        <SignUpPage />
      </MemoryRouter>
    );

    expect(screen.getByPlaceholderText(/Jane Doe/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/student@university.edu/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Minimum 8 characters/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Repeat password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create Student Account/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Google/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /GitHub/i })).toBeInTheDocument();
  });

  it("validates password length (min 8 chars)", async () => {
    render(
      <MemoryRouter initialEntries={["/signup"]}>
        <SignUpPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/Jane Doe/i), {
      target: { value: "Alice Smith" },
    });
    fireEvent.change(screen.getByPlaceholderText(/student@university.edu/i), {
      target: { value: "alice@university.edu" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Minimum 8 characters/i), {
      target: { value: "short" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Repeat password/i), {
      target: { value: "short" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Create Student Account/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/at least 8 characters long/i);
    });
    expect(mockSignUpWithEmail).not.toHaveBeenCalled();
  });

  it("validates that password and confirm password match", async () => {
    render(
      <MemoryRouter initialEntries={["/signup"]}>
        <SignUpPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/Jane Doe/i), {
      target: { value: "Alice Smith" },
    });
    fireEvent.change(screen.getByPlaceholderText(/student@university.edu/i), {
      target: { value: "alice@university.edu" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Minimum 8 characters/i), {
      target: { value: "Password123!" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Repeat password/i), {
      target: { value: "DifferentPassword123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Create Student Account/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Passwords do not match/i);
    });
    expect(mockSignUpWithEmail).not.toHaveBeenCalled();
  });

  it("handles successful signup with email confirmation message", async () => {
    mockSignUpWithEmail.mockResolvedValueOnce({ needsConfirmation: true });

    render(
      <MemoryRouter initialEntries={["/signup"]}>
        <SignUpPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/Jane Doe/i), {
      target: { value: "Alice Smith" },
    });
    fireEvent.change(screen.getByPlaceholderText(/student@university.edu/i), {
      target: { value: "alice@university.edu" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Minimum 8 characters/i), {
      target: { value: "Password123!" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Repeat password/i), {
      target: { value: "Password123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Create Student Account/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/Verification email dispatched/i);
    });
  });
});

describe("ForgotPasswordPage UI & Flows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
    });
  });

  it("renders email input and sends reset link on submit", async () => {
    mockResetPasswordForEmail.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter initialEntries={["/forgot-password"]}>
        <ForgotPasswordPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByPlaceholderText(/student@university.edu/i);
    fireEvent.change(emailInput, { target: { value: "student@mit.edu" } });

    fireEvent.click(screen.getByRole("button", { name: /Send Reset Link/i }));

    await waitFor(() => {
      expect(mockResetPasswordForEmail).toHaveBeenCalledWith("student@mit.edu");
      expect(screen.getByRole("status")).toHaveTextContent(/Recovery link sent!/i);
    });
  });
});

describe("ResetPasswordPage UI & Validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("displays invalid/expired message when not in recovery mode without session", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
      session: null,
      isRecoveryMode: false,
    });

    render(
      <MemoryRouter initialEntries={["/reset-password"]}>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Reset Session Invalid or Expired/i)).toBeInTheDocument();
    expect(screen.getByText(/Request New Reset Link/i)).toBeInTheDocument();
  });

  it("allows setting new password when session/recovery mode is active", async () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
      session: { access_token: "test-token" } as any,
      isRecoveryMode: true,
    });
    mockUpdatePassword.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter initialEntries={["/reset-password"]}>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    const newPassInput = screen.getByPlaceholderText(/Minimum 8 characters/i);
    const confirmInput = screen.getByPlaceholderText(/Repeat new password/i);

    fireEvent.change(newPassInput, { target: { value: "NewPassword123!" } });
    fireEvent.change(confirmInput, { target: { value: "NewPassword123!" } });

    fireEvent.click(screen.getByRole("button", { name: /Update Password/i }));

    await waitFor(() => {
      expect(mockUpdatePassword).toHaveBeenCalledWith("NewPassword123!");
      expect(screen.getByRole("status")).toHaveTextContent(/Password updated successfully!/i);
    });
  });
});

describe("Route Protection", () => {
  it("redirects unauthenticated user from protected route to /login", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
      user: null,
      token: null,
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Protected Dashboard Content</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page Mock</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText(/Protected Dashboard Content/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Login Page Mock/i)).toBeInTheDocument();
  });

  it("redirects authenticated user away from public auth routes to /dashboard", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
      user: { id: "user-123", email: "user@example.com", displayName: "Test User" },
      token: "valid-token",
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route element={<PublicAuthRoute />}>
            <Route path="/login" element={<div>Public Login Page</div>} />
          </Route>
          <Route path="/dashboard" element={<div>Dashboard Destination</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText(/Public Login Page/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Dashboard Destination/i)).toBeInTheDocument();
  });

  it("renders spinner during initial auth check without flashing content", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      ...defaultAuthContextValue,
      loading: true,
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Checking authentication\.\.\./i)).toBeInTheDocument();
    expect(screen.queryByText(/Protected Content/i)).not.toBeInTheDocument();
  });
});

describe("OAuth Redirect URL Resolution", () => {
  it("resolves default path to dashboard on current origin", () => {
    const url = getAuthRedirectUrl();
    expect(url).toContain("/dashboard");
    expect(url.startsWith("http")).toBe(true);
  });

  it("resolves custom path correctly", () => {
    const url = getAuthRedirectUrl("/reset-password");
    expect(url).toContain("/reset-password");
  });

  it("formats OAuth cancellation and callback errors", () => {
    expect(formatAuthError("bad_oauth_callback")).toContain("Authentication was cancelled or the OAuth callback was invalid");
    expect(formatAuthError("OAuth state parameter missing")).toContain("Authentication was cancelled or the OAuth callback was invalid");
    expect(formatAuthError("access_denied")).toContain("Authentication was cancelled or the OAuth callback was invalid");
  });
});
