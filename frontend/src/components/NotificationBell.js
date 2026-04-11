import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, X, RefreshCcw, Zap, Star, Film, Trophy, Target, Users, Flame } from 'lucide-react';
import api from '../utils/api';

const ICON_MAP = {
  story_remixed: Users,
  story_trending: Zap,
  daily_challenge_live: Target,
  ownership_milestone: Trophy,
  continuation: RefreshCcw,
  share_reward: Zap,
  follow: Star,
  trending: Film,
  viral_remix: Flame,
  rank_drop: Trophy,
  version_outperformed: Zap,
  story_branched: RefreshCcw,
};

const COLOR_MAP = {
  story_remixed: 'text-pink-400 bg-pink-500/10',
  story_trending: 'text-amber-400 bg-amber-500/10',
  daily_challenge_live: 'text-emerald-400 bg-emerald-500/10',
  ownership_milestone: 'text-yellow-400 bg-yellow-500/10',
  viral_remix: 'text-rose-400 bg-rose-500/10',
  rank_drop: 'text-rose-400 bg-rose-500/10',
  version_outperformed: 'text-amber-400 bg-amber-500/10',
  story_branched: 'text-violet-400 bg-violet-500/10',
};

export default function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    fetchNotifications();
    const iv = setInterval(fetchNotifications, 30000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const fetchNotifications = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      const res = await api.get('/api/universe/notifications');
      if (res.data.success) {
        setNotifications(res.data.notifications || []);
        setUnread(res.data.unread_count || 0);
      }
    } catch {}
  };

  const markRead = async () => {
    try {
      await api.post('/api/universe/notifications/read');
      setUnread(0);
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch {}
  };

  const handleClick = (n) => {
    const link = n.link || n.data?.deep_link;
    if (link) {
      setOpen(false);
      navigate(link);
    }
  };

  const timeAgo = (iso) => {
    if (!iso) return '';
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return `${mins}m`;
    if (mins < 1440) return `${Math.floor(mins / 60)}h`;
    return `${Math.floor(mins / 1440)}d`;
  };

  return (
    <div className="relative" ref={ref} data-testid="notification-bell">
      <button
        onClick={() => { setOpen(!open); if (!open && unread > 0) markRead(); }}
        className="relative p-2 text-slate-400 hover:text-white transition-colors rounded-full bg-black/40 backdrop-blur-xl border border-white/[0.06] hover:border-white/10"
        data-testid="notification-btn"
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-rose-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center min-w-[16px] h-[16px] px-0.5 animate-pulse" data-testid="notification-badge">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 w-80 bg-[#0d0d18] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden" data-testid="notification-dropdown">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
            <h3 className="text-sm font-bold text-white">Notifications</h3>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <span className="text-[10px] text-indigo-400 font-medium">{unread} new</span>
              )}
              <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="text-center py-8 px-4">
                <Bell className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                <p className="text-xs text-slate-500 font-medium">No notifications yet</p>
                <p className="text-[10px] text-slate-600 mt-1">We'll let you know when someone remixes your story or a challenge goes live</p>
              </div>
            ) : (
              notifications.map((n, i) => {
                const NIcon = ICON_MAP[n.type] || Bell;
                const colorCls = COLOR_MAP[n.type] || (!n.read ? 'text-violet-400 bg-violet-500/10' : 'text-slate-500 bg-white/[0.04]');
                const hasLink = !!(n.link || n.data?.deep_link);
                return (
                  <div
                    key={n._id || i}
                    className={`px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors ${hasLink ? 'cursor-pointer' : ''} ${!n.read ? 'bg-violet-500/[0.04]' : ''}`}
                    onClick={() => handleClick(n)}
                    data-testid={`notification-item-${i}`}
                  >
                    <div className="flex gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${colorCls}`}>
                        <NIcon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs font-medium leading-relaxed ${!n.read ? 'text-white' : 'text-slate-400'}`}>{n.title}</p>
                        {n.body && <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{n.body}</p>}
                        {/* Aggregated remix count */}
                        {n.type === 'story_remixed' && n.meta?.remix_count > 1 && (
                          <span className="inline-flex items-center gap-1 text-[10px] text-pink-400 font-semibold mt-1">
                            <Users className="w-2.5 h-2.5" /> {n.meta.remix_count} people
                          </span>
                        )}
                        {/* Viral remix momentum */}
                        {n.type === 'viral_remix' && n.count > 1 && (
                          <span className="inline-flex items-center gap-1 text-[10px] text-rose-400 font-semibold mt-1" data-testid="viral-notification-count">
                            <Flame className="w-2.5 h-2.5" /> {n.count} creator{n.count !== 1 ? 's' : ''} inspired
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-600 flex-shrink-0">{timeAgo(n.created_at)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
