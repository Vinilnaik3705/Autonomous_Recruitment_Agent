import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
    CheckCircle, Clock, AlertCircle, Calendar, Video,
    FileText, Download, LogOut, User, Briefcase, Mail,
    Phone, RefreshCw, ChevronRight, ExternalLink, RotateCcw, Settings as SettingsIcon
} from 'lucide-react';
import SettingsPage from './Settings';

// ─── Status config ────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
    APPLIED: { label: 'Applied', color: 'blue', badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
    SCREENED: { label: 'Screened', color: 'purple', badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30' },
    SHORTLISTED: { label: 'Shortlisted ✨', color: 'green', badge: 'bg-green-500/20 text-green-300 border-green-500/30' },
    INTERVIEW_SCHEDULED: { label: 'Interview Scheduled', color: 'orange', badge: 'bg-orange-500/20 text-orange-300 border-orange-500/30' },
    SCHEDULED: { label: 'Interview Scheduled', color: 'orange', badge: 'bg-orange-500/20 text-orange-300 border-orange-500/30' },
    FEEDBACK_REQUESTED: { label: 'Under Review', color: 'yellow', badge: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
    FEEDBACK_SUBMITTED: { label: 'Under Review', color: 'yellow', badge: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
    NEXT_ROUND: { label: 'Advanced to Next Round 🎉', color: 'green', badge: 'bg-green-500/20 text-green-300 border-green-500/30' },
    HIRED: { label: 'Offer Extended 🎊', color: 'green', badge: 'bg-green-500/20 text-green-300 border-green-500/30' },
    ONBOARDING_INITIATED: { label: 'Onboarding', color: 'teal', badge: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
    REJECTED: { label: 'Not Selected', color: 'red', badge: 'bg-red-500/20 text-red-300 border-red-500/30' },
};

const getStatusConfig = (s) => STATUS_CONFIG[s] || STATUS_CONFIG['APPLIED'];

// ─── Timeline step icons ──────────────────────────────────────────────────────
function TimelineStep({ step, isLast }) {
    const isDone = step.state === 'completed';
    const isCurrent = step.state === 'current';

    return (
        <div className="flex flex-col items-center" style={{ flex: 1 }}>
            {/* Circle */}
            <div className={`
        w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all
        ${isDone ? 'bg-green-500 border-green-400 text-white shadow-lg shadow-green-500/30' : ''}
        ${isCurrent ? 'bg-orange-500 border-orange-400 text-white shadow-lg shadow-orange-500/30 ring-4 ring-orange-500/20' : ''}
        ${!isDone && !isCurrent ? 'bg-gray-800 border-gray-600 text-gray-500' : ''}
      `}>
                {isDone ? <CheckCircle className="w-4 h-4" /> : isCurrent ? <Clock className="w-4 h-4" /> : ''}
            </div>

            {/* Connector line */}
            {!isLast && (
                <div className="absolute" style={{ display: 'none' }} />
            )}

            {/* Label */}
            <p className={`mt-2 text-xs text-center leading-tight ${isDone ? 'text-green-400' : isCurrent ? 'text-orange-400 font-semibold' : 'text-gray-600'
                }`}>
                {step.label}
            </p>
        </div>
    );
}

function Timeline({ steps }) {
    return (
        <div className="relative">
            {/* Background connector */}
            <div className="absolute top-4 left-4 right-4 h-0.5 bg-gray-700" style={{ marginLeft: '2rem', marginRight: '2rem' }} />

            {/* Filled connector */}
            <div
                className="absolute top-4 h-0.5 bg-gradient-to-r from-green-500 to-orange-500 transition-all duration-700"
                style={{
                    left: '2rem',
                    width: `calc((100% - 4rem) * ${Math.max(0, steps.filter(s => s.state === 'completed').length) / Math.max(1, steps.length - 1)})`
                }}
            />

            <div className="relative flex justify-between">
                {steps.map((step, i) => (
                    <TimelineStep key={step.stage} step={step} isLast={i === steps.length - 1} />
                ))}
            </div>
        </div>
    );
}

// ─── Status card ──────────────────────────────────────────────────────────────
function ApplicationStatusCard({ application }) {
    const cfg = getStatusConfig(application.status);
    const isRejected = application.status === 'REJECTED';

    return (
        <div className="rounded-2xl border border-gray-700/50 bg-gray-800/60 backdrop-blur-sm p-6 space-y-4">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center">
                    <Briefcase className="w-5 h-5 text-orange-400" />
                </div>
                <h2 className="text-lg font-semibold text-white">Your Application</h2>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Position</p>
                    <p className="text-white font-medium">{application.job_title || 'Open Role'}</p>
                </div>
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Status</p>
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${cfg.badge}`}>
                        ● {cfg.label}
                    </span>
                </div>
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Applied</p>
                    <p className="text-gray-300 text-sm">
                        {application.applied_at
                            ? new Date(application.applied_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
                            : '—'}
                    </p>
                </div>
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Contact</p>
                    <p className="text-gray-300 text-sm">{application.phone || '—'}</p>
                </div>
            </div>

            {/* Skills */}
            {application.skills && (
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Skills on File</p>
                    <div className="flex flex-wrap gap-2">
                        {String(application.skills).split(',').slice(0, 8).map((sk, i) => (
                            <span key={i} className="px-2 py-0.5 rounded-md bg-gray-700/60 text-gray-300 text-xs border border-gray-600/50">
                                {sk.trim()}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Rejection message */}
            {isRejected && (
                <div className="mt-4 p-4 rounded-xl bg-red-900/20 border border-red-700/40 space-y-2">
                    <p className="text-red-300 font-medium">Thank you for applying</p>
                    <p className="text-gray-400 text-sm">
                        After careful consideration, we've moved forward with other candidates for this role.
                        We appreciate the time you invested in our process and encourage you to apply again
                        for future openings that match your skills.
                    </p>
                    <a
                        href="/"
                        className="inline-flex items-center gap-2 mt-2 text-sm text-orange-400 hover:text-orange-300 transition-colors"
                    >
                        <RotateCcw className="w-4 h-4" /> View open positions
                    </a>
                </div>
            )}
        </div>
    );
}

// ─── Interview card ───────────────────────────────────────────────────────────
function InterviewCard({ interview }) {
    if (!interview) return null;

    const date = interview.scheduled_time ? new Date(interview.scheduled_time) : null;
    const isUpcoming = date && date > new Date();

    const addToCalendarUrl = date
        ? `https://calendar.google.com/calendar/render?action=TEMPLATE&text=Interview&dates=${date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z'
        }`
        : null;

    return (
        <div className={`rounded-2xl border p-6 space-y-4 ${isUpcoming
            ? 'bg-gradient-to-br from-orange-500/10 to-orange-600/5 border-orange-500/30'
            : 'bg-gray-800/60 border-gray-700/50'
            } backdrop-blur-sm`}>
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-orange-500/15 flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                    <h2 className="text-lg font-semibold text-white">
                        {isUpcoming ? 'Upcoming Interview' : 'Interview Details'}
                    </h2>
                    {isUpcoming && (
                        <p className="text-xs text-orange-400">Scheduled</p>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Date & Time</p>
                    <p className="text-white font-medium">
                        {date
                            ? date.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'long' })
                            : '—'}
                    </p>
                    <p className="text-gray-400 text-sm">
                        {date ? date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : ''}
                    </p>
                </div>
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Interviewer</p>
                    <p className="text-white font-medium">{interview.interviewer_name || 'HR Team'}</p>
                    <p className="text-gray-400 text-sm">Round 1</p>
                </div>
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Format</p>
                    <div className="flex items-center gap-2 text-gray-300">
                        <Video className="w-4 h-4 text-blue-400" />
                        <span className="text-sm">Video Call</span>
                    </div>
                </div>
                <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Status</p>
                    <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/20 text-orange-300 border border-orange-500/30">
                        {interview.status || 'Scheduled'}
                    </span>
                </div>
            </div>

            <div className="flex gap-3 pt-2">
                {interview.google_event_id && (
                    <a
                        href={`https://calendar.google.com/calendar/event?eid=${interview.google_event_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
                    >
                        <Video className="w-4 h-4" />
                        Join Meeting
                    </a>
                )}
                {addToCalendarUrl && (
                    <a
                        href={addToCalendarUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium transition-colors border border-gray-600"
                    >
                        <Calendar className="w-4 h-4" />
                        Add to Calendar
                    </a>
                )}
            </div>
        </div>
    );
}

// ─── Documents card ───────────────────────────────────────────────────────────
function DocumentsCard({ resumeUrl, candidateName }) {
    return (
        <div className="rounded-2xl border border-gray-700/50 bg-gray-800/60 backdrop-blur-sm p-6 space-y-4">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-blue-400" />
                </div>
                <h2 className="text-lg font-semibold text-white">Documents</h2>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-gray-700/50 border border-gray-600/50">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center">
                        <FileText className="w-4 h-4 text-red-400" />
                    </div>
                    <div>
                        <p className="text-sm text-white font-medium">Submitted Resume</p>
                        <p className="text-xs text-gray-500">{candidateName}</p>
                    </div>
                </div>
                {resumeUrl ? (
                    <a
                        href={resumeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-sm text-orange-400 hover:text-orange-300 transition-colors"
                    >
                        <Download className="w-4 h-4" />
                        View
                    </a>
                ) : (
                    <span className="text-xs text-gray-600">Not available</span>
                )}
            </div>
        </div>
    );
}

// ─── Under review card ────────────────────────────────────────────────────────
function UnderReviewBanner() {
    return (
        <div className="rounded-2xl border border-yellow-700/40 bg-yellow-500/10 p-5 flex items-start gap-4">
            <Clock className="w-6 h-6 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
                <p className="text-yellow-300 font-semibold mb-1">Your interview is under review</p>
                <p className="text-gray-400 text-sm">
                    Our hiring team is evaluating the interview. You'll receive an email once a decision has been made.
                    This typically takes 3–5 business days.
                </p>
            </div>
        </div>
    );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function CandidatePortal() {
    const { user, token, logout } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('portal'); // 'portal' or 'settings'

    const fetchStatus = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/candidate/my-status', {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Failed to load status' }));
                throw new Error(err.detail || 'Failed to load');
            }
            setData(await res.json());
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchStatus(); }, []);

    const isUnderReview = data?.application?.status &&
        ['FEEDBACK_REQUESTED', 'FEEDBACK_SUBMITTED'].includes(data.application.status);

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-white">
            {/* Header */}
            <header className="border-b border-gray-800/80 bg-gray-900/60 backdrop-blur-md sticky top-0 z-10">
                <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center">
                            <span className="text-sm font-bold text-white">T</span>
                        </div>
                        <div>
                            <p className="font-semibold text-white leading-none">Talent Hub</p>
                            <p className="text-xs text-gray-500">Candidate Portal</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <User className="w-4 h-4" />
                            <span>{user?.username}</span>
                        </div>
                        <button
                            onClick={() => setActiveTab('settings')}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${activeTab === 'settings' ? 'bg-orange-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700/60'}`}
                        >
                            <SettingsIcon className="w-4 h-4" />
                            Settings
                        </button>
                        <button
                            onClick={logout}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-700/60 transition-all"
                        >
                            <LogOut className="w-4 h-4" />
                            Logout
                        </button>
                    </div>
                </div>
            </header>

            {/* Content */}
            <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">

                {activeTab === 'settings' ? (
                    <div className="animate-fade-up">
                        <div className="flex items-center gap-3 mb-8">
                            <button
                                onClick={() => setActiveTab('portal')}
                                className="p-2 hover:bg-gray-800 rounded-xl transition-all"
                            >
                                <TimelineStep step={{ state: 'completed', label: '' }} isLast={true} /> {/* Circular back button style */}
                            </button>
                            <h1 className="text-2xl font-bold">Account Settings</h1>
                        </div>
                        <SettingsPage user={user} />
                    </div>
                ) : (
                    <>
                        {/* Page title */}
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-2xl font-bold text-white">
                                    Hi, {data?.application?.candidate_name?.split(' ')[0] || user?.username} 👋
                                </h1>
                                <p className="text-gray-400 text-sm mt-1">Track your application progress below</p>
                            </div>
                            <button
                                onClick={fetchStatus}
                                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-700/60 transition-all border border-gray-700"
                            >
                                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                                Refresh
                            </button>
                        </div>

                        {/* Loading state */}
                        {loading && (
                            <div className="flex items-center justify-center py-20">
                                <div className="flex flex-col items-center gap-3">
                                    <div className="w-10 h-10 border-2 border-orange-500/40 border-t-orange-400 rounded-full animate-spin" />
                                    <p className="text-gray-500 text-sm">Loading your application...</p>
                                </div>
                            </div>
                        )}

                        {/* Error state */}
                        {error && !loading && (
                            <div className="flex items-start gap-3 p-5 rounded-2xl bg-red-900/20 border border-red-700/40">
                                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                                <div>
                                    <p className="text-red-300 font-medium">Could not load your application</p>
                                    <p className="text-gray-400 text-sm mt-1">{error}</p>
                                </div>
                            </div>
                        )}

                        {/* No application found */}
                        {!loading && !error && data && !data.found && (
                            <div className="text-center py-16 space-y-4">
                                <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
                                    <Briefcase className="w-8 h-8 text-gray-600" />
                                </div>
                                <div>
                                    <p className="text-white font-semibold text-lg">No application found</p>
                                    <p className="text-gray-400 text-sm mt-1">
                                        We couldn't find an application linked to <strong className="text-gray-300">{data.email}</strong>.
                                    </p>
                                    <p className="text-gray-500 text-sm mt-1">
                                        Make sure you registered with the same email you used to submit your resume.
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Main content */}
                        {!loading && !error && data?.found && (
                            <>
                                {/* Timeline */}
                                <div className="rounded-2xl border border-gray-700/50 bg-gray-800/60 backdrop-blur-sm p-6">
                                    <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-6">Application Timeline</h2>
                                    <Timeline steps={data.timeline} />
                                </div>

                                {/* Status card */}
                                <ApplicationStatusCard application={data.application} />

                                {/* Under review banner */}
                                {isUnderReview && <UnderReviewBanner />}

                                {/* Interview card */}
                                {data.interview && <InterviewCard interview={data.interview} />}

                                {/* Documents */}
                                <DocumentsCard
                                    resumeUrl={data.application.resume_url}
                                    candidateName={data.application.candidate_name}
                                />

                                {/* Footer note */}
                                <p className="text-center text-gray-600 text-xs pb-4">
                                    Questions? Contact us at{' '}
                                    <a href="mailto:workspace3705@gmail.com" className="text-orange-500/70 hover:text-orange-400 transition-colors">
                                        workspace3705@gmail.com
                                    </a>
                                </p>
                            </>
                        )}
                    </>
                )}
            </main>
        </div>
    );
}
