"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Bell, Loader2, X } from "lucide-react";
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api";
import { filterNotificationsByPrefs, type NotificationPrefs } from "@/lib/user-preferences";

export type NotificationItem = {
  id: number;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at?: string;
  time?: string;
};

function formatTime(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function NotificationRow({
  notif,
  onRead,
}: {
  notif: NotificationItem;
  onRead: (id: number) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => !notif.read && onRead(notif.id)}
      className={`w-full text-left p-5 flex gap-4 hover:bg-gray-50 transition-all border-b border-gray-100 ${
        !notif.read ? "bg-blue-50/50" : ""
      }`}
    >
      <div
        className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
          notif.type === "alert"
            ? "bg-orange-100 text-orange-600"
            : notif.type === "success"
              ? "bg-emerald-100 text-emerald-600"
              : "bg-blue-100 text-blue-600"
        }`}
      >
        <Bell className="w-5 h-5" />
      </div>
      <div className="space-y-1 min-w-0">
        <p className="text-sm font-black text-gray-900 leading-tight">{notif.title}</p>
        <p className="text-xs text-gray-500 font-medium leading-relaxed">{notif.message}</p>
        <p className="text-[10px] text-gray-400 font-bold">{notif.time}</p>
      </div>
    </button>
  );
}

export default function NotificationCenter({
  prefs,
}: {
  prefs: NotificationPrefs;
}) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [showAllModal, setShowAllModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingAll, setLoadingAll] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [allNotifications, setAllNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  const mapItems = useCallback(
    (items: Array<Record<string, unknown>>) => {
      const formatted = items.map((n) => ({
        id: n.id as number,
        type: (n.type as string) || "info",
        title: (n.title as string) || "",
        message: (n.message as string) || "",
        read: Boolean(n.read),
        created_at: n.created_at as string | undefined,
        time: formatTime(n.created_at as string),
      }));
      return filterNotificationsByPrefs(formatted, prefs);
    },
    [prefs],
  );

  const loadPreview = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNotifications({ limit: 20, offset: 0 });
      const items = mapItems(data.items || []);
      setNotifications(items);
      setUnreadCount(data.unread ?? 0);
      setTotalCount(data.total ?? items.length);
    } catch (e) {
      console.error("Failed to fetch notifications:", e);
    } finally {
      setLoading(false);
    }
  }, [mapItems]);

  const loadAll = useCallback(async () => {
    setLoadingAll(true);
    try {
      const data = await getNotifications({ limit: 500, offset: 0 });
      const items = mapItems(data.items || []);
      setAllNotifications(items);
      setUnreadCount(data.unread ?? 0);
      setTotalCount(data.total ?? items.length);
    } catch (e) {
      console.error("Failed to fetch all notifications:", e);
    } finally {
      setLoadingAll(false);
    }
  }, [mapItems]);

  useEffect(() => {
    loadPreview();
    const interval = setInterval(loadPreview, 30000);
    return () => clearInterval(interval);
  }, [loadPreview]);

  const handleMarkRead = async (id: number) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );
      setAllNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      console.error("Failed to mark notification read:", e);
    }
  };

  const handleViewAll = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowDropdown(false);
    setShowAllModal(true);
    await loadAll();
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      await loadAll();
      await loadPreview();
    } catch (e) {
      console.error("Failed to mark all read:", e);
    }
  };

  const displayUnread = notifications.filter((n) => !n.read).length;

  return (
    <>
      <div className="relative">
        <button
          type="button"
          onClick={() => setShowDropdown(!showDropdown)}
          className={`w-11 h-11 flex items-center justify-center rounded-2xl bg-white border border-gray-100 shadow-sm hover:scale-105 transition-all ${
            showDropdown ? "text-blue-600 ring-2 ring-blue-500/10" : "text-gray-400"
          }`}
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5" />
          {(unreadCount > 0 || displayUnread > 0) && (
            <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-red-500 border-2 border-white rounded-full" />
          )}
        </button>

        {showDropdown && (
          <>
            <div className="fixed inset-0 z-[90]" onClick={() => setShowDropdown(false)} />
            <div
              className="absolute right-0 top-full mt-4 w-96 bg-white border border-gray-200 rounded-3xl shadow-2xl z-[100] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                <h3 className="text-sm font-black text-gray-900 tracking-widest uppercase">
                  Notifications
                </h3>
                <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-lg uppercase tracking-widest">
                  {unreadCount || displayUnread} New
                </span>
              </div>
              <div className="max-h-[400px] overflow-y-auto">
                {loading ? (
                  <div className="p-10 flex justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                  </div>
                ) : notifications.length > 0 ? (
                  notifications.map((notif) => (
                    <NotificationRow key={notif.id} notif={notif} onRead={handleMarkRead} />
                  ))
                ) : (
                  <div className="p-10 text-center space-y-3">
                    <Bell className="w-10 h-10 mx-auto text-gray-200" />
                    <p className="text-sm text-gray-400 font-medium tracking-tight">All caught up!</p>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={handleViewAll}
                className="w-full py-4 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 hover:text-blue-600 bg-gray-50 transition-all border-t border-gray-100"
              >
                View all activity
                {totalCount > notifications.length ? ` (${totalCount})` : ""}
              </button>
            </div>
          </>
        )}
      </div>

      {showAllModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowAllModal(false)}
          />
          <div className="relative w-full max-w-2xl max-h-[85vh] bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-black text-gray-900">All activity</h2>
                <p className="text-sm text-gray-500 mt-1">
                  {totalCount} total · {unreadCount} unread
                </p>
              </div>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={handleMarkAllRead}
                    className="text-[10px] font-black uppercase tracking-widest text-blue-600 hover:text-blue-800 px-3 py-2"
                  >
                    Mark all read
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowAllModal(false)}
                  className="p-2 rounded-xl hover:bg-gray-100 text-gray-500"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loadingAll ? (
                <div className="p-16 flex justify-center">
                  <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
                </div>
              ) : allNotifications.length > 0 ? (
                allNotifications.map((notif) => (
                  <NotificationRow key={notif.id} notif={notif} onRead={handleMarkRead} />
                ))
              ) : (
                <div className="p-16 text-center text-gray-400 text-sm">No notifications yet</div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
