"use client";

import React, { useEffect, useMemo, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAdminUsers, getInterviewStatus } from "@/lib/api";
import api from "@/lib/api";
import { ChartCard } from "./ChartCard";

type DbStatus = {
  candidates?: number;
  shortlisted_candidates?: number;
  interview_schedules?: number;
  interview_feedback?: number;
  job_descriptions?: number;
};

const COLORS = ["#0c87ff", "#ef5807", "#10b981", "#8b5cf6", "#f59e0b", "#6366f1"];

export default function HRAnalytics() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    inactiveUsers: 0,
    recruiters: 0,
    students: 0,
    hrUsers: 0,
    candidates: 0,
    shortlisted: 0,
    interviews: 0,
    feedback: 0,
    jobs: 0,
    completedInterviews: 0,
    scheduled: 0,
    inProgress: 0,
  });

  const load = async () => {
    setLoading(true);
    try {
      const [users, interviews, dbRes] = await Promise.all([
        getAdminUsers(),
        getInterviewStatus(true),
        api.get<DbStatus>("/jobs/database-status").then((r) => r.data),
      ]);
      const list = Array.isArray(users) ? users : [];
      const active = list.filter((u: { is_active?: boolean }) => u.is_active).length;
      setStats({
        totalUsers: list.length,
        activeUsers: active,
        inactiveUsers: list.length - active,
        recruiters: list.filter((u: { role?: string }) => u.role === "recruiter").length,
        students: list.filter((u: { role?: string }) => u.role === "student").length,
        hrUsers: list.filter((u: { role?: string }) => u.role === "hr").length,
        candidates: dbRes.candidates ?? 0,
        shortlisted: dbRes.shortlisted_candidates ?? 0,
        interviews: dbRes.interview_schedules ?? 0,
        feedback: dbRes.interview_feedback ?? 0,
        jobs: dbRes.job_descriptions ?? 0,
        completedInterviews: interviews.completed?.length ?? 0,
        scheduled: interviews.scheduled?.length ?? 0,
        inProgress: interviews.in_progress?.length ?? 0,
      });
    } catch (e) {
      console.error("Failed to load HR analytics", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const roleData = useMemo(
    () =>
      [
        { name: "Recruiters", value: stats.recruiters, fill: COLORS[3] },
        { name: "Students", value: stats.students, fill: COLORS[1] },
        { name: "HR", value: stats.hrUsers, fill: COLORS[0] },
      ].filter((d) => d.value > 0),
    [stats],
  );

  const accountData = useMemo(
    () => [
      { name: "Active", value: stats.activeUsers, fill: COLORS[2] },
      { name: "Inactive", value: stats.inactiveUsers, fill: "#ef4444" },
    ],
    [stats],
  );

  const hiringData = useMemo(
    () => [
      { metric: "Candidates", count: stats.candidates, fill: COLORS[0] },
      { metric: "Shortlisted", count: stats.shortlisted, fill: COLORS[2] },
      { metric: "Interviews", count: stats.interviews, fill: COLORS[4] },
      { metric: "Feedback", count: stats.feedback, fill: COLORS[5] },
      { metric: "Job posts", count: stats.jobs, fill: COLORS[3] },
    ],
    [stats],
  );

  const interviewData = useMemo(
    () => [
      { status: "Scheduled", count: stats.scheduled, fill: COLORS[0] },
      { status: "In progress", count: stats.inProgress, fill: COLORS[4] },
      { status: "Completed", count: stats.completedInterviews, fill: COLORS[2] },
    ],
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
          <ChartCard title="Users by role" subtitle="Team composition across the platform">
            {roleData.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-16">No users yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={roleData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={4}
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {roleData.map((entry, i) => (
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

          <ChartCard title="Account status" subtitle="Active vs deactivated accounts">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={accountData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  label={({ name, percent }: { name?: string; percent?: number }) =>
                    `${name || ""} ${((percent ?? 0) * 100).toFixed(0)}%`
                  }
                >
                  {accountData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard
            title="Hiring pipeline"
            subtitle="Organization-wide candidate and interview volume"
            className="xl:col-span-2"
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={hiringData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis
                  dataKey="metric"
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
                <Bar dataKey="count" radius={[10, 10, 0, 0]} maxBarSize={48}>
                  {hiringData.map((entry, i) => (
                    <Cell key={entry.metric} fill={entry.fill || COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard
            title="Interview stages"
            subtitle="Live interview distribution"
            className="xl:col-span-2"
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={interviewData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis
                  dataKey="status"
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
                  {interviewData.map((entry, i) => (
                    <Cell key={entry.status} fill={entry.fill || COLORS[i % COLORS.length]} />
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
