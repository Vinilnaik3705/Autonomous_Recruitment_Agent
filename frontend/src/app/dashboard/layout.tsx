"use client";

import React, { useEffect, useState } from "react";
import { authClient } from "@/lib/auth-client";
import { UserPreferencesProvider, applyTheme } from "@/lib/user-preferences";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { data: session } = authClient.useSession();
  const user = session?.user;
  const userKey = user?.email || (user?.id != null ? String(user.id) : null);

  const [displayName, setDisplayName] = useState<string | undefined>();
  const [bio, setBio] = useState<string | undefined>();

  useEffect(() => {
    applyTheme("light");
  }, []);

  useEffect(() => {
    if (!user) return;
    setDisplayName(user.name || user.username);
    setBio(user.bio ?? "");
  }, [user]);

  useEffect(() => {
    const onUpdate = (e: Event) => {
      const detail = (e as CustomEvent<{ displayName?: string; bio?: string }>).detail;
      if (detail?.displayName) setDisplayName(detail.displayName);
      if (detail?.bio !== undefined) setBio(detail.bio);
    };
    window.addEventListener("user-profile-updated", onUpdate);
    return () => window.removeEventListener("user-profile-updated", onUpdate);
  }, []);

  return (
    <UserPreferencesProvider
      userKey={userKey}
      initialDisplayName={displayName}
      initialBio={bio}
    >
      {children}
    </UserPreferencesProvider>
  );
}
