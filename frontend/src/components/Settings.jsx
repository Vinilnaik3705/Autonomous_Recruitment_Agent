import React, { useState } from 'react';
import {
    User, Bell, Shield, Palette, Save,
    Mail, Globe, Moon, Sun, Monitor,
    Github, Linkedin, Twitter
} from 'lucide-react';

const Settings = ({ user }) => {
    const [profile, setProfile] = useState({
        username: user?.username || 'Vinil Naik',
        email: user?.email || 'vinil@example.com',
        role: user?.role || 'Senior Recruiter',
        bio: 'AI-focused talent acquisition specialist with 5+ years of experience.'
    });

    const [notifications, setNotifications] = useState({
        interviews: true,
        feedback: true,
        selection: true,
        marketing: false
    });

    const [theme, setTheme] = useState('system');

    return (
        <div className="max-w-5xl mx-auto space-y-10 animate-fade-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-black text-gray-900 tracking-tighter">Account Settings</h2>
                    <p className="text-gray-500 font-medium">Manage your profile, notifications, and system preferences.</p>
                </div>
                <button className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/30">
                    <Save className="w-4 h-4" />
                    Save Changes
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Left Col - Profile */}
                <div className="md:col-span-2 space-y-8">
                    <section className="bg-white rounded-[2rem] p-8 border border-gray-100 shadow-sm space-y-6">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-blue-50 rounded-xl">
                                <User className="w-5 h-5 text-blue-600" />
                            </div>
                            <h3 className="text-xl font-black text-gray-900 tracking-tight">Public Profile</h3>
                        </div>

                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">Full Name</label>
                                <input
                                    type="text"
                                    value={profile.username}
                                    onChange={(e) => setProfile({ ...profile, username: e.target.value })}
                                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">Email Address</label>
                                <input
                                    type="email"
                                    value={profile.email}
                                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                                />
                            </div>
                            <div className="col-span-2 space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">Professional Bio</label>
                                <textarea
                                    rows="4"
                                    value={profile.bio}
                                    onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-4 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                                />
                            </div>
                        </div>
                    </section>

                    <section className="bg-white rounded-[2rem] p-8 border border-gray-100 shadow-sm">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="p-2 bg-purple-50 rounded-xl">
                                <Shield className="w-5 h-5 text-purple-600" />
                            </div>
                            <h3 className="text-xl font-black text-gray-900 tracking-tight">Security & Social</h3>
                        </div>

                        <div className="space-y-4">
                            {[
                                { label: 'Google Account', icon: Globe, color: 'text-orange-500', status: `Connected as ${profile.email}`, primary: true },
                                { label: 'GitHub Account', icon: Github, color: 'text-gray-900', status: 'Not connected' },
                                { label: 'LinkedIn Profile', icon: Linkedin, color: 'text-blue-600', status: 'Not connected' }
                            ].map((social, i) => (
                                <div key={i} className={`flex items-center justify-between p-4 rounded-2xl border ${social.primary ? 'bg-orange-50/50 border-orange-100' : 'bg-gray-50 border-transparent'}`}>
                                    <div className="flex items-center gap-4">
                                        <div className={`p-2 rounded-xl ${social.primary ? 'bg-white shadow-sm' : ''}`}>
                                            <social.icon className={`w-5 h-5 ${social.color}`} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-black text-gray-900 tracking-tight">{social.label}</p>
                                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{social.status}</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => alert(`${social.label} configuration is currently managed via your primary login provider.`)}
                                        className={`text-[10px] font-black uppercase tracking-[0.2em] transition-all font-inter ${social.primary ? 'text-orange-600' : 'text-blue-600 hover:opacity-80'}`}
                                    >
                                        {social.primary ? 'Verified' : 'Configure'}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                {/* Right Col - System */}
                <div className="space-y-8">
                    <section className="bg-white rounded-[2rem] p-8 border border-gray-100 shadow-sm">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="p-2 bg-orange-50 rounded-xl">
                                <Bell className="w-5 h-5 text-orange-600" />
                            </div>
                            <h3 className="text-xl font-black text-gray-900 tracking-tight">Notifications</h3>
                        </div>

                        <div className="space-y-6">
                            {[
                                { id: 'interviews', title: 'Interview Reminders', desc: 'Alerts for upcoming calls' },
                                { id: 'feedback', title: 'Feedback Requests', desc: 'Prompt to fill evaluation' },
                                { id: 'selection', title: 'Selection Alerts', desc: 'When candidates are hired' }
                            ].map((notif) => (
                                <div key={notif.id} className="flex items-center justify-between">
                                    <div className="max-w-[140px]">
                                        <p className="text-sm font-black text-gray-900 tracking-tight">{notif.title}</p>
                                        <p className="text-[10px] font-medium text-gray-400">{notif.desc}</p>
                                    </div>
                                    <button
                                        onClick={() => setNotifications({ ...notifications, [notif.id]: !notifications[notif.id] })}
                                        className={`w-12 h-6 rounded-full transition-all relative ${notifications[notif.id] ? 'bg-blue-600' : 'bg-gray-200'}`}
                                    >
                                        <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm transition-all ${notifications[notif.id] ? 'left-7' : 'left-1'}`} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="bg-white rounded-[2rem] p-8 border border-gray-100 shadow-sm">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="p-2 bg-emerald-50 rounded-xl">
                                <Palette className="w-5 h-5 text-emerald-600" />
                            </div>
                            <h3 className="text-xl font-black text-gray-900 tracking-tight">System Theme</h3>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                            {[
                                { id: 'light', icon: Sun, label: 'Light' },
                                { id: 'dark', icon: Moon, label: 'Dark' },
                                { id: 'system', icon: Monitor, label: 'Auto' }
                            ].map((t) => (
                                <button
                                    key={t.id}
                                    onClick={() => setTheme(t.id)}
                                    className={`flex flex-col items-center gap-2 p-3 rounded-2xl border-2 transition-all ${theme === t.id ? 'border-blue-600 bg-blue-50/50' : 'border-gray-50 hover:border-gray-100'}`}
                                >
                                    <t.icon className={`w-5 h-5 ${theme === t.id ? 'text-blue-600' : 'text-gray-400'}`} />
                                    <span className={`text-[10px] font-black uppercase tracking-widest ${theme === t.id ? 'text-blue-900' : 'text-gray-400'}`}>{t.label}</span>
                                </button>
                            ))}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default Settings;
