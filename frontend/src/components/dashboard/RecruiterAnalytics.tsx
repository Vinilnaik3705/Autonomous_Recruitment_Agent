"use client";

import React, { useEffect, useMemo, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getInterviewStatus } from "@/lib/api";
import api from "@/lib/api";
import { ChartCard } from "./ChartCard";

type DbStatus = {
  resume_data?: number;
  candidates?: number;
  shortlisted_candidates?: number;
  interview_schedules?: number;
  job_descriptions?: number;
};

const COLORS = ["#0c87ff", "#ef5807", "#10b981", "#8b5cf6", "#f59e0b", "#6366f1"];

function buildWeeklyTrend(
  interviews: Array<{ scheduled_time?: string; created_at?: string }>,
  weeks = 6,
) {
  const now = new Date();
  const buckets: { week: string; interviews: number; start: number; end: number }[] = [];

  for (let i = weeks - 1; i >= 0; i--) {
    const weekEnd = new Date(now);
    weekEnd.setDate(weekEnd.getDate() - i * 7);
    weekEnd.setHours(23, 59, 59, 999);
    const weekStart = new Date(weekEnd);
    weekStart.setDate(weekStart.getDate() - 6);
    weekStart.setHours(0, 0, 0, 0);
    buckets.push({
      week: weekStart.toLocaleDateString([], { month: "short", day: "numeric" }),
      interviews: 0,
      start: weekStart.getTime(),
      end: weekEnd.getTime(),
    });
  }

  for (const iv of interviews) {
    const raw = iv.scheduled_time || iv.created_at;
    if (!raw) continue;
    const t = new Date(raw).getTime();
    const bucket = buckets.find((b) => t >= b.start && t <= b.end);
    if (bucket) bucket.interviews += 1;
  }

  return buckets.map(({ week, interviews: count }) => ({ week, interviews: count }));
}

export default function RecruiterAnalytics() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    resumes: 0,
    candidates: 0,
    shortlisted: 0,
    totalInterviews: 0,
    scheduled: 0,
    inProgress: 0,
    completed: 0,
    pendingFeedback: 0,
    activeJobs: 0,
    notShortlisted: 0,
  });
  const [weeklyTrend, setWeeklyTrend] = useState<{ week: string; interviews: number }[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const [interviews, dbRes] = await Promise.all([
        getInterviewStatus(true),
        api.get<DbStatus>("/jobs/database-status").then((r) => r.data),
      ]);
      const candidates = dbRes.candidates ?? 0;
      const shortlisted = dbRes.shortlisted_candidates ?? 0;
      setStats({
        resumes: dbRes.resume_data ?? 0,
        candidates,
        shortlisted,
        notShortlisted: Math.max(0, candidates - shortlisted),
        activeJobs: dbRes.job_descriptions ?? 0,
        totalInterviews: interviews.total_interviews ?? 0,
        scheduled: interviews.scheduled?.length ?? 0,
        inProgress: interviews.in_progress?.length ?? 0,
        completed: interviews.completed?.length ?? 0,
        pendingFeedback: interviews.pending_feedback ?? 0,
      });
      const all = interviews.all_interviews || [];
      setWeeklyTrend(buildWeeklyTrend(all));
    } catch (e) {
      console.error("Failed to load recruiter analytics", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const funnelData = useMemo(
    () => [
      { stage: "Resumes", count: stats.resumes, fill: COLORS[0] },
      { stage: "Candidates", count: stats.candidates, fill: COLORS[1] },
      { stage: "Shortlisted", count: stats.shortlisted, fill: COLORS[2] },
      { stage: "Interviews", count: stats.totalInterviews, fill: COLORS[3] },
      { stage: "Completed", count: stats.completed, fill: COLORS[4] },
    ],
    [stats],
  );

  const interviewStatusData = useMemo(
    () =>
      [
        { name: "Scheduled", value: stats.scheduled, fill: COLORS[0] },
        { name: "In progress", value: stats.inProgress, fill: COLORS[4] },
        { name: "Completed", value: stats.completed, fill: COLORS[2] },
        { name: "Pending feedback", value: stats.pendingFeedback, fill: COLORS[1] },
      ].filter((d) => d.value > 0),
    [stats],
  );

  const shortlistSplit = useMemo(
    () =>
      [
        { name: "Shortlisted", value: stats.shortlisted, fill: COLORS[2] },
        { name: "Not shortlisted", value: stats.notShortlisted, fill: "#e5e7eb" },
      ].filter((d) => d.value > 0),
    [stats],
  );

  const tooltipStyle = {
    borderRadius: "12px",
    border: "1px solid #e5e7eb",
    fontSize: "12px",
    fontWeight: 600,
  };

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex items-center justify-end">
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-white border border-gray-100 shadow-sm text-xs font-black uppercase tracking-widest text-blue-600 hover:bg-gray-50 transition-all disabled:opacity-60"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <ChartCard
            title="Hiring funnel"
            subtitle="Volume at each stage of your pipeline"
            className="xl:col-span-2"
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={funnelData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis
                  dataKey="stage"
                  tick={{ fill: "#6b7280", fontSize: 12, fontWeight: 600 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" radius={[10, 10, 0, 0]} maxBarSize={56}>
                  {funnelData.map((entry, i) => (
                    <Cell key={entry.stage} fill={entry.fill || COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Interview status" subtitle="Current distribution across stages">
            {interviewStatusData.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-16">No interviews yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={interviewStatusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                  >
                    {interviewStatusData.map((entry, i) => (
                      <Cell key={entry.name} fill={entry.fill || COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend
                    verticalAlign="bottom"
                    iconType="circle"
                    formatter={(value) => (
                      <span className="text-xs font-semibold text-gray-600">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard title="Shortlist breakdown" subtitle="Candidates shortlisted vs remaining">
            {stats.candidates === 0 ? (
              <p className="text-sm text-gray-400 text-center py-16">No candidates tracked yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={
                      shortlistSplit.length
                        ? shortlistSplit
                        : [{ name: "No data", value: 1, fill: "#e5e7eb" }]
                    }
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percent }: { name?: string; percent?: number }) =>
                      `${name || ""} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {(shortlistSplit.length ? shortlistSplit : [{ fill: "#e5e7eb" }]).map(
                      (entry, i) => (
                        <Cell
                          key={`cell-${i}`}
                          fill={"fill" in entry ? entry.fill : COLORS[i]}
                        />
                      ),
                    )}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard
            title="Interview activity"
            subtitle="Interviews scheduled over recent weeks"
            className="xl:col-span-2"
          >
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={weeklyTrend} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="week"
                  tick={{ fill: "#6b7280", fontSize: 11, fontWeight: 600 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Line
                  type="monotone"
                  dataKey="interviews"
                  stroke="#0c87ff"
                  strokeWidth={3}
                  dot={{ fill: "#0c87ff", r: 5, strokeWidth: 2, stroke: "#fff" }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard
            title="Jobs vs resumes"
            subtitle={`${stats.activeJobs} active posts · ${stats.resumes} resumes in pool`}
            className="xl:col-span-2"
          >
            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={[
                  { label: "Job posts", count: stats.activeJobs, fill: COLORS[3] },
                  { label: "Resumes", count: stats.resumes, fill: COLORS[0] },
                  { label: "Avg per job", count: stats.activeJobs > 0 ? Math.round(stats.resumes / stats.activeJobs) : 0, fill: COLORS[1] },
                ]}
                layout="vertical"
                margin={{ top: 8, right: 24, left: 24, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="label"
                  tick={{ fill: "#6b7280", fontSize: 12, fontWeight: 600 }}
                  width={90}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" radius={[0, 8, 8, 0]} maxBarSize={32}>
                  {[COLORS[3], COLORS[0], COLORS[1]].map((c, i) => (
                    <Cell key={i} fill={c} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}
    </div>
  );
}
