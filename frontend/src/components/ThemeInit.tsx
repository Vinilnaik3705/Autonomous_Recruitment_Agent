"use client";

import { useEffect } from "react";
import { applyTheme, type ThemeMode } from "@/lib/user-preferences";

const STORAGE_PREFIX = "antigravity_user_prefs";

/** Apply saved theme before paint on any page (including login). */
export default function ThemeInit() {
  useEffect(() => {
    applyTheme("light");
  }, []);

  return null;
}
