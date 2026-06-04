"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";

export default function DashboardIndex() {
  const router = useRouter();

  useEffect(() => {
    authClient.getSession().then((session) => {
      if (session?.data?.user) {
        const userRole = session.data.user.role || "recruiter";
        if (userRole === "student") {
          router.push("/dashboard/student");
        } else if (userRole === "hr") {
          router.push("/dashboard/admin");
        } else {
          router.push("/dashboard/recruiter");
        }
      } else {
        router.push("/login");
      }
    });
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-orange-500/40 border-t-orange-400 rounded-full animate-spin" />
        <p className="text-slate-500 text-sm">Redirecting to your dashboard...</p>
      </div>
    </div>
  );
}
