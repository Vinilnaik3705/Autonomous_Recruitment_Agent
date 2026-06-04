"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth-client";
import { Lock, Mail, User, Shield, AlertCircle, Github } from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectByRole = (userRole: string) => {
    if (userRole === "student") {
      router.push("/dashboard/student");
    } else if (userRole === "hr") {
      router.push("/dashboard/admin");
    } else {
      router.push("/dashboard/recruiter");
    }
  };
  
  const [tab, setTab] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("recruiter");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "signup") {
      setTab("signup");
    }

    // Check if session is already active (e.g. returning from social login redirect)
    authClient.getSession().then((session) => {
      if (session?.data?.user) {
        const userRole = session.data.user.role || "recruiter";
        redirectByRole(userRole);
      }
    });
  }, [searchParams, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (tab === "login") {
        const { error: signInError } = await authClient.signIn.email({
          email,
          password,
        });

        if (signInError) {
          throw new Error(signInError.message || "Invalid email or password");
        }

        // Fetch session to determine role and redirect
        const session = await authClient.getSession();
        const userRole = session?.data?.user?.role || "recruiter";
        redirectByRole(userRole);
      } else {
        const { error: signUpError } = await authClient.signUp.email({
          email,
          password,
          name,
          role,
        });

        if (signUpError) {
          throw new Error(signUpError.message || "Failed to create account");
        }

        // Successfully registered, auto login and redirect
        redirectByRole(role);
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handleSocialLogin = async (provider: "google" | "github") => {
    setLoading(true);
    setError(null);
    try {
      const { error: socialError } = await authClient.signIn.social({
        provider,
        callbackURL: "/login",
        role: tab === "signup" ? role : undefined,
        mode: tab === "signup" ? "signup" : "login",
      });
      if (socialError) {
        throw new Error(socialError.message || `Failed to sign in with ${provider}`);
      }

      const session = await authClient.getSession();
      const userRole = session?.data?.user?.role || "recruiter";
      redirectByRole(userRole);
    } catch (err: any) {
      setError(err.message || `Failed to sign in with ${provider}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-mesh min-h-screen flex items-center justify-center p-6 selection:bg-orange-500 selection:text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-950/80 p-8 shadow-2xl relative">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-orange-600 flex items-center justify-center font-extrabold text-2xl text-white mb-4">A</div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Welcome to Antigravity</h2>
          <p className="text-slate-400 text-sm mt-2">Enterprise-Grade AI Recruitment Platform</p>
        </div>

        {/* Tab Selection */}
        <div className="grid grid-cols-2 p-1 bg-slate-900 border border-slate-800 rounded-xl mb-6">
          <button
            onClick={() => setTab("login")}
            suppressHydrationWarning
            className={`py-2 text-sm font-semibold rounded-lg transition-all ${tab === "login" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"}`}
          >
            Sign In
          </button>
          <button
            onClick={() => setTab("signup")}
            suppressHydrationWarning
            className={`py-2 text-sm font-semibold rounded-lg transition-all ${tab === "signup" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"}`}
          >
            Sign Up
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2.5 text-red-400 text-sm mb-6">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === "signup" && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  required
                  suppressHydrationWarning
                  placeholder="e.g. John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 transition-colors"
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="email"
                required
                suppressHydrationWarning
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 transition-colors"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                required
                suppressHydrationWarning
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 transition-colors"
              />
            </div>
          </div>

          {tab === "signup" && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">I am a</label>
              <div className="relative">
                <Shield className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <select
                  value={role}
                  suppressHydrationWarning
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-white appearance-none focus:outline-none focus:border-orange-500 transition-colors"
                >
                  <option value="recruiter">Recruiter</option>
                  <option value="student">Student</option>
                  <option value="hr">HR</option>
                </select>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            suppressHydrationWarning
            className="w-full py-3.5 bg-orange-600 hover:bg-orange-500 text-white font-bold rounded-xl shadow-lg shadow-orange-600/20 hover:shadow-orange-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            {loading ? "Please wait..." : tab === "login" ? "Sign In" : "Sign Up"}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6 flex items-center justify-center">
          <div className="absolute inset-0 border-t border-slate-800/80"></div>
          <span className="relative px-3 bg-slate-950 text-xs font-semibold text-slate-500 uppercase tracking-wider">Or continue with</span>
        </div>

        {/* Social Buttons */}
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            disabled={loading}
            suppressHydrationWarning
            onClick={() => handleSocialLogin("google")}
            className="flex items-center justify-center gap-2.5 py-3 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 font-semibold rounded-xl transition-all disabled:opacity-50"
          >
            <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            <span>Google</span>
          </button>
          <button
            type="button"
            disabled={loading}
            suppressHydrationWarning
            onClick={() => handleSocialLogin("github")}
            className="flex items-center justify-center gap-2.5 py-3 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 font-semibold rounded-xl transition-all disabled:opacity-50"
          >
            <Github className="w-4 h-4 text-slate-200 shrink-0" />
            <span>GitHub</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-400">
        Loading...
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
