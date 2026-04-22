import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import {
  LayoutDashboard, Users, Film, CreditCard, BarChart3,
  Shield, Server, Settings, LogOut, ChevronRight, ChevronDown,
  Activity, Eye, FileText, Heart, Zap, BookOpen, Star, TrendingUp,
  Lock, AlertTriangle, Clock, Monitor, Cpu, Radio, Sparkles,
  Menu, X, ArrowLeft, Target, MessageSquare
} from 'lucide-react';

const NAV_GROUPS = [
  {
    label: 'Overview',
    items: [
      { path: '/app/admin', label: 'Dashboard', icon: LayoutDashboard, exact: true },
      { path: '/app/admin/production-metrics', label: 'Production Metrics', icon: Target },
    ],
  },
  {
    label: 'Users',
    items: [
      { path: '/app/admin/users', label: 'User Management', icon: Users },
      { path: '/app/admin/user-analytics', label: 'User Analytics', icon: BarChart3 },
      { path: '/app/admin/user-activity', label: 'User Activity', icon: Activity },
      { path: '/app/admin/login-activity', label: 'Login Activity', icon: Eye },
      { path: '/app/admin/account-locks', label: 'Account Locks', icon: Lock },
    ],
  },
  {
    label: 'Content Engine',
    items: [
      { path: '/app/admin/content-engine', label: 'Seed Content', icon: Sparkles },
      { path: '/app/admin/story-video-analytics', label: 'Story Analytics', icon: Film },
      { path: '/app/admin/bio-templates', label: 'Templates', icon: FileText },
      { path: '/app/admin/leaderboard', label: 'Leaderboard', icon: Star },
      { path: '/app/admin/template-analytics', label: 'Template Analytics', icon: TrendingUp },
    ],
  },
  {
    label: 'Jobs & Pipelines',
    items: [
      { path: '/app/admin/workers', label: 'Worker Dashboard', icon: Cpu },
      { path: '/app/admin/automation', label: 'Automation', icon: Zap },
      { path: '/app/admin/ttfd-analytics', label: 'TTFD Analytics', icon: Clock },
    ],
  },
  {
    label: 'Revenue & Credits',
    items: [
      { path: '/app/admin/revenue', label: 'Revenue Analytics', icon: CreditCard },
      { path: '/app/admin/growth', label: 'Growth Metrics', icon: TrendingUp },
    ],
  },
  {
    label: 'Analytics',
    items: [
      { path: '/app/admin/realtime-analytics', label: 'Realtime Analytics', icon: BarChart3 },
      { path: '/app/admin/daily-report', label: 'Daily Report', icon: BookOpen },
      { path: '/app/admin/feedback', label: 'User Feedback', icon: MessageSquare },
      { path: '/app/admin/ga4-tester', label: 'GA4 Event Tester', icon: Radio },
    ],
  },
  {
    label: 'System Health',
    items: [
      { path: '/app/admin/system-health', label: 'System Health', icon: Heart },
      { path: '/app/admin/performance', label: 'Performance', icon: Activity },
      { path: '/app/admin/monitoring', label: 'Monitoring', icon: Monitor },
      { path: '/app/admin/environment-monitor', label: 'Environment', icon: Server },
      { path: '/app/admin/self-healing', label: 'Self-Healing', icon: Radio },
    ],
  },
  {
    label: 'Security',
    items: [
      { path: '/app/admin/security', label: 'Security Dashboard', icon: Shield },
      { path: '/app/admin/security-reports', label: 'Vulnerability Reports', icon: Shield },
      { path: '/app/admin/referrals', label: 'Referral Program', icon: Users },
      { path: '/app/admin/anti-abuse', label: 'Anti-Abuse', icon: AlertTriangle },
      { path: '/app/admin/audit-logs', label: 'Audit Logs', icon: FileText },
    ],
  },
];

function parseJwtRole(token) {
  try {
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload));
    return decoded.role || '';
  } catch {
    return '';
  }
}

function NavItem({ item, isActive, badge }) {
  const Icon = item.icon;
  return (
    <Link to={item.path} data-testid={`admin-nav-${item.label.replace(/\s/g, '-').toLowerCase()}`}>
      <div className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all cursor-pointer ${
        isActive
          ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/20'
          : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
      }`}>
        <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-indigo-400' : ''}`} />
        <span className="truncate">{item.label}</span>
        {badge > 0 && (
          <span className="ml-auto px-1.5 py-0.5 text-[10px] font-bold bg-red-500 text-white rounded-full min-w-[18px] text-center" data-testid="feedback-unread-badge">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
      </div>
    </Link>
  );
}

function NavGroup({ group, location, defaultOpen, feedbackUnread }) {
  const [open, setOpen] = useState(defaultOpen);
  const hasActive = group.items.some(item =>
    item.exact ? location.pathname === item.path : location.pathname.startsWith(item.path)
  );

  return (
    <div className="mb-1" data-testid={`admin-nav-group-${group.label.replace(/\s/g, '-').toLowerCase()}`}>
      <button
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${
          hasActive ? 'text-indigo-400/70' : 'text-slate-600'
        } hover:text-slate-400 transition-colors`}
      >
        {group.label}
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>
      {open && (
        <div className="space-y-0.5 mt-0.5">
          {group.items.map(item => {
            const isActive = item.exact
              ? location.pathname === item.path
              : location.pathname.startsWith(item.path);
            const badge = item.path === '/app/admin/feedback' ? feedbackUnread : 0;
            return <NavItem key={item.path} item={item} isActive={isActive} badge={badge} />;
          })}
        </div>
      )}
    </div>
  );
}

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authState, setAuthState] = useState('checking');
  const [feedbackUnread, setFeedbackUnread] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }
    const role = parseJwtRole(token);
    if (role.toUpperCase() === 'ADMIN' || role.toUpperCase() === 'SUPERADMIN') {
      setAuthState('authorized');
    } else {
      setAuthState('unauthorized');
      navigate('/app', { replace: true });
    }
  }, [navigate]);

  // Fetch unread feedback count
  useEffect(() => {
    if (authState !== 'authorized') return;
    const fetchUnread = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/feedback/unread-count`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (data.success) setFeedbackUnread(data.data.unread_count);
      } catch {}
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60000);
    return () => clearInterval(interval);
  }, [authState]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  if (authState === 'checking') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <div className="flex items-center gap-3 text-slate-400">
          <div className="w-5 h-5 border-2 border-slate-600 border-t-indigo-400 rounded-full animate-spin" />
          <span className="text-sm">Verifying access...</span>
        </div>
      </div>
    );
  }

  if (authState === 'unauthorized') return null;

  const sidebar = (
    <div className="flex flex-col h-full">
      {/* Logo / Title */}
      <div className="px-4 py-4 border-b border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center">
            <Shield className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white leading-none">Admin</h1>
            <p className="text-[10px] text-slate-500 mt-0.5">Control Center</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5 scrollbar-thin" data-testid="admin-sidebar-nav">
        {NAV_GROUPS.map((group, idx) => {
          const hasActive = group.items.some(item =>
            item.exact ? location.pathname === item.path : location.pathname.startsWith(item.path)
          );
          return (
            <NavGroup
              key={group.label}
              group={group}
              location={location}
              defaultOpen={idx === 0 || hasActive}
              feedbackUnread={feedbackUnread}
            />
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-slate-800/60 space-y-1">
        <Link to="/app" data-testid="admin-nav-back-to-app">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-slate-500 hover:text-white hover:bg-white/[0.04] transition-all cursor-pointer">
            <ArrowLeft className="w-4 h-4" /> Back to App
          </div>
        </Link>
        <button onClick={handleLogout} className="w-full" data-testid="admin-nav-logout">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-red-400/60 hover:text-red-400 hover:bg-red-500/[0.06] transition-all cursor-pointer">
            <LogOut className="w-4 h-4" /> Logout
          </div>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-slate-950" data-testid="admin-layout">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col w-[240px] bg-slate-900/50 border-r border-slate-800/40 fixed inset-y-0 left-0 z-40" data-testid="admin-sidebar">
        {sidebar}
      </aside>

      {/* Mobile menu button */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="lg:hidden fixed top-3 left-3 z-50 w-9 h-9 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-center text-white"
        data-testid="admin-mobile-menu"
      >
        {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
      </button>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <>
          <div className="lg:hidden fixed inset-0 bg-black/60 z-40" onClick={() => setMobileOpen(false)} />
          <aside className="lg:hidden fixed inset-y-0 left-0 w-[260px] bg-slate-900 border-r border-slate-800 z-50" data-testid="admin-mobile-sidebar">
            {sidebar}
          </aside>
        </>
      )}

      {/* Main content */}
      <main className="flex-1 lg:ml-[240px] min-h-screen" data-testid="admin-content">
        <Outlet />
      </main>

      <style>{`
        .scrollbar-thin::-webkit-scrollbar{width:4px}
        .scrollbar-thin::-webkit-scrollbar-track{background:transparent}
        .scrollbar-thin::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.05);border-radius:4px}
        .scrollbar-thin::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.1)}
      `}</style>
    </div>
  );
}
