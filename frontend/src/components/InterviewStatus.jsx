import React, { useState, useEffect } from 'react';
import {
  Calendar, CheckCircle, Clock, XCircle, User, Mail,
  Star, MessageSquare, RefreshCw, TrendingUp, Award,
  AlertCircle, Zap, Radio, ClipboardCheck, Rocket, Settings as SettingsIcon, ChevronLeft
} from 'lucide-react';
import { getInterviewStatus, clearAllInterviews } from '../api';
import SettingsPage from './Settings';

/* --- Stat card --- */
const StatCard = ({ label, value, icon: Icon, accent }) => (
  <div className="bg-white border border-gray-100 rounded-[1.5rem] p-6 shadow-sm hover:shadow-md transition-all">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2">{label}</p>
        <p className="text-4xl font-black text-gray-900 tracking-tighter">{value}</p>
      </div>
      <div
        className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg"
        style={{ background: accent, boxShadow: `0 8px 16px -4px ${accent}40` }}
      >
        <Icon className="w-6 h-6 text-white" />
      </div>
    </div>
  </div>
);

/* --- Status badge --- */
const StatusBadge = ({ status, feedbackSubmitted }) => {
  if (feedbackSubmitted)
    return (
      <span className="badge-feedback inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold">
        <CheckCircle className="w-3 h-3" /> Reviewed
      </span>
    );
  if (status === 'completed')
    return (
      <span className="badge-completed inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold">
        <Clock className="w-3 h-3" /> Pending Feedback
      </span>
    );
  if (status === 'in_progress')
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 border border-blue-200 text-blue-600">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse inline-block" />
        In Progress
      </span>
    );
  if (status === 'scheduled')
    return (
      <span className="badge-scheduled inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold">
        <Calendar className="w-3 h-3" /> Scheduled
      </span>
    );
  if (status === 'cancelled')
    return (
      <span className="badge-cancelled inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold">
        <XCircle className="w-3 h-3" /> Cancelled
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 border border-gray-200 text-gray-500">
      {status}
    </span>
  );
};

/* --- Section header --- */
const SectionHeader = ({ icon: Icon, label, count, accent }) => (
  <div className="flex items-center gap-4 px-8 py-8 border-b border-white/20 bg-white/5">
    <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md" style={{ background: accent }}>
      <Icon className="w-5 h-5 text-white" />
    </div>
    <h3 className="font-black text-gray-900 text-base uppercase tracking-tight">{label}</h3>
    <span className="ml-auto text-[10px] px-3 py-1 rounded-lg font-black uppercase tracking-widest shadow-sm"
      style={{ background: 'white', color: accent, border: `1px solid ${accent}40` }}>
      {count} Active
    </span>
  </div>
);

/* --- Table head --- */
const THead = ({ columns }) => (
  <thead>
    <tr className="text-[10px] uppercase font-black tracking-[0.15em] text-gray-400 bg-white/5 border-b border-white/10">
      {columns.map(c => (
        <th key={c} className="px-8 py-5 whitespace-nowrap text-left">{c}</th>
      ))}
      <th className="px-8 py-5 text-right whitespace-nowrap">Actions</th>
    </tr>
  </thead>
);

/* --- Avatar --- */
const Avatar = ({ name, color }) => (
  <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-white text-xs font-bold"
    style={{ background: color || '#0c87ff' }}>
    {(name || '?').charAt(0).toUpperCase()}
  </div>
);

/* --- Star rating --- */
const StarRating = ({ rating }) => {
  if (!rating) return <span className="text-xs text-gray-300">-</span>;
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <Star key={i} className={`w-3.5 h-3.5 ${i <= rating ? 'fill-orange-400 text-orange-400' : 'text-gray-200'}`} />
      ))}
      <span className="text-xs text-orange-500 font-semibold ml-1.5">{rating}/5</span>
    </div>
  );
};

/* --- Recommendation pill --- */
const RecoPill = ({ rec }) => {
  if (!rec) return <span className="text-xs text-gray-300">-</span>;
  const map = {
    HIRE: { cls: 'badge-shortlisted', icon: CheckCircle },
    REJECT: { cls: 'badge-rejected', icon: XCircle },
    HOLD: { cls: 'badge-scheduled', icon: Clock },
    MAYBE: { cls: 'badge-scheduled', icon: AlertCircle },
  };
  const { cls, icon: Icon } = map[rec] || { cls: 'bg-gray-100 border border-gray-200 text-gray-500', icon: null };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      {Icon && <Icon className="w-3 h-3" />}
      {rec}
    </span>
  );
};

/* --- Main Component --- */
const InterviewStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const [clearing, setClearing] = useState(false);
  const [activeTab, setActiveTab] = useState('interviews'); // 'interviews' or 'settings'

  const clearInterviews = async () => {
    if (!window.confirm('Remove all interview records? This cannot be undone.')) return;
    setClearing(true);
    try {
      await clearAllInterviews();
      await fetchStatus(true);
    } catch (err) {
      alert('Failed to clear: ' + err.message);
    } finally {
      setClearing(false);
    }
  };

  const fetchStatus = async (forceFresh = false) => {
    try {
      setLoading(true);
      const data = await getInterviewStatus(forceFresh);
      setStatus(data);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus(true);
    const interval = setInterval(() => fetchStatus(true), 30000);
    return () => clearInterval(interval);
  }, []);

  const formatDate = (ds) => {
    if (!ds) return '-';
    return new Date(ds).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  if (loading && !status) {
    return (
      <div className="card p-12 flex flex-col items-center justify-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center">
          <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
        </div>
        <p className="text-gray-400 text-sm">Loading interview data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-8 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center flex-shrink-0">
          <XCircle className="w-5 h-5 text-red-400" />
        </div>
        <div>
          <p className="font-semibold text-red-500 text-sm">Failed to load interviews</p>
          <p className="text-gray-400 text-xs mt-0.5">{error}</p>
        </div>
        <button onClick={fetchStatus} className="ml-auto btn-primary px-4 py-2 text-xs">Retry</button>
      </div>
    );
  }

  if (!status || status.total_interviews === 0) {
    return (
      <div className="card p-14 flex flex-col items-center justify-center text-center space-y-5">
        <div className="w-20 h-20 rounded-3xl bg-blue-50 flex items-center justify-center">
          <Calendar className="w-10 h-10 text-blue-400 animate-float" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">No Interviews Yet</h3>
          <p className="text-gray-400 text-sm max-w-xs">
            Shortlist candidates from the Screening tab to automatically schedule interviews.
          </p>
        </div>
        <div className="section-chip section-chip-blue">
          <Zap className="w-3.5 h-3.5" />
          Powered by AI scheduling
        </div>
      </div>
    );
  }

  const scheduled = status.scheduled || [];
  const in_progress = status.in_progress || [];
  const completed = status.completed || [];
  const allInterviews = status.all_interviews || [];
  const hasBucketedRows = scheduled.length > 0 || in_progress.length > 0 || completed.length > 0;

  return (
    <div className="space-y-6">
      {activeTab === 'settings' ? (
        <div className="animate-fade-up">
          <div className="flex items-center gap-4 mb-10">
            <button
              onClick={() => setActiveTab('interviews')}
              className="p-3 bg-white border border-gray-100 rounded-2xl hover:bg-gray-50 transition-all shadow-sm"
            >
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h2 className="text-3xl font-black text-gray-900 tracking-tighter">Account Settings</h2>
              <p className="text-gray-500 font-medium">Configure your profile and preferences.</p>
            </div>
          </div>
          <SettingsPage />
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between flex-wrap gap-4 mb-8">
            <div>
              <h2 className="text-4xl font-black text-gray-900 tracking-tighter">Pilot Hub</h2>
              <p className="text-xs text-gray-400 font-bold uppercase tracking-widest mt-1">
                {lastRefresh ? `Last updated ${lastRefresh.toLocaleTimeString()}` : 'Live Synchronization Active'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={clearInterviews} disabled={clearing}
                className="px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest text-red-500 glass-container hover:bg-red-500 hover:text-white transition-all shadow-xl shadow-red-500/5">
                <div className="flex items-center gap-2">
                  <XCircle className={`w-3.5 h-3.5 ${clearing ? 'animate-spin' : ''}`} />
                  Purge Records
                </div>
              </button>
              <button onClick={fetchStatus} disabled={loading}
                className="px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest text-blue-500 glass-container hover:bg-blue-500 hover:text-white transition-all shadow-xl shadow-blue-500/5">
                <div className="flex items-center gap-2">
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-white' : ''}`} />
                  Refresh Data
                </div>
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className="px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest text-gray-600 glass-container hover:bg-gray-900 hover:text-white transition-all shadow-xl shadow-gray-500/5"
              >
                <div className="flex items-center gap-2">
                  <SettingsIcon className="w-3.5 h-3.5" />
                  Settings
                </div>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <StatCard label="Total" value={status.total_interviews} icon={Calendar} accent="#0c87ff" />
            <StatCard label="Scheduled" value={scheduled.length} icon={Clock} accent="#ef5807" />
            <StatCard label="In Progress" value={in_progress.length} icon={Radio} accent="#0c87ff" />
            <StatCard label="Completed" value={completed.length} icon={CheckCircle} accent="#10b981" />
            <StatCard label="Pending Review" value={status.pending_feedback || 0} icon={MessageSquare} accent="#6366f1" />
          </div>

          {scheduled.length > 0 && (
            <div className="border border-gray-100 bg-white shadow-sm overflow-hidden animate-fade-up !rounded-[2rem]">
              <SectionHeader icon={Clock} label="Upcoming Interviews" count={scheduled.length} accent="#ef5807" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <THead columns={['Candidate', 'Email', 'Scheduled Time', 'Interviewer', 'Status']} />
                  <tbody>
                    {scheduled.map((iv) => (
                      <tr key={iv.interview_id} className="table-row-premium">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <Avatar name={iv.candidate_name} color="#ef5807" />
                            <span className="font-semibold text-gray-900">{iv.candidate_name}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <a href={`mailto:${iv.candidate_email}`}
                            className="text-xs text-blue-500 hover:underline flex items-center gap-1">
                            <Mail className="w-3 h-3" /> {iv.candidate_email}
                          </a>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-600">
                            <Calendar className="w-3.5 h-3.5 text-orange-400" />
                            {formatDate(iv.scheduled_time)}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <User className="w-3.5 h-3.5" />
                            {iv.interviewer_name || 'TBD'}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge status={iv.interview_status} feedbackSubmitted={iv.feedback_submitted} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {in_progress.length > 0 && (
            <div className="border border-blue-100 bg-white shadow-sm overflow-hidden animate-fade-up !rounded-[2rem]">
              <SectionHeader icon={Radio} label="Currently In Progress" count={in_progress.length} accent="#0c87ff" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <THead columns={['Candidate', 'Email', 'Started', 'Interviewer', 'Status']} />
                  <tbody>
                    {in_progress.map((iv) => (
                      <tr key={iv.interview_id} className="table-row-premium">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <Avatar name={iv.candidate_name} color="#0c87ff" />
                            <span className="font-semibold text-gray-900">{iv.candidate_name}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <a href={`mailto:${iv.candidate_email}`}
                            className="text-xs text-blue-500 hover:underline flex items-center gap-1">
                            <Mail className="w-3 h-3" /> {iv.candidate_email}
                          </a>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-600">
                            <Calendar className="w-3.5 h-3.5 text-blue-400" />
                            {formatDate(iv.scheduled_time)}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <User className="w-3.5 h-3.5" />
                            {iv.interviewer_name || 'TBD'}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge status={iv.interview_status} feedbackSubmitted={iv.feedback_submitted} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {completed.length > 0 && (
            <div className="border border-gray-100 bg-white shadow-sm overflow-hidden animate-fade-up !rounded-[2rem]">
              <SectionHeader icon={Award} label="Completed Interviews" count={completed.length} accent="#10b981" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <THead columns={['Candidate', 'Date', 'Interviewer', 'Rating', 'Recommendation', 'Status']} />
                  <tbody>
                    {completed.map((iv) => (
                      <tr key={iv.interview_id} className="table-row-premium">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <Avatar name={iv.candidate_name} color="#0c87ff" />
                            <div>
                              <p className="font-semibold text-gray-900 leading-tight">{iv.candidate_name}</p>
                              {iv.candidate_email && (
                                <p className="text-xs text-gray-400">{iv.candidate_email}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <Calendar className="w-3.5 h-3.5 text-green-400" />
                            {formatDate(iv.scheduled_time)}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <User className="w-3 h-3" />
                            {iv.interviewer_name || 'N/A'}
                          </div>
                        </td>
                        <td className="px-5 py-4"><StarRating rating={iv.overall_rating} /></td>
                        <td className="px-5 py-4"><RecoPill rec={iv.recommendation} /></td>
                        <td className="px-5 py-4">
                          <StatusBadge status={iv.interview_status} feedbackSubmitted={iv.feedback_submitted} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!hasBucketedRows && allInterviews.length > 0 && (
            <div className="border border-gray-100 bg-white shadow-sm overflow-hidden animate-fade-up !rounded-[2rem]">
              <SectionHeader icon={ClipboardCheck} label="All Interview Records" count={allInterviews.length} accent="#6366f1" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <THead columns={['Candidate', 'Email', 'Date', 'Interviewer', 'Status']} />
                  <tbody>
                    {allInterviews.map((iv) => (
                      <tr key={iv.interview_id} className="table-row-premium">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <Avatar name={iv.candidate_name} color="#6366f1" />
                            <div>
                              <p className="font-semibold text-gray-900 leading-tight">{iv.candidate_name}</p>
                              {iv.candidate_email && (
                                <p className="text-xs text-gray-400">{iv.candidate_email}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <a href={`mailto:${iv.candidate_email}`}
                            className="text-xs text-blue-500 hover:underline flex items-center gap-1">
                            <Mail className="w-3 h-3" /> {iv.candidate_email}
                          </a>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <Calendar className="w-3.5 h-3.5 text-gray-400" />
                            {formatDate(iv.scheduled_time)}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <User className="w-3 h-3" />
                            {iv.interviewer_name || 'N/A'}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge status={iv.interview_status} feedbackSubmitted={iv.feedback_submitted} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {status.total_interviews > 0 && (
            <div className="border border-gray-100 bg-white p-5 shadow-sm overflow-hidden animate-fade-up !rounded-[2rem]">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                  <TrendingUp className="w-4 h-4 text-blue-500" />
                  Pipeline Progress
                </div>
                <span className="text-xs text-gray-400">
                  {completed.length} / {status.total_interviews - (status.cancelled?.length || 0)} completed
                </span>
              </div>
              <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full progress-bar-fill"
                  style={{ width: `${((completed.length + in_progress.length) / Math.max(status.total_interviews, 1)) * 100}%` }}
                />
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-300">
                <span>0</span>
                <span>{status.total_interviews}</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default InterviewStatus;
