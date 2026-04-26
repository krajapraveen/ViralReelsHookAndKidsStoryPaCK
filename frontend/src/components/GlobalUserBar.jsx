import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Zap, Settings, CreditCard, LogOut } from 'lucide-react';
import { useCredits } from '../contexts/CreditContext';
import NotificationBell from './NotificationBell';

function isAdminUser() {
  try {
    const token = localStorage.getItem('token');
    if (!token) return false;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role?.toUpperCase() === 'ADMIN' || payload.role?.toUpperCase() === 'SUPERADMIN';
  } catch { return false; }
}

export default function GlobalUserBar() {
  const navigate = useNavigate();
  const { credits } = useCredits();
  const [open, setOpen] = useState(false);
  const isAdmin = isAdminUser();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  return (
    <div className={`fixed ${isAdmin ? 'top-[52px]' : 'top-0'} right-0 z-[10002] p-2 sm:p-3`} data-testid="global-user-bar">
      <div className="relative flex items-center gap-1.5 sm:gap-2">
        <NotificationBell />
        <button
          onClick={() => setOpen(prev => !prev)}
          className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-full border border-white/10 bg-black/60 backdrop-blur-xl hover:bg-white/10 transition-colors"
          data-testid="user-menu-toggle"
          aria-label="User menu"
        >
          <Zap className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-amber-400" />
          <span className="text-[11px] sm:text-xs font-medium text-white">{credits >= 99999 ? '∞' : (credits ?? '...')}</span>
          <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-indigo-500/30 border border-indigo-500/40 flex items-center justify-center">
            <User className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-indigo-300" />
          </div>
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <div className="absolute right-0 top-full mt-2 w-48 bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl py-1.5 z-20" data-testid="user-menu-dropdown">
              <button onClick={() => { setOpen(false); navigate('/app/profile'); }} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors" data-testid="menu-profile">
                <User className="w-4 h-4" /> Profile
              </button>
              <button onClick={() => { setOpen(false); navigate('/app/billing'); }} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors" data-testid="menu-billing">
                <CreditCard className="w-4 h-4" /> Billing
              </button>
              <button onClick={() => { setOpen(false); navigate('/app/settings'); }} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors" data-testid="menu-settings">
                <Settings className="w-4 h-4" /> Settings
              </button>
              <div className="h-px bg-white/5 my-1" />
              <button onClick={() => { setOpen(false); navigate('/help'); }} className="w-full text-left px-4 py-2.5 text-sm text-slate-400 hover:bg-white/5 hover:text-white transition-colors" data-testid="menu-help">
                Help
              </button>
              <button onClick={() => { setOpen(false); navigate('/contact'); }} className="w-full text-left px-4 py-2.5 text-sm text-slate-400 hover:bg-white/5 hover:text-white transition-colors" data-testid="menu-support">
                Support
              </button>
              <div className="h-px bg-white/5 my-1" />
              <button onClick={handleLogout} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors" data-testid="menu-logout">
                <LogOut className="w-4 h-4" /> Logout
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
