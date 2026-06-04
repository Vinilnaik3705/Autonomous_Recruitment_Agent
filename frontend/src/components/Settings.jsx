import React, { useEffect, useState } from 'react';
import {
    User, Bell, Shield, Save,
    Mail, Globe
} from 'lucide-react';
import { useUserPreferences } from '@/lib/user-preferences';

const Settings = ({ user }) => {
    const {
        prefs,
        setNotification,
        updateProfileFields,
        savePreferences,
        isSaving,
        saveMessage,
    } = useUserPreferences();

    const [profile, setProfile] = useState({
        username: user?.username || 'User',
        email: user?.email || '',
        role: user?.role || 'recruiter',
        bio: prefs.bio || '',
        avatar: prefs.avatar || '',
    });

    const [localSaveMessage, setLocalSaveMessage] = useState('');

    useEffect(() => {
        setProfile({
            username: prefs.displayName || user?.username || 'User',
            email: user?.email || '',
            role: user?.role || 'recruiter',
            bio: prefs.bio || '',
            avatar: prefs.avatar || '',
        });
    }, [user?.username, user?.email, user?.role, prefs.displayName, prefs.bio, prefs.avatar]);

    useEffect(() => {
        if (saveMessage) {
            setLocalSaveMessage(saveMessage);
            const timer = setTimeout(() => {
                setLocalSaveMessage('');
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [saveMessage]);

    const handleProfileChange = (field, value) => {
        const next = { ...profile, [field]: value };
        setProfile(next);
        if (field === 'username') updateProfileFields({ displayName: value });
        if (field === 'bio') updateProfileFields({ bio: value });
    };

    const handleAvatarUpload = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (uploadEvent) => {
            const base64 = uploadEvent.target?.result;
            if (typeof base64 === 'string') {
                setProfile(prev => ({ ...prev, avatar: base64 }));
            }
        };
        reader.readAsDataURL(file);
    };

    const handleSave = async () => {
        await savePreferences({
            displayName: profile.username,
            bio: profile.bio,
            avatar: profile.avatar,
        });
    };

    return (
        <div className="max-w-5xl mx-auto space-y-10 animate-fade-up text-gray-900">
            <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                    <h2 className="text-3xl font-black text-gray-900 tracking-tighter">Account Settings</h2>
                    <p className="text-gray-500 font-medium">Manage your profile and notifications.</p>
                    {localSaveMessage && (
                        <p className={`mt-2 text-sm font-semibold ${localSaveMessage.includes('failed') || localSaveMessage.includes('locally') ? 'text-amber-600' : 'text-emerald-600'}`}>
                            {localSaveMessage}
                        </p>
                    )}
                </div>
                <button
                    type="button"
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/30 disabled:opacity-60"
                >
                    <Save className="w-4 h-4" />
                    {isSaving ? 'Saving…' : 'Save Changes'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="md:col-span-2 space-y-8">
                    <section className="bg-white rounded-[2rem] p-8 border border-gray-100 shadow-sm space-y-6">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-blue-50 rounded-xl">
                                <User className="w-5 h-5 text-blue-600" />
                            </div>
                            <h3 className="text-xl font-black text-gray-900 tracking-tight">Public Profile</h3>
                        </div>

                        {/* Avatar Upload Container */}
                        <div className="flex items-center gap-6 pb-6 border-b border-gray-100 flex-wrap">
                            <div className="relative group">
                                <div className="w-20 h-20 rounded-3xl bg-blue-500 text-white flex items-center justify-center text-3xl font-black shadow-lg overflow-hidden border-2 border-white">
                                    {profile.avatar ? (
                                        <img src={profile.avatar} alt="Avatar" className="w-full h-full object-cover" />
                                    ) : (
                                        profile.username.charAt(0).toUpperCase()
                                    )}
                                </div>
                                <label className="absolute inset-0 flex items-center justify-center bg-black/40 text-white text-[10px] font-black uppercase tracking-widest rounded-3xl opacity-0 group-hover:opacity-100 transition-all cursor-pointer">
                                    Upload
                                    <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
                                </label>
                            </div>
                            <div>
                                <h4 className="font-black text-gray-900 text-lg leading-tight">{profile.username}</h4>
                                <p className="text-xs text-gray-400 font-bold uppercase tracking-widest mt-1">{profile.role}</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">Full Name</label>
                                <input
                                    type="text"
                                    value={profile.username}
                                    onChange={(e) => handleProfileChange('username', e.target.value)}
                                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                    <input
                                        type="email"
                                        value={profile.email}
                                        readOnly
                                        className="w-full bg-gray-100 border border-gray-200 rounded-xl pl-10 pr-4 py-3 text-sm font-semibold text-gray-500 cursor-not-allowed"
                                    />
                                </div>
                            </div>
                            <div className="col-span-2 space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">Professional Bio</label>
                                <textarea
                                    rows="4"
                                    value={profile.bio}
                                    onChange={(e) => handleProfileChange('bio', e.target.value)}
                                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-4 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
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
                                { label: 'Google Account', icon: Globe, color: 'text-orange-500', status: profile.email ? `Connected as ${profile.email}` : 'Sign in with Google', primary: true }
                            ].map((social, i) => (
                                <div key={i} className="flex items-center justify-between p-4 rounded-2xl border bg-orange-50/50 border-orange-100">
                                    <div className="flex items-center gap-4">
                                        <div className="p-2 rounded-xl bg-white shadow-sm">
                                            <social.icon className={`w-5 h-5 ${social.color}`} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-black text-gray-900 tracking-tight">{social.label}</p>
                                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{social.status}</p>
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        className="text-[10px] font-black uppercase tracking-[0.2em] transition-all text-orange-600 cursor-default"
                                    >
                                        Verified
                                    </button>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

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
                                        type="button"
                                        aria-pressed={prefs.notifications[notif.id]}
                                        onClick={() => setNotification(notif.id, !prefs.notifications[notif.id])}
                                        className={`w-12 h-6 rounded-full transition-all relative ${prefs.notifications[notif.id] ? 'bg-blue-600' : 'bg-gray-200'}`}
                                    >
                                        <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm transition-all ${prefs.notifications[notif.id] ? 'left-7' : 'left-1'}`} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default Settings;
