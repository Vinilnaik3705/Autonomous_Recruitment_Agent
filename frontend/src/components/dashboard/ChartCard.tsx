"use client";

import React from "react";

export function ChartCard({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`glass-card p-6 md:p-8 !rounded-[2rem] border-white/40 shadow-lg ${className}`}
    >
      <div className="mb-6">
        <h3 className="text-lg font-black text-gray-900 tracking-tight">{title}</h3>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
