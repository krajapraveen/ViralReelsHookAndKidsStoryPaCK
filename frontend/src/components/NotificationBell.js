import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, X, Film, RefreshCcw, Zap, Star, Play, ArrowRight } from 'lucide-react';
import api from '../utils/api';

const ICON_MAP = {
  continuation: RefreshCcw,
  share_reward: Zap,
  follow: Star,
  trending: Film,
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
    if (n.link) {
      setOpen(false);
      navigate(n.link);
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
        className="relative p-2 text-slate-400 hover:text-white transition-colors"
        data-testid="notification-btn"
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-rose-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center min-w-[18px] h-[18px] px-1 animate-pulse" data-testid="notification-badge">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 w-80 bg-[#0d0d18] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden" data-testid="notification-dropdown">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
            <h3 className="text-sm font-bold text-white">Notifications</h3>
            <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="text-center py-8 px-4">
                <Bell className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                <p className="text-xs text-slate-500 font-medium">No notifications yet</p>
                <p className="text-[10px] text-slate-600 mt-1">Follow characters to get notified when new stories drop</p>
              </div>
            ) : (
              notifications.map((n, i) => {
                const NIcon = ICON_MAP[n.type] || Bell;
                const hasLink = !!n.link;
                return (
                  <div
                    key={i}
                    className={`px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors ${hasLink ? 'cursor-pointer' : ''} ${!n.read ? 'bg-violet-500/[0.04]' : ''}`}
                    onClick={() => handleClick(n)}
                    data-testid={`notification-${i}`}
                  >
                    <div className="flex gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${!n.read ? 'bg-violet-500/10' : 'bg-white/[0.04]'}`}>
                        <NIcon className={`w-4 h-4 ${!n.read ? 'text-violet-400' : 'text-slate-500'}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs font-medium leading-relaxed ${!n.read ? 'text-white' : 'text-slate-400'}`}>{n.title}</p>
                        {n.body && <p className="text-[10px] text-slate-500 mt-0.5">{n.body}</p>}
                        {/* Action-driven: show continue link for follow-type notifications */}
                        {hasLink && n.type === 'follow' && (
                          <span className="inline-flex items-center gap-1 text-[10px] text-violet-400 font-semibold mt-1">
                            <Play className="w-2.5 h-2.5" /> Continue story <ArrowRight className="w-2.5 h-2.5" />
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
