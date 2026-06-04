import React, { useState, useRef, useCallback } from 'react';
import {
  Upload, FileText, X, Check, Search, FileUp, Loader2, Sparkles,
  Calendar, Users, Zap, ChevronRight, TrendingUp, Clock,
  Brain, LayoutDashboard, Home, Settings, Bell, ChevronDown, Lock,
  ChevronLeft, Menu
} from 'lucide-react';
import { extractTextFromJD, generateJD, getNotifications, markNotificationRead } from '../api';
import { useAuth } from '../context/AuthContext';
import { ProtectedRoute, ShowIfPermission, ShowIfRole, HideIfRole } from './ProtectedRoute';
import InterviewStatus from './InterviewStatus';
import SettingsPage from './Settings';

/* --- Score pill -------------------------------------------- */
const ScorePill = ({ score }) => {
  const pct = (score * 100).toFixed(1);
  const great = score >= 0.60, ok = score >= 0.35;
  const barClass = great ? 'progress-bar-fill' : ok ? 'progress-bar-fill-warn' : 'progress-bar-fill-danger';
  const textColor = great ? 'text-green-600' : ok ? 'text-orange-500' : 'text-red-500';
  return (
    <div className="flex items-center gap-3 min-w-[130px]">
      <span className={`text-sm font-bold tabular-nums ${textColor}`}>{pct}%</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

const RankBadge = ({ n }) => {
  const cls = n === 1 ? 'rank-1' : n === 2 ? 'rank-2' : n === 3 ? 'rank-3' : 'rank-n';
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${cls}`}>
      {n <= 3 ? n : `#${n}`}
    </span>
  );
};

/* --- Sidebar ----------------------------------------------- */
const Sidebar = ({ activeTab, onTabChange, user }) => (
  <div className="v2-sidebar">
    {/* Profile Section */}
    <div className="v2-sidebar-profile">
      <div className="avatar">
        {user?.username?.charAt(0)?.toUpperCase() || 'U'}
      </div>
      <div className="v2-sidebar-profile-info mt-2">
        <p className="text-white font-black text-sm tracking-tight">{user?.username || 'User'}</p>
        <p className="text-white/40 text-[10px] uppercase font-black tracking-widest">{user?.role || 'Recruiter'}</p>
      </div>
    </div>

    {/* Nav items */}
    <div className="flex flex-col gap-1">
      {[
        { id: 'screening', icon: Users, label: 'Dashboard' },
        { id: 'interviews', icon: Calendar, label: 'Interviews' },
      ].map((item) => (
        <button
          key={item.id}
          onClick={() => onTabChange(item.id)}
          className={`v2-nav-item ${activeTab === item.id ? 'active' : ''}`}
        >
          <item.icon className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{item.label}</span>
        </button>
      ))}

      {user?.role === 'hr' && (
        <>
          <button className="v2-nav-item" title={collapsed ? 'Overview' : ''}>
            <LayoutDashboard className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">Overview</span>
          </button>
          <button className="v2-nav-item" title={collapsed ? 'Analytics' : ''}>
            <TrendingUp className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">Analytics</span>
          </button>
        </>
      )}
    </div>

    {/* Bottom - Logout style */}
    <div className="mt-auto mb-8">
      <button
        onClick={() => onTabChange('settings')}
        className={`v2-nav-item ${activeTab === 'settings' ? 'active' : '!text-white/30 hover:!text-white'}`}
      >
        <Settings className="w-5 h-5 flex-shrink-0" />
        <span className="text-sm">Settings</span>
      </button>
    </div>
  </div>
);

/* --- Top bar ----------------------------------------------- */
const TopBar = ({ activeTab, onTabChange, user, onLogout, notifications, showNotifs, setShowNotifs }) => (
  <div className="v2-header-full">
    <div className="flex items-center gap-10">
      {/* Search Bar */}
      <div className="hidden md:flex items-center bg-gray-100 rounded-2xl px-5 py-2.5 w-80 border border-gray-200/50">
        <Search className="w-4 h-4 text-gray-400 mr-3" />
        <input
          type="text"
          placeholder="Search candidates..."
          className="bg-transparent border-none outline-none text-sm font-medium w-full text-gray-700 placeholder:text-gray-400"
        />
      </div>
    </div>

    {/* Right side */}
    <div className="ml-auto flex items-center gap-8">
      <div className="hidden lg:block text-gray-400 font-bold text-xs uppercase tracking-widest">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-orange-500" />
          <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}, {new Date().toLocaleDateString([], { month: 'long', day: 'numeric' })}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className={`w-11 h-11 flex items-center justify-center rounded-2xl bg-white border border-gray-100 shadow-sm hover:scale-105 transition-all ${showNotifs ? 'text-blue-600 ring-2 ring-blue-500/10' : 'text-gray-400'}`}
          >
            <Bell className="w-5 h-5" />
            {notifications.some(n => !n.read) && (
              <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-red-500 border-2 border-white rounded-full" />
            )}
          </button>

          {/* Backdrop to close on outside click */}
          {showNotifs && (
            <div 
              className="fixed inset-0 z-[99]" 
              onClick={() => setShowNotifs(false)}
            />
          )}

          {/* Notifications Overlay */}
          {showNotifs && (
            <div 
              className="absolute right-0 top-full mt-4 w-96 bg-white border border-gray-200 !rounded-3xl shadow-2xl z-[100] overflow-hidden animate-fade-in"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                <h3 className="text-sm font-black text-gray-900 tracking-widest uppercase">Notifications</h3>
                <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-lg uppercase tracking-widest">
                  {notifications.filter(n => !n.read).length} New
                </span>
              </div>
              <div className="max-h-[400px] overflow-y-auto">
                {notifications.length > 0 ? (
                  notifications.map((notif) => (
                    <div key={notif.id} className={`p-5 flex gap-4 hover:bg-gray-50 transition-all cursor-pointer border-b border-gray-100 ${!notif.read ? 'bg-blue-50/50' : ''}`}>
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${notif.type === 'alert' ? 'bg-orange-100 text-orange-600' : notif.type === 'success' ? 'bg-emerald-100 text-emerald-600' : 'bg-blue-100 text-blue-600'}`}>
                        {notif.icon || <Bell className="w-5 h-5" />}
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-black text-gray-900 leading-tight">{notif.title}</p>
                        <p className="text-xs text-gray-500 font-medium leading-relaxed">{notif.message}</p>
                        <p className="text-[10px] text-gray-400 font-bold">{notif.time}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-10 text-center space-y-3">
                    <Bell className="w-10 h-10 mx-auto text-gray-200" />
                    <p className="text-sm text-gray-400 font-medium tracking-tight">All caught up!</p>
                  </div>
                )}
              </div>
              <button className="w-full py-4 text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 hover:text-blue-600 bg-gray-50 transition-all">
                View all activity
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3.5 group relative cursor-pointer glass-card !rounded-2xl pl-2 pr-4 py-2 hover:bg-white transition-all shadow-sm">
          <div className="user-avatar !w-9 !h-9 !text-xs !bg-blue-500 border-2 border-white shadow-md">{user?.username?.charAt(0)?.toUpperCase() || 'U'}</div>
          <ChevronDown className="w-4 h-4 text-gray-400 group-hover:text-gray-900 transition-colors" />

          {/* Dropdown menu */}
          <div className="absolute right-0 top-full mt-3 w-56 bg-white border border-gray-200 !rounded-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-gray-100 bg-gray-50/50">
              <p className="text-sm font-black text-gray-900">{user?.username || 'User'}</p>
              <p className="text-xs text-gray-500">{user?.email || ''}</p>
            </div>
            <button
              onClick={() => onTabChange('settings')}
              className="w-full text-left px-5 py-4 text-xs font-black uppercase tracking-widest text-gray-600 hover:bg-gray-50 transition-all border-b border-gray-100"
            >
              Preferences
            </button>
            <button
              onClick={onLogout}
              className="w-full text-left px-5 py-4 text-xs font-black uppercase tracking-widest text-red-500 hover:bg-red-500 hover:text-white transition-all"
            >
              Logout session
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* --- File upload status dot ------------------------------- */
const statusDot = (s) =>
  s === 'success' ? 'bg-green-400' : s === 'error' ? 'bg-red-400' : 'bg-blue-400';

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const runWithConcurrency = async (items, worker, concurrency = 4) => {
  const limit = Math.max(1, Math.min(concurrency, items.length || 1));
  const results = new Array(items.length);
  let nextIndex = 0;

  const runner = async () => {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      results[currentIndex] = await worker(items[currentIndex], currentIndex);
    }
  };

  await Promise.all(Array.from({ length: limit }, () => runner()));
  return results;
};

/* --- Main Component ---------------------------------------- */
const HRScreening = () => {
  const auth = useAuth();
  const [activeTab, setActiveTab] = useState('screening');
  const [resumes, setResumes] = useState([]);
  const [jdMode, setJdMode] = useState('text');
  const [jdText, setJdText] = useState('');
  const [jdAgentInput, setJdAgentInput] = useState({ role: '', exp: '', skills: '' });
  const [isGeneratingJD, setIsGeneratingJD] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [matchResults, setMatchResults] = useState(null);
  const [uploadStatus, setUploadStatus] = useState({});
  const [dragOver, setDragOver] = useState(false);
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const notificationIdRef = useRef(1);
  const resultsRef = useRef(null);

  const loadNotifications = useCallback(async () => {
    try {
      const data = await getNotifications();
      // Format time for display
      const formattedData = data.map(n => {
        const d = new Date(n.created_at);
        return {
          ...n,
          time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
      });
      setNotifications(formattedData);
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    }
  }, []);

  React.useEffect(() => {
    const refreshNotifications = () => {
      if (document.visibilityState === 'visible') {
        loadNotifications();
      }
    };

    refreshNotifications();
    const interval = setInterval(refreshNotifications, 30000);
    document.addEventListener('visibilitychange', refreshNotifications);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', refreshNotifications);
    };
  }, [loadNotifications]);

  const handleMarkAsRead = async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  const addNotification = useCallback((notif) => {
    // This now pushes to backend so it's persistent
    const now = new Date();
    const timeLabel = notif.time || now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setNotifications((prev) => [
      {
        id: Date.now(), // Temp ID
        type: notif.type || 'info',
        title: notif.title,
        message: notif.message,
        time: timeLabel,
        icon: notif.icon,
        read: false,
      },
      ...prev,
    ]);
  }, []);

  const isRecruiter = auth.user?.role === 'recruiter';
  const isHR = auth.user?.role === 'hr';
  const canUploadResumes = isHR || isRecruiter;
  const canRunScreening = isHR || isRecruiter;
  const canWriteJD = isHR || isRecruiter;

  /* --- drag & drop -------- */
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files).filter(f =>
      /\.(pdf|docx|doc)$/i.test(f.name)
    );
    if (files.length) setResumes(prev => [...prev, ...files]);
  }, []);

  const handleResumeUpload = (e) =>
    setResumes(prev => [...prev, ...Array.from(e.target.files)]);

  const removeResume = (i) =>
    setResumes(prev => prev.filter((_, idx) => idx !== i));

  /* --- JD helpers ----------- */
  const handleJDFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      setProcessing(true);
      const data = await extractTextFromJD(file);
      setJdText(data.text);
    } catch { alert('Failed to extract text from JD file.'); }
    finally { setProcessing(false); }
  };

  const handleGenerateJD = async () => {
    setIsGeneratingJD(true);
    try {
      const data = await generateJD(jdAgentInput.role, jdAgentInput.exp, jdAgentInput.skills);
      setJdText(data.jd_text);
      setJdMode('text');
    } catch { alert('Failed to generate JD'); }
    finally { setIsGeneratingJD(false); }
  };

  /* --- Screening ----------- */
  const startScreening = async () => {
    if (!resumes.length) return alert('Please upload resumes first!');
    if (!jdText.trim()) return alert('Please provide a Job Description.');

    const screeningStartedAt = Date.now();
    const minResultsDwellMs = 1200;

    // Non-blocking health check: if n8n is unavailable, fallback to direct batch screening.
    let n8nHealthy = false;
    for (const healthUrl of ['/api/jobs/health', 'http://127.0.0.1:8000/jobs/health']) {
      try {
        const healthRes = await fetch(healthUrl);
        if (!healthRes.ok) continue;
        const health = await healthRes.json();
        if (health.status === 'healthy') {
          n8nHealthy = true;
          break;
        }
      } catch {
        // Try the next health endpoint.
      }
    }
    
    // Last-chance probe from browser context: backend health may fail when
    // backend and n8n use different hostnames across docker/local runs.
    if (!n8nHealthy) {
      try {
        await fetch('http://localhost:5678', { mode: 'no-cors' });
        n8nHealthy = true;
      } catch {
        // Keep unhealthy=false and use backend fallback.
      }
    }

    setProcessing(true);
    setMatchResults(null);

    const USE_TEST_WEBHOOKS = false;
    const N8N_BASE = 'http://localhost:5678';
    const N8N_UPLOAD_URL = '/api/jobs/n8n-proxy';
    const SCREEN_TRIGGER_URL = '/api/jobs/start-screening-proxy';

    let jobId = `JOB-${Date.now()}`;
    try {
      const jdData = {
        title: jdAgentInput.role || 'Job Opening',
        description: jdText,
        required_skills: jdAgentInput.skills || 'Not specified',
        min_experience: 0, max_experience: 0
      };
      const { createJobDescription } = await import('../api');
      const jdRes = await createJobDescription(jdData);
      if (jdRes?.job_id) jobId = jdRes.job_id;
    } catch { /* use timestamp jobId */ }

    if (!n8nHealthy) {
      try {
        addNotification({
          type: 'info',
          title: 'Fallback Screening Mode',
          message: 'Workflow engine is unavailable. Running direct screening from backend.',
        });

        const batchForm = new FormData();
        resumes.forEach(file => batchForm.append('files', file));
        batchForm.append('jobId', jobId);

        const batchRes = await fetch('/api/jobs/batch-screen', {
          method: 'POST',
          body: batchForm,
        });
        if (!batchRes.ok) throw new Error(`Batch screening failed: HTTP ${batchRes.status}`);

        const batchData = await batchRes.json();
        const uiResults = (batchData.candidates || []).map(c => ({
          Name: c.candidate_name || 'Unknown',
          File: c.file_name || 'Processed via Backend',
          ResumeScore: (parseFloat(c.score || 0) * 0.01),
          OAScore: 0,
          Email: c.email || '',
          Phone: c.phone || '',
          Skills: c.skills || '',
          Education: c.summary || '',
          shortlisted: !!c.shortlisted,
        })).sort((a, b) => (b.ResumeScore + b.OAScore) - (a.ResumeScore + a.OAScore));

        if (!uiResults.length) {
          throw new Error('No screening results returned from backend.');
        }

        setUploadStatus(prev => {
          const next = { ...prev };
          resumes.forEach(file => {
            next[file.name] = 'success';
          });
          return next;
        });

        const elapsed = Date.now() - screeningStartedAt;
        if (elapsed < minResultsDwellMs) {
          await sleep(minResultsDwellMs - elapsed);
        }

        setMatchResults(uiResults);
        setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);

        const sl = uiResults.filter(r => r.shortlisted).length;
        addNotification({
          type: 'success',
          title: 'Resume Screening Agent',
          message: `Resume screening completed in fallback mode. ${sl} of ${uiResults.length} shortlisted.`,
          icon: <Sparkles className="w-5 h-5" />,
        });
      } catch (err) {
        addNotification({
          type: 'alert',
          title: 'Screening Error',
          message: `Resume screening failed: ${err.message}`,
        });
        alert(`Screening error: ${err.message}`);
      } finally {
        setProcessing(false);
      }
      return;
    }

    const newStatus = {};
    resumes.forEach(f => (newStatus[f.name] = 'processing'));
    setUploadStatus(prev => ({ ...prev, ...newStatus }));

    const uploadResults = await runWithConcurrency(resumes, async (file) => {
      try {
        const form = new FormData();
        form.append('file', file);
        form.append('jobId', jobId);
        const res = await fetch(N8N_UPLOAD_URL, { method: 'POST', body: form });
        if (res.ok) {
          setUploadStatus(prev => ({ ...prev, [file.name]: 'success' }));
          return { status: 'success', file: file.name };
        }
        throw new Error(res.statusText);
      } catch {
        setUploadStatus(prev => ({ ...prev, [file.name]: 'error' }));
        return { status: 'error', file: file.name };
      }
    }, 4);

    if (uploadResults.every(r => r.status === 'error')) {
      try {
        addNotification({
          type: 'info',
          title: 'Fallback Screening Mode',
          message: 'N8N upload failed for all files. Running direct screening from backend.',
        });

        const batchForm = new FormData();
        resumes.forEach(file => batchForm.append('files', file));
        batchForm.append('jobId', jobId);

        const batchRes = await fetch('/api/jobs/batch-screen', {
          method: 'POST',
          body: batchForm,
        });
        if (!batchRes.ok) throw new Error(`Batch screening failed: HTTP ${batchRes.status}`);

        const batchData = await batchRes.json();
        const fallbackResults = (batchData.candidates || []).map(c => ({
          Name: c.candidate_name || 'Unknown',
          File: c.file_name || 'Processed via Backend',
          ResumeScore: (parseFloat(c.score || 0) * 0.01),
          OAScore: 0,
          Email: c.email || '',
          Phone: c.phone || '',
          Skills: c.skills || '',
          Education: c.summary || '',
          shortlisted: !!c.shortlisted,
        })).sort((a, b) => (b.ResumeScore + b.OAScore) - (a.ResumeScore + a.OAScore));

        if (!fallbackResults.length) {
          throw new Error('No screening results returned from backend fallback.');
        }

        setUploadStatus(prev => {
          const next = { ...prev };
          resumes.forEach(file => {
            next[file.name] = 'success';
          });
          return next;
        });

        const elapsed = Date.now() - screeningStartedAt;
        if (elapsed < minResultsDwellMs) {
          await sleep(minResultsDwellMs - elapsed);
        }

        setMatchResults(fallbackResults);
        setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      } catch (fallbackErr) {
        alert(`❌ All uploads failed. Troubleshooting:\n\n1. Check N8N is running at ${N8N_BASE}\n2. Verify the backend is running on port 8000\n3. Run 'docker compose up -d' to start all services\n\nFallback also failed: ${fallbackErr.message}`);
      } finally {
        setProcessing(false);
      }
      return;
    }

    const successCount = uploadResults.filter(r => r.status === 'success').length;

    // Start polling quickly instead of fixed waiting per resume.
    // This avoids artificial delay and lets UI render partial results as soon as DB rows appear.
    await new Promise(resolve => setTimeout(resolve, 500));

    // Trigger start-screening webhook ONCE through FastAPI to avoid browser CORS.
    try {
      const form = new FormData();
      form.append('jobId', jobId);

      const res = await fetch(SCREEN_TRIGGER_URL, {
        method: 'POST',
        body: form,
      });

      if (res.ok) {
        addNotification({
          type: 'info',
          title: 'Interview Scheduling Agent',
          message: `Interview scheduling agent has started processing shortlisted candidates for job ${jobId}.`,
        });
      }
    } catch {
      // non-critical — interview scheduling will retry via scheduler
    }

    // Poll the FastAPI DB endpoint for results (NOT the n8n webhook).
    // This avoids triggering extra n8n executions on every poll tick.
    const RESULTS_URL = `/api/jobs/results/${jobId}`;
    const pollDeadline = Date.now() + 120000; // 2 min timeout
    let uiResults = [];

    try {
      while (Date.now() < pollDeadline) {
        try {
          const res = await fetch(RESULTS_URL);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);

          const data = await res.json();
          const dataList = data.results || [];

          // Filter out placeholder rows (no name yet — DB write not complete)
          const validRows = dataList.filter(r =>
            r.candidate_name && r.candidate_name !== 'Unknown' && r.candidate_name !== ''
          );

          // De-duplicate by email (keep highest score)
          const distinctMap = new Map();
          validRows.forEach(row => {
            const email = row.email?.toLowerCase();
            if (!email) {
              const key = `no-email-${row.candidate_name}-${row.id}`;
              distinctMap.set(key, row);
              return;
            }
            const rowScore = parseFloat(row.resume_match_score || row.match_score || row.ai_score || 0);
            const existingScore = parseFloat(distinctMap.get(email)?.resume_match_score || distinctMap.get(email)?.match_score || distinctMap.get(email)?.ai_score || 0);
            if (!distinctMap.has(email) || rowScore > existingScore) {
              distinctMap.set(email, row);
            }
          });
          const deDupedRows = Array.from(distinctMap.values());

          if (deDupedRows.length > 0) {
            uiResults = deDupedRows.map(r => ({
              Name: r.candidate_name,
              File: r.file_name || r.resume_url || 'Processed via N8N',
              ResumeScore: (parseFloat(r.resume_match_score || r.match_score || r.ai_score || 0) * (r.resume_match_score || r.match_score ? 0.01 : 1)), // Normalize to 0-1
              OAScore: (parseFloat(r.oa_score || 0) * 0.01), // Normalize to 0-1 (0-100 range)
              Email: r.email || '',
              Phone: r.phone || '',
              Skills: typeof r.skills === 'string' ? r.skills : (Array.isArray(r.skills) ? r.skills.join(', ') : ''),
              Education: r.ai_summary || '',
              shortlisted: (() => {
                const status = String(r.status || r.interview_status || '').trim().toUpperCase();
                const score = parseFloat(r.resume_match_score || r.match_score || r.ai_score || 0);
                return status === 'SHORTLISTED' || score >= 35;
              })()
            })).sort((a, b) => (b.ResumeScore + b.OAScore) - (a.ResumeScore + a.OAScore));

            if (deDupedRows.length >= successCount) break;
          }
          // Not all results ready yet — retry quickly for responsive UI
          await new Promise(resolve => setTimeout(resolve, 1200));
        } catch (fetchErr) {
          // Transient fetch error — short wait and retry
          await new Promise(resolve => setTimeout(resolve, 1200));
        }
      }

      if (!uiResults.length) {
        throw new Error('Screening timed out. Check N8N logs for errors.');
      }

      const elapsed = Date.now() - screeningStartedAt;
      if (elapsed < minResultsDwellMs) {
        await sleep(minResultsDwellMs - elapsed);
      }

      setMatchResults(uiResults);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      const sl = uiResults.filter(r => r.shortlisted).length;

      addNotification({
        type: 'success',
        title: 'Resume Screening Agent',
        message: `Resume screening agent shortlisted ${sl} of ${uiResults.length} candidates.`,
        icon: <Sparkles className="w-5 h-5" />,
      });

      alert(`✅ Screening Complete! ${sl} shortlisted, ${uiResults.length - sl} not shortlisted.`);
    } catch (err) {
      addNotification({
        type: 'alert',
        title: 'Screening Error',
        message: `Resume screening agent encountered an error: ${err.message}`,
      });
      alert(`Screening error: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  /* --- render --------------- */
  if (!auth.isAuthenticated) {
    return (
      <div className="v2-main !ml-0 items-center justify-center p-8 bg-[#f5f7fb]">
        <div className="glass-card !rounded-[2.5rem] p-12 max-w-md text-center space-y-6 shadow-2xl border-white/40">
          <div className="w-20 h-20 mx-auto rounded-3xl bg-orange-500/10 flex items-center justify-center">
            <Lock className="w-10 h-10 text-orange-500" />
          </div>
          <div>
            <h1 className="text-4xl font-black text-gray-900 tracking-tighter mb-2">Access Denied</h1>
            <p className="text-gray-500 font-medium leading-relaxed">This sector is restricted. Please authenticate to access the recruitment engine.</p>
          </div>
          <button
            onClick={() => window.location.href = '/login'}
            className="btn-primary w-full py-4 !rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/30"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }



  return (
    <div className="min-h-screen bg-[#f5f7fb] flex flex-col pt-20">
      <TopBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        user={auth.user}
        onLogout={auth.logout}
        notifications={notifications}
        showNotifs={showNotifs}
        setShowNotifs={setShowNotifs}
      />

      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} user={auth.user} />

        <div className="v2-main overflow-hidden">
          <div className="v2-content-container">
            {/* -- Page header (Show if not settings) -- */}
            {activeTab !== 'settings' && (
              <div className="animate-fade-up mb-12 flex items-center justify-between">
                <div>
                  <h1 className="text-5xl font-black text-gray-900 tracking-tighter mb-2">
                    {activeTab === 'screening' ? 'Recruitment Hub' : 'Pipeline Control'}
                  </h1>
                  <p className="text-base text-gray-400 font-bold uppercase tracking-[0.2em]">
                    {activeTab === 'screening'
                      ? 'AI-POWERED CANDIDATE EVALUATION'
                      : 'INTERVIEW SCHEDULING & TRACKING'}
                  </p>
                </div>


              </div>
            )}

            {/* -- SETTINGS TAB ------------------------------ */}
            {activeTab === 'settings' && (
              <SettingsPage user={auth.user} />
            )}

            {/* -- INTERVIEWS TAB ------------------------------ */}
            {activeTab === 'interviews' && (
              <div className="animate-fade-up">
                <InterviewStatus />
              </div>
            )}

            {/* -- SCREENING TAB ------------------------------- */}
            {activeTab === 'screening' && (
              <>
                {!canUploadResumes && (
                  <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
                    <Lock className="w-5 h-5 text-red-600" />
                    <p className="text-red-700 font-medium">You don't have permission to access the screening tools. Contact your administrator.</p>
                  </div>
                )}

                {canUploadResumes && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                    {/* -- LEFT: Resume Upload -- */}
                    <div className="space-y-5 animate-fade-up" style={{ animationDelay: '.05s' }}>

                      {/* Upload card */}
                      <div className="glass-card p-8 space-y-6 !rounded-[2.5rem] border-white/40 shadow-xl shadow-blue-500/5">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-blue-500 shadow-lg shadow-blue-500/20">
                            <FileUp className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h2 className="text-xl font-black text-gray-900 tracking-tight">Resume Upload</h2>
                            <p className="text-xs text-gray-400 font-bold uppercase tracking-widest">PDF / DOCX / DOC</p>
                          </div>
                          {resumes.length > 0 && (
                            <span className="ml-auto text-[10px] px-3 py-1 rounded-lg font-black uppercase tracking-widest bg-blue-500 text-white shadow-md shadow-blue-500/20">
                              {resumes.length} {resumes.length > 1 ? 'Files' : 'File'}
                            </span>
                          )}
                        </div>

                        {/* Drop zone */}
                        <div
                          className={`relative border-2 border-dashed rounded-[2rem] p-12 text-center cursor-pointer transition-all duration-500 group
                        ${dragOver ? 'border-blue-500 bg-blue-50/50 shadow-inner' : 'border-gray-200/50 hover:border-blue-400/50 hover:bg-white/40'}`}
                          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                          onDragLeave={() => setDragOver(false)}
                          onDrop={handleDrop}
                          onClick={() => document.getElementById('resume-input').click()}
                        >
                          <input id="resume-input" type="file" multiple accept=".pdf,.docx,.doc"
                            onChange={handleResumeUpload} className="hidden" />
                          <div className="pointer-events-none space-y-4">
                            <div className={`w-20 h-20 mx-auto rounded-3xl flex items-center justify-center transition-all duration-500 shadow-sm
                          ${dragOver ? 'bg-blue-500 text-white scale-110' : 'bg-gray-50/50 text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-500'}`}>
                              <Upload className={`w-8 h-8 transition-all duration-500 ${dragOver ? 'animate-bounce' : ''}`} />
                            </div>
                            <div>
                              <p className="text-gray-900 font-black text-lg tracking-tight">
                                {dragOver ? 'Release to process' : 'Drop files or browse'}
                              </p>
                              <p className="text-gray-400 text-[10px] font-bold uppercase tracking-widest mt-1">Maximum 50MB per file</p>
                            </div>
                          </div>
                        </div>

                        {/* File list */}
                        {resumes.length > 0 && (
                          <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                            {resumes.map((file, idx) => (
                              <div key={idx}
                                className="group flex items-center gap-3 p-3 rounded-xl bg-gray-50 border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all">
                                <div className="relative flex-shrink-0">
                                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                                    <FileText className="w-4 h-4 text-blue-500" />
                                  </div>
                                  <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${statusDot(uploadStatus[file.name])}`} />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm text-gray-800 truncate font-medium">{file.name}</p>
                                  <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
                                </div>
                                <button
                                  onClick={(e) => { e.stopPropagation(); removeResume(idx); }}
                                  className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-all"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Action card */}
                      <div className="glass-card p-8 space-y-6 !rounded-[2.5rem] border-white/40 shadow-xl">
                        <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.2em]">
                          <div className="flex items-center gap-2 text-blue-500">
                            <TrendingUp className="w-3 h-3" />
                            <span>{resumes.length} Ready</span>
                          </div>
                          <span className="text-gray-300">|</span>
                          <div className={`flex items-center gap-2 ${jdText.trim() ? 'text-green-500' : 'text-orange-500'}`}>
                            {jdText.trim() ? <Check className="w-3 h-3" /> : <Loader2 className="w-3 h-3 animate-spin" />}
                            <span>{jdText.trim() ? 'JD Verified' : 'JD Requested'}</span>
                          </div>
                        </div>

                        <button
                          onClick={startScreening}
                          disabled={!canRunScreening || processing || resumes.length === 0 || !jdText}
                          className="btn-primary w-full py-5 !rounded-2xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-3 shadow-2xl shadow-blue-500/40 hover:scale-[1.02] active:scale-95 transition-all"
                        >
                          {!canRunScreening ? (
                            <><Lock className="w-4 h-4" /><span>Access Restricted</span></>
                          ) : processing ? (
                            <><Loader2 className="w-4 h-4 animate-spin" /><span>Processing Engine...</span></>
                          ) : (
                            <><Zap className="w-4 h-4 fill-white" /><span>Start AI Analysis</span><ChevronRight className="w-4 h-4 opacity-50" /></>
                          )}
                        </button>

                        {processing && (
                          <div className="space-y-2 text-xs text-gray-400">
                            {['Uploading resumes to pipeline', 'Extracting candidate signals', 'Running AI match engine'].map((s, i) => (
                              <div key={i} className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" style={{ animationDelay: `${i * 200}ms` }} />
                                {s}
                              </div>
                            ))}
                          </div>
                        )}

                        {matchResults && !processing && (
                          <div className="flex items-center gap-2 text-sm text-green-700 px-4 py-2.5 rounded-xl bg-green-50 border border-green-100 animate-fade-up">
                            <Check className="w-4 h-4 flex-shrink-0 text-green-500" />
                            Screening complete � {matchResults.filter(r => r.shortlisted).length} shortlisted of {matchResults.length}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* -- RIGHT: Job Description -- */}
                    <div className="glass-card p-8 flex flex-col gap-6 animate-fade-up !rounded-[2.5rem] border-white/40 shadow-xl shadow-orange-500/5 transition-all" style={{ animationDelay: '.1s' }}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-orange-500 shadow-lg shadow-orange-500/20">
                            <FileText className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h2 className="text-xl font-black text-gray-900 tracking-tight">Job Spec</h2>
                            <p className="text-xs text-gray-400 font-bold uppercase tracking-widest">Requirements Engine</p>
                          </div>
                        </div>

                        {/* Mode switcher */}
                        <div className="flex gap-1 p-1 pr-1.5 glass-container !rounded-xl">
                          {[
                            { id: 'text', label: 'Write' },
                            { id: 'file', label: 'Upload' },
                            { id: 'agent', label: 'AI' },
                          ].map(({ id, label }) => (
                            <button
                              key={id}
                              onClick={() => canWriteJD && setJdMode(id)}
                              disabled={!canWriteJD}
                              className={`px-5 py-2 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all duration-300 ${!canWriteJD ? 'opacity-50 cursor-not-allowed' : ''
                                }
                            ${jdMode === id
                                  ? 'glass-card !bg-white text-gray-900 shadow-sm'
                                  : 'text-gray-500 hover:text-gray-900 hover:bg-white/40'
                                }`}
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {jdMode === 'text' && (
                        <textarea
                          className="input-premium flex-1 p-4 resize-none text-sm leading-relaxed min-h-[280px]"
                          placeholder={`Paste or type the full job description here\n\nInclude: role, responsibilities, required skills, experience`}
                          value={jdText}
                          onChange={(e) => setJdText(e.target.value)}
                        />
                      )}

                      {jdMode === 'file' && (
                        <div className="flex-1 flex flex-col items-center justify-center min-h-[280px] border-2 border-dashed border-gray-200 rounded-xl hover:border-orange-300 hover:bg-orange-50/30 transition-all cursor-pointer relative group">
                          <input type="file" accept=".pdf,.docx,.doc" onChange={handleJDFileUpload}
                            className="absolute inset-0 opacity-0 cursor-pointer z-10" />
                          <div className="text-center space-y-3">
                            <div className="w-12 h-12 mx-auto rounded-xl bg-gray-50 flex items-center justify-center group-hover:bg-orange-50 transition-all">
                              <Upload className="w-6 h-6 text-gray-400 group-hover:text-orange-400 transition-colors" />
                            </div>
                            <p className="text-gray-700 font-medium">Upload JD document</p>
                            <p className="text-gray-400 text-xs">PDF or DOCX or text extracted automatically</p>
                            <button
                              onClick={(e) => { e.preventDefault(); document.querySelector('input[accept*="pdf"]')?.click?.(); }}
                              className="mt-4 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition-all"
                            >
                              Choose File
                            </button>
                          </div>
                        </div>
                      )}

                      {jdMode === 'agent' && (
                        <div className="flex-1 flex flex-col gap-3 min-h-[280px]">
                          <input type="text" placeholder="Role title  (e.g. Senior Python Developer)"
                            className="input-premium p-3 text-sm"
                            value={jdAgentInput.role}
                            onChange={(e) => setJdAgentInput({ ...jdAgentInput, role: e.target.value })} />
                          <input type="text" placeholder="Experience required  (e.g. 5+ years)"
                            className="input-premium p-3 text-sm"
                            value={jdAgentInput.exp}
                            onChange={(e) => setJdAgentInput({ ...jdAgentInput, exp: e.target.value })} />
                          <textarea placeholder="Key skills  (e.g. FastAPI, AWS, PostgreSQL, Docker)"
                            className="input-premium flex-1 p-3 text-sm resize-none"
                            value={jdAgentInput.skills}
                            onChange={(e) => setJdAgentInput({ ...jdAgentInput, skills: e.target.value })} />
                          <button onClick={handleGenerateJD} disabled={isGeneratingJD}
                            className="btn-orange py-3 flex items-center justify-center gap-2 text-sm w-full">
                            {isGeneratingJD
                              ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating</>
                              : <><Sparkles className="w-4 h-4" /> Generate Job Description</>
                            }
                          </button>
                        </div>
                      )}

                      {jdText && (
                        <div className="flex items-center gap-2 text-xs font-medium px-3 py-2 rounded-xl section-chip-green section-chip">
                          <Check className="w-3.5 h-3.5" />
                          {jdText.split(/\s+/).length} words loaded
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* -- RESULTS TABLE -- */}
                {matchResults && (
                  <div ref={resultsRef} className="glass-card overflow-hidden animate-fade-up mt-10 !rounded-[2.5rem] border-white/40 shadow-2xl transition-all"
                    style={{ animationDelay: '.05s' }}>

                    {/* Table header */}
                    <div className="px-8 py-8 border-b border-white/20 flex items-center justify-between flex-wrap gap-4 bg-white/10">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-blue-500 shadow-lg shadow-blue-500/20 flex items-center justify-center">
                          <LayoutDashboard className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <h2 className="text-2xl font-black text-gray-900 tracking-tighter">Candidate Analysis</h2>
                          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{matchResults.length} Evaluated Engineers</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="glass-card !bg-green-500 text-white border-none px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-green-500/20">
                          {matchResults.filter(r => r.shortlisted).length} Shortlisted
                        </span>
                        <span className="glass-card !bg-gray-400 text-white border-none px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-md shadow-gray-400/20">
                          {matchResults.filter(r => !r.shortlisted).length} Rejected
                        </span>
                      </div>
                    </div>

                    {matchResults.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                          <thead>
                            <tr className="text-[10px] uppercase font-black tracking-[0.15em] text-gray-400 bg-white/5 border-b border-white/10">
                              {['Rank', 'Candidate details', 'AI Verdict', 'Resume Score', 'Contact', 'Skills'].map(h => (
                                <th key={h} className="px-8 py-5 whitespace-nowrap">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {matchResults.map((c, idx) => (
                              <tr key={idx}
                                className={`table-row-premium ${c.shortlisted ? 'table-row-shortlisted' : ''}`}>
                                <td className="px-5 py-4"><RankBadge n={idx + 1} /></td>
                                <td className="px-8 py-6">
                                  <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 font-black text-white text-base shadow-sm"
                                      style={{ background: c.shortlisted ? '#0c87ff' : '#6b7280' }}>
                                      {c.Name.charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                      <p className="font-black text-gray-900 text-base leading-none tracking-tight mb-1">{c.Name}</p>
                                      <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest truncate max-w-[150px]">{c.File}</p>
                                    </div>
                                  </div>
                                </td>
                                <td className="px-8 py-6">
                                  {c.shortlisted ? (
                                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-green-500/10 text-green-600 text-[10px] font-black uppercase tracking-widest border border-green-500/20">
                                      <Check className="w-3 h-3" /> Selected
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-gray-500/10 text-gray-500 text-[10px] font-black uppercase tracking-widest border border-gray-500/20">
                                      <X className="w-3 h-3" /> Declined
                                    </span>
                                  )}
                                </td>
                                <td className="px-8 py-6"><ScorePill score={c.ResumeScore} /></td>
                                <td className="px-5 py-4 space-y-1">
                                  {c.Email && (
                                    <a href={`mailto:${c.Email}`}
                                      className="block text-xs text-blue-500 hover:text-blue-600 hover:underline truncate max-w-[160px]">
                                      {c.Email}
                                    </a>
                                  )}
                                  {c.Phone && <p className="text-xs text-gray-500">{c.Phone}</p>}
                                  {!c.Email && !c.Phone && <span className="text-xs text-gray-300">�</span>}
                                </td>
                                <td className="px-8 py-6">
                                  <div className="flex flex-wrap gap-2">
                                    {c.Skills
                                      ? c.Skills.split(',').slice(0, 3).map((sk, si) => (
                                        <span key={si} className="px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest bg-white/60 border border-white/40 text-gray-600 shadow-sm">
                                          {sk.trim()}
                                        </span>
                                      ))
                                      : <span className="text-xs text-gray-300"></span>
                                    }
                                    {c.Skills && c.Skills.split(',').length > 3 && (
                                      <span className="px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest bg-blue-500 text-white shadow-md shadow-blue-500/20">
                                        +{c.Skills.split(',').length - 3}
                                      </span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="py-16 text-center space-y-3">
                        <Search className="w-12 h-12 mx-auto text-gray-300" />
                        <p className="text-gray-500 font-medium">No candidates found</p>
                        <p className="text-gray-400 text-sm">Check N8N workflow logs and try again.</p>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HRScreening;
