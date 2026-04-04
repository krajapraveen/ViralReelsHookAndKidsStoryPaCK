import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Shield, AlertTriangle, Eye, Download, Lock, Unlock, RefreshCw, User, Activity } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function useAdminFetch(path, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setData(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => { fetch_(); }, [fetch_]);
  return { data, loading, refresh: fetch_ };
}

function StatCard({ icon: Icon, label, value, color = 'text-white' }) {
  return (
    <Card className="bg-zinc-900 border-zinc-800" data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <CardContent className="p-4 flex items-center gap-3">
        <Icon className={`w-5 h-5 ${color}`} />
        <div>
          <p className="text-xs text-zinc-500 uppercase tracking-wider">{label}</p>
          <p className={`text-xl font-bold ${color}`}>{value ?? '—'}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function FlagRow({ flag, onResolve }) {
  return (
    <div className="flex items-center justify-between p-3 bg-zinc-900 rounded border border-zinc-800" data-testid={`flag-${flag.flag_id}`}>
      <div className="flex-1">
        <span className={`text-xs px-2 py-0.5 rounded ${flag.severity === 'high' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}>
          {flag.severity || 'medium'}
        </span>
        <span className="text-sm text-zinc-300 ml-2">{flag.reason}</span>
        <span className="text-xs text-zinc-500 ml-2">User: {flag.user_id?.slice(0, 8)}...</span>
        <span className="text-xs text-zinc-600 ml-2">{flag.created_at?.slice(0, 19)}</span>
      </div>
      {flag.status === 'open' && (
        <Button size="sm" variant="outline" onClick={() => onResolve(flag.flag_id)} className="text-xs" data-testid={`resolve-${flag.flag_id}`}>
          Resolve
        </Button>
      )}
    </div>
  );
}

function EventRow({ event }) {
  return (
    <div className="flex items-center gap-3 p-2 text-xs border-b border-zinc-800/50">
      <span className={`px-1.5 py-0.5 rounded ${event.action?.includes('denied') || event.action?.includes('rate') ? 'bg-red-900/60 text-red-400' : 'bg-zinc-800 text-zinc-400'}`}>
        {event.action}
      </span>
      <span className="text-zinc-500 w-24 truncate">{event.user_id?.slice(0, 12)}</span>
      <span className="text-zinc-600 w-28 truncate">{event.ip}</span>
      <span className="text-zinc-600 flex-1 truncate">{event.user_agent?.slice(0, 40)}</span>
      <span className="text-zinc-600 w-20">{event.timestamp?.slice(11, 19)}</span>
    </div>
  );
}

export default function MediaSecurityDashboard() {
  const [hours, setHours] = useState(24);
  const [selectedUser, setSelectedUser] = useState(null);
  const { data: overview, loading, refresh } = useAdminFetch(`/api/admin/media/overview?hours=${hours}`, [hours]);
  const { data: flags, refresh: refreshFlags } = useAdminFetch('/api/admin/media/abuse-flags?status=open');
  const { data: events, refresh: refreshEvents } = useAdminFetch(`/api/admin/media/access-events?hours=${hours}&limit=50`, [hours]);
  const { data: userDetail, loading: userLoading } = useAdminFetch(
    selectedUser ? `/api/admin/media/user/${selectedUser}` : null, [selectedUser]
  );

  const adminAction = async (endpoint, body) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API}${endpoint}`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  };

  const handleResolve = async (flagId) => {
    await adminAction('/api/admin/media/flags/resolve', { flag_id: flagId });
    refreshFlags();
  };

  const handleRevoke = async (userId) => {
    await adminAction('/api/admin/media/tokens/revoke', { user_id: userId, reason: 'manual_revoke' });
    refresh();
  };

  const handleSuspend = async (userId) => {
    await adminAction('/api/admin/media/users/suspend-media', { user_id: userId, duration_minutes: 60, reason: 'manual_suspend' });
    refresh();
  };

  const handleUnsuspend = async (userId) => {
    await adminAction('/api/admin/media/users/unsuspend-media', { user_id: userId });
    refresh();
  };

  return (
    <div className="space-y-6" data-testid="media-security-dashboard">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-red-400" />
          <h1 className="text-xl font-bold text-white">Media Security</h1>
        </div>
        <div className="flex items-center gap-2">
          {[1, 6, 24, 72].map(h => (
            <Button key={h} size="sm" variant={hours === h ? 'default' : 'ghost'}
              onClick={() => setHours(h)} className="text-xs" data-testid={`hours-${h}`}>
              {h}h
            </Button>
          ))}
          <Button size="sm" variant="ghost" onClick={() => { refresh(); refreshFlags(); refreshEvents(); }} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      {!loading && overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard icon={Activity} label="Actions" value={Object.values(overview.action_summary || {}).reduce((s, a) => s + a.count, 0)} />
          <StatCard icon={Download} label="Downloads" value={overview.action_summary?.download_token_issued?.count || 0} />
          <StatCard icon={AlertTriangle} label="Denied" value={overview.denied_events} color="text-red-400" />
          <StatCard icon={Shield} label="Flags" value={overview.open_abuse_flags} color={overview.open_abuse_flags > 0 ? 'text-red-400' : 'text-green-400'} />
          <StatCard icon={Eye} label="Tokens" value={overview.active_tokens} />
          <StatCard icon={User} label="Sessions" value={overview.active_sessions} />
          <StatCard icon={Lock} label="Suspensions" value={overview.active_suspensions} color={overview.active_suspensions > 0 ? 'text-yellow-400' : 'text-white'} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top Risk Users */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-zinc-400">Top Risk Users</CardTitle></CardHeader>
          <CardContent className="space-y-2" data-testid="top-risk-users">
            {overview?.top_risk_users?.map((u, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-zinc-800/50 rounded text-sm">
                <button className="text-blue-400 hover:underline text-xs" onClick={() => setSelectedUser(u.user_id)} data-testid={`risk-user-${i}`}>
                  {u.user_id?.slice(0, 12)}...
                </button>
                <div className="flex items-center gap-2">
                  <span className="text-zinc-400">{u.downloads} DLs</span>
                  <Button size="sm" variant="ghost" className="h-6 text-xs text-yellow-400" onClick={() => handleRevoke(u.user_id)} data-testid={`revoke-${i}`}>
                    Revoke
                  </Button>
                  <Button size="sm" variant="ghost" className="h-6 text-xs text-red-400" onClick={() => handleSuspend(u.user_id)} data-testid={`suspend-${i}`}>
                    Suspend
                  </Button>
                </div>
              </div>
            ))}
            {(!overview?.top_risk_users || overview.top_risk_users.length === 0) && (
              <p className="text-zinc-600 text-xs">No download activity</p>
            )}
          </CardContent>
        </Card>

        {/* Abuse Flags */}
        <Card className="bg-zinc-900 border-zinc-800 lg:col-span-2">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-zinc-400">Open Abuse Flags ({flags?.count || 0})</CardTitle></CardHeader>
          <CardContent className="space-y-2 max-h-64 overflow-y-auto" data-testid="abuse-flags">
            {flags?.flags?.map(f => <FlagRow key={f.flag_id} flag={f} onResolve={handleResolve} />)}
            {(!flags?.flags || flags.flags.length === 0) && (
              <p className="text-green-500 text-xs">No open flags</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* User Investigation Panel */}
      {selectedUser && (
        <Card className="bg-zinc-900 border-zinc-800" data-testid="user-investigation">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm text-zinc-400">User Investigation: {selectedUser.slice(0, 12)}...</CardTitle>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" className="text-xs text-yellow-400" onClick={() => handleRevoke(selectedUser)} data-testid="investigate-revoke">
                Revoke All
              </Button>
              <Button size="sm" variant="ghost" className="text-xs text-red-400" onClick={() => handleSuspend(selectedUser)} data-testid="investigate-suspend">
                Suspend
              </Button>
              {userDetail?.active_suspension && (
                <Button size="sm" variant="ghost" className="text-xs text-green-400" onClick={() => handleUnsuspend(selectedUser)} data-testid="investigate-unsuspend">
                  <Unlock className="w-3 h-3 mr-1" /> Unsuspend
                </Button>
              )}
              <Button size="sm" variant="ghost" className="text-xs" onClick={() => setSelectedUser(null)}>Close</Button>
            </div>
          </CardHeader>
          <CardContent>
            {!userLoading && userDetail && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                <div className="bg-zinc-800/50 p-2 rounded">
                  <span className="text-zinc-500">Email</span>
                  <p className="text-white">{userDetail.user?.email}</p>
                </div>
                <div className="bg-zinc-800/50 p-2 rounded">
                  <span className="text-zinc-500">Sessions</span>
                  <p className="text-white">{userDetail.sessions?.length}</p>
                </div>
                <div className="bg-zinc-800/50 p-2 rounded">
                  <span className="text-zinc-500">Tokens (24h)</span>
                  <p className="text-white">{userDetail.tokens_24h?.length}</p>
                </div>
                <div className="bg-zinc-800/50 p-2 rounded">
                  <span className="text-zinc-500">Unique IPs</span>
                  <p className="text-white">{userDetail.unique_ips_24h}</p>
                </div>
                <div className="bg-zinc-800/50 p-2 rounded">
                  <span className="text-zinc-500">Flags</span>
                  <p className={userDetail.flags?.length > 0 ? 'text-red-400' : 'text-green-400'}>{userDetail.flags?.length}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Access Events */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-zinc-400">Recent Access Events</CardTitle></CardHeader>
        <CardContent className="max-h-80 overflow-y-auto" data-testid="access-events">
          <div className="flex items-center gap-3 p-2 text-xs border-b border-zinc-700 text-zinc-500 font-medium">
            <span className="w-32">Action</span>
            <span className="w-24">User</span>
            <span className="w-28">IP</span>
            <span className="flex-1">User Agent</span>
            <span className="w-20">Time</span>
          </div>
          {events?.events?.map((e, i) => <EventRow key={i} event={e} />)}
          {(!events?.events || events.events.length === 0) && (
            <p className="text-zinc-600 text-xs p-3">No events in this window</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
