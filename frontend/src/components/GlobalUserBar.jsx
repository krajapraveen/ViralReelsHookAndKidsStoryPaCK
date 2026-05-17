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
    // P0 2026-05-19 — Shared global user bar layout hardening.
    //
    // Production screenshot showed page title text ("Preview & Generate"
    // / "pe…") bleeding visibly THROUGH the bell + credits pills because
    // the previous bg-black/40 + bg-black/60 backgrounds were transparent
    // enough for content underneath to read through, even though z-index
    // sat correctly above. The two pills also appeared to visually
    // collide at tight widths because backdrop-blur halos overlapped the
    // 6 px sibling gap.
    //
    // Structural fixes (defensive, applied in the SHARED component, not
    // page-by-page):
    //   1. `pointer-events-none` on the outer wrapper so dead areas
    //      between pills never steal clicks from underlying page UI.
    //      Each interactive pill re-enables pointer events.
    //   2. `flex-nowrap` so the cluster NEVER wraps onto a second row
    //      at any viewport.
    //   3. `gap-2 sm:gap-2.5` — slightly larger gap so the backdrop-blur
    //      halos of the two pills can't visually merge.
    //   4. Both pills use SOLID `bg-slate-950/95` (was `bg-black/40`
    //      and `bg-black/60`) → backdrop-blur preserved for aesthetic,
    //      but the alpha is high enough that any underlying page
    //      content is fully visually masked.
    //   5. `flex-shrink-0` on both pills so they never compress on
    //      narrow viewports — overflow is preferable to a collapsed,
    //      unreadable cluster.
    //   6. Hard `max-w-[calc(100vw-1rem)]` cap so on the smallest
    //      mobile widths the bar can never push horizontal scroll.
    //
    // The shared bar is `fixed top-0 right-0`. It is NOT a flex header
    // sibling to page content. Page titles render BELOW it in the DOM,
    // not next to it — so the canonical "flex-1 min-w-0 truncate" rule
    // doesn't apply here. What DOES apply is hard visual opacity so the
    // bar never lets page content bleed through, plus zero-overlap
    // sibling layout inside the cluster itself.
    <div
      className={`fixed ${isAdmin ? 'top-[52px]' : 'top-0'} right-0 z-[10002] p-2 sm:p-3 max-w-[calc(100vw-0.5rem)] pointer-events-none`}
      data-testid="global-user-bar"
    >
      <div className="relative flex items-center justify-end flex-nowrap gap-2 sm:gap-2.5 overflow-visible">
        <div className="pointer-events-auto flex-shrink-0">
          <NotificationBell />
        </div>
        <button
          onClick={() => setOpen(prev => !prev)}
          className="pointer-events-auto flex-shrink-0 flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-full border border-white/10 bg-slate-950/95 backdrop-blur-xl hover:bg-slate-900 transition-colors shadow-lg shadow-black/40"
          data-testid="user-menu-toggle"
          aria-label="User menu"
        >
          <Zap className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-amber-400 flex-shrink-0" />
          <span className="text-[11px] sm:text-xs font-medium text-white flex-shrink-0">{credits >= 99999 ? '∞' : (credits ?? '...')}</span>
          <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-indigo-500/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0">
            <User className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-indigo-300" />
          </div>
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-10 pointer-events-auto" onClick={() => setOpen(false)} />
            <div className="absolute right-0 top-full mt-2 w-48 bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl py-1.5 z-20 pointer-events-auto" data-testid="user-menu-dropdown">
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
