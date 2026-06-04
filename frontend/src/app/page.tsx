"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Bot, Calendar, CheckCircle2, ShieldCheck, Zap, Sparkles } from "lucide-react";

export default function LandingPage() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  if (!mounted) {
    return (
      <div className="bg-mesh min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-lg bg-orange-600 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="bg-mesh min-h-screen text-slate-100 font-sans overflow-x-hidden selection:bg-orange-500 selection:text-white">
      {/* Navigation */}
      <header className="fixed top-0 w-full z-50 backdrop-blur-md bg-slate-950/40 border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xl tracking-tight text-white">
            <span className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center font-extrabold text-lg">A</span>
            <span className="whitespace-nowrap">
              Antigravity <span className="text-orange-500">Recruit</span>
            </span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
            <a href="#about" className="hover:text-white transition-colors">About</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-semibold hover:text-white transition-colors">
              Sign In
            </Link>
            <Link href="/login?tab=signup" className="px-4 py-2 text-sm font-semibold rounded-lg bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-600/20 hover:shadow-orange-500/30 transition-all">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 max-w-7xl mx-auto flex flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs font-semibold mb-6 animate-pulse"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Introducing Enterprise AI Scoring</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-6xl font-extrabold tracking-tight max-w-4xl text-white mb-6 leading-tight"
        >
          Hire the best talent. <br />
          <span className="gradient-text-primary">Autonomously, at scale.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-slate-400 text-lg sm:text-xl max-w-2xl mb-10 leading-relaxed"
        >
          Streamline resume screening, run automated online assessments, and coordinate interviewer schedules on a single, secure enterprise-grade platform.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 justify-center w-full max-w-md mb-16"
        >
          <Link href="/login?tab=signup" className="flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-orange-600 hover:bg-orange-500 font-bold shadow-lg shadow-orange-600/30 hover:shadow-orange-500/40 transition-all group">
            <span>Start Free Trial</span>
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a href="#features" className="flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 font-semibold transition-all">
            Explore Features
          </a>
        </motion.div>

        {/* Dashboard Preview Mockup */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="w-full max-w-5xl rounded-2xl border border-slate-800 bg-slate-950/80 p-4 shadow-2xl shadow-orange-500/5 relative group"
        >
          <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-72 h-72 bg-orange-500/10 rounded-full blur-3xl -z-10 group-hover:bg-orange-500/15 transition-all duration-500" />
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-4">
            <span className="w-3 h-3 rounded-full bg-red-500/50" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/50" />
            <span className="w-3 h-3 rounded-full bg-green-500/50" />
            <span className="text-xs text-slate-500 ml-4 font-mono">recruitment.antigravity.io/dashboard</span>
          </div>
          {/* Mock Dashboard Screenshot Asset */}
          <div className="bg-slate-900/50 rounded-xl border border-slate-800/80 aspect-[16/9] flex items-center justify-center p-8 overflow-hidden">
            <div className="grid grid-cols-3 gap-6 w-full h-full text-left">
              <div className="col-span-2 border border-slate-800 bg-slate-950/60 rounded-xl p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-lg text-white">Candidate Ranking</h3>
                    <span className="text-xs text-slate-500 font-mono">Job: Senior React Developer</span>
                  </div>
                  <div className="space-y-3">
                    {[
                      { name: "John Doe", score: 94, status: "Shortlisted", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
                      { name: "Alice Smith", score: 88, status: "Shortlisted", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
                      { name: "Bob Johnson", score: 71, status: "Screened", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" }
                    ].map((c, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                        <div className="flex items-center gap-3">
                          <span className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-slate-300">{i+1}</span>
                          <span className="font-semibold text-slate-200">{c.name}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="font-mono text-orange-500 font-bold">{c.score}%</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full border ${c.color}`}>{c.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden mt-4">
                  <div className="h-full w-4/5 bg-gradient-to-r from-orange-600 to-blue-500 rounded-full" />
                </div>
              </div>
              <div className="border border-slate-800 bg-slate-950/60 rounded-xl p-6 flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-lg text-white mb-4">Pipeline Stats</h3>
                  <div className="space-y-4">
                    <div>
                      <span className="text-xs text-slate-500 uppercase font-semibold">Total Resumes</span>
                      <p className="text-3xl font-extrabold text-white mt-1">1,482</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 uppercase font-semibold">Interview Rate</span>
                      <p className="text-3xl font-extrabold text-blue-400 mt-1">12.4%</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-center py-4 bg-orange-600/10 border border-orange-500/20 rounded-xl gap-2 text-orange-400 font-semibold text-sm">
                  <Bot className="w-4 h-4" />
                  <span>AI Recruiter Active</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 border-t border-slate-900 bg-slate-950/20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white mb-4">Built for Enterprise scale.</h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Everything you need to automate screening, assessments, scheduling, and notifications safely.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: <Bot className="w-6 h-6 text-orange-500" />, title: "AI Candidate Scoring", desc: "Embeddings-based semantic similarity to rank profiles objectively against job requirements." },
              { icon: <Zap className="w-6 h-6 text-yellow-500" />, title: "Celery Workers Async", desc: "Background parsing and analysis engine runs completely decoupled off the main thread." },
              { icon: <Calendar className="w-6 h-6 text-blue-500" />, title: "Automated Calendars", desc: "Cross-matches panel availabilities and automates calendar scheduling links." },
              { icon: <CheckCircle2 className="w-6 h-6 text-emerald-500" />, title: "Online Assessment Sync", desc: "Tracks HackerRank/Codilot completions in real-time, auto-scheduling subsequent steps." },
              { icon: <ShieldCheck className="w-6 h-6 text-violet-500" />, title: "Granular RBAC", desc: "Secured backend validators to keep candidate details isolated from recruiter panels." },
              { icon: <Sparkles className="w-6 h-6 text-cyan-500" />, title: "Firebase Authentication", desc: "Email and Google sign-in with backend allowlist enforcement for approved users." }
            ].map((f, i) => (
              <div key={i} className="p-8 rounded-2xl border border-slate-800/80 bg-slate-950/40 hover:bg-slate-950/90 hover:border-slate-700/80 transition-all group">
                <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  {f.icon}
                </div>
                <h3 className="font-bold text-xl text-white mb-3">{f.title}</h3>
                <p className="text-slate-400 leading-relaxed text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 border-t border-slate-900 bg-slate-950/40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs font-semibold mb-4"
            >
              <Sparkles className="w-3 h-3" />
              <span>Simple, Transparent Pricing</span>
            </motion.div>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white mb-4">Flexible plans for any size team</h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Choose the perfect plan to automate your hiring pipeline and scale your recruitment operations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
            {/* Starter Plan */}
            <motion.div
              whileHover={{ y: -5 }}
              transition={{ duration: 0.2 }}
              className="p-8 rounded-3xl border border-slate-800/80 bg-slate-950/60 flex flex-col justify-between"
            >
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Starter</h3>
                <p className="text-slate-400 text-sm mb-6">Perfect for small teams testing AI hiring tools.</p>
                <div className="flex items-baseline gap-1 text-white mb-8">
                  <span className="text-4xl font-extrabold">$0</span>
                  <span className="text-slate-500 text-sm">/ month</span>
                </div>
                <ul className="space-y-4 text-slate-300 text-sm">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Up to 50 resume screenings / mo</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Basic AI scoring & ranking</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Email templates & scheduling</span>
                  </li>
                </ul>
              </div>
              <Link href="/login?tab=signup" className="mt-8 w-full py-3 text-center rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-white font-semibold transition-all">
                Get Started
              </Link>
            </motion.div>

            {/* Professional Plan (Featured) */}
            <motion.div
              whileHover={{ y: -5 }}
              transition={{ duration: 0.2 }}
              className="p-8 rounded-3xl border-2 border-orange-500 bg-slate-950/90 flex flex-col justify-between relative shadow-xl shadow-orange-500/5"
            >
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-orange-600 text-white text-xs font-bold flex items-center gap-1 shadow-lg shadow-orange-600/30">
                <Zap className="w-3 h-3 fill-current" />
                <span>MOST POPULAR</span>
              </div>
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Professional</h3>
                <p className="text-slate-400 text-sm mb-6">Designed for growing companies with high volume hiring.</p>
                <div className="flex items-baseline gap-1 text-white mb-8">
                  <span className="text-4xl font-extrabold">$149</span>
                  <span className="text-slate-500 text-sm">/ month</span>
                </div>
                <ul className="space-y-4 text-slate-300 text-sm">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span className="font-semibold text-white">Unlimited resume screenings</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Enterprise semantic scoring</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Async Celery background tasks</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Google Calendar panel integration</span>
                  </li>
                </ul>
              </div>
              <Link href="/login?tab=signup" className="mt-8 w-full py-3.5 text-center rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-bold shadow-lg shadow-orange-600/20 hover:shadow-orange-500/35 transition-all">
                Start 14-Day Free Trial
              </Link>
            </motion.div>

            {/* Enterprise Plan */}
            <motion.div
              whileHover={{ y: -5 }}
              transition={{ duration: 0.2 }}
              className="p-8 rounded-3xl border border-slate-800/80 bg-slate-950/60 flex flex-col justify-between"
            >
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Enterprise</h3>
                <p className="text-slate-400 text-sm mb-6">Custom features and dedicated resources for large firms.</p>
                <div className="flex items-baseline gap-1 text-white mb-8">
                  <span className="text-4xl font-extrabold">Custom</span>
                </div>
                <ul className="space-y-4 text-slate-300 text-sm">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span className="font-semibold text-white">Dedicated AI model instances</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>Custom workflow integrations</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>SLA uptime guarantees & support</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-orange-500" />
                    <span>SSO & custom role-based RBAC</span>
                  </li>
                </ul>
              </div>
              <a href="mailto:sales@antigravity.io" className="mt-8 w-full py-3 text-center rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-white font-semibold transition-all">
                Contact Sales
              </a>
            </motion.div>
          </div>
        </div>
      </section>

      {/* About & FAQ Section */}
      <section id="about" className="py-24 border-t border-slate-900 bg-slate-950/20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
            <div>
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-4"
              >
                <span>About Antigravity Recruit</span>
              </motion.div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-6">Revolutionizing hiring through secure automation</h2>
              <p className="text-slate-400 leading-relaxed mb-6">
                Antigravity Recruit was built with a clear vision: to free recruiters and candidates from administrative bottlenecks. By combining state-of-the-art semantic matching with scalable container workflows, we handle resume parsing, automated assessments, scheduling, and onboarding communication.
              </p>
              <p className="text-slate-400 leading-relaxed mb-8">
                Your data security and system integrity are our core focus. Featuring strict role-based access control (RBAC), decoupled worker architectures, and secure n8n integration pipelines, we protect candidate profile details and company secrets at every stage.
              </p>
              <div className="grid grid-cols-2 gap-6 border-t border-slate-800 pt-8">
                <div>
                  <h4 className="text-2xl font-extrabold text-orange-500">10x</h4>
                  <p className="text-sm text-slate-400 mt-1">Faster time-to-hire metrics</p>
                </div>
                <div>
                  <h4 className="text-2xl font-extrabold text-blue-400">92%</h4>
                  <p className="text-sm text-slate-400 mt-1">Candidate satisfaction rate</p>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-2xl font-extrabold text-white mb-8">Frequently Asked Questions</h3>
              <div className="space-y-6">
                {[
                  { q: "How does the AI semantic ranking work?", a: "Instead of relying on simple keyword matching, our model uses deep sentence embeddings to understand candidate experience and skill sets in context, scoring similarity directly against your job descriptions." },
                  { q: "Can we integrate with our existing calendar systems?", a: "Yes. Antigravity integrates with Google Calendar and Outlook to automatically cross-match availability blocks and generate customized slots for candidate panels." },
                  { q: "Are candidate resumes kept private?", a: "Absolutely. All resume parsing and similarity computations run within isolated environments. Our granular RBAC structure ensures candidate data remains strictly confidential." },
                  { q: "How are background scoring jobs handled?", a: "We leverage a robust FastAPI backend coupled with Celery and Redis to handle screening and background processing asynchronously, ensuring the main user interface remains smooth and responsive." }
                ].map((faq, i) => (
                  <div key={i} className="border-b border-slate-800 pb-6">
                    <h4 className="font-bold text-white text-base mb-2">{faq.q}</h4>
                    <p className="text-slate-400 text-sm leading-relaxed">{faq.a}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-12 text-slate-500 text-sm">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-bold text-white">
            <span className="w-6 h-6 rounded bg-orange-600 flex items-center justify-center font-extrabold text-sm">A</span>
            <span>Antigravity Recruit</span>
          </div>
          <p suppressHydrationWarning>© {new Date().getFullYear()} Antigravity Systems Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
