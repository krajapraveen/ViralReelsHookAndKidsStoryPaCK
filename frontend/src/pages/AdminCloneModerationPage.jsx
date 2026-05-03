import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ShieldAlert, CheckCircle2, XCircle, Power, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeaders = (extra = {}) => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, ...extra });

function Section({ title, count, children, testId }) {
  return (
    <section className="space-y-3" data-testid={testId}>
      <div className="flex items-baseline gap-2">
        <h2 className="text-lg font-bold text-white">{title}</h2>
        <span className="text-xs text-slate-500">({count})</span>
      </div>
      {children}
    </section>
  );
}

export default function AdminCloneModerationPage() {
  const nav = useNavigate();
  const [pending, setPending] = useState([]);
  const [clones, setClones] = useState([]);
  const [reports, setReports] = useState([]);
  const [busy, setBusy] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(async () => {
    try {
      const [p, c, r] = await Promise.all([
        fetch(`${API}/api/avatar/admin/consents/pending`, { headers: authHeaders() }).then(x => x.json()),
        fetch(`${API}/api/avatar/admin/clones`, { headers: authHeaders() }).then(x => x.json()),
        fetch(`${API}/api/avatar/admin/abuse-reports`, { headers: authHeaders() }).then(x => x.json()),
      ]);
      setPending(p.consents || []);
      setClones(c.clones || []);
      setReports(r.reports || []);
    } catch (e) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const action = async (cloneId, act, notes = '') => {
    setBusy(`${cloneId}:${act}`); setErr(null);
    try {
      const r = await fetch(`${API}/api/avatar/admin/clones/${cloneId}/action`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: act, notes }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Action failed');
      await load();
    } catch (e) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const reportAction = async (id, status, notes = '') => {
    setBusy(`r:${id}:${status}`); setErr(null);
    try {
      const r = await fetch(`${API}/api/avatar/admin/abuse-reports/${id}/action`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ status, notes }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Action failed');
      await load();
    } catch (e) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-white" data-testid="avatar-admin-page">
      <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => nav('/app/avatar')}
                  className="text-slate-300 hover:text-white flex items-center gap-1.5 text-sm"
                  data-testid="avatar-admin-back">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="ml-auto flex items-center gap-2 text-xs text-amber-300">
            <ShieldAlert className="w-3.5 h-3.5" /> Admin moderation
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6 space-y-8">
        {err && <div className="text-xs text-rose-300 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30" data-testid="avatar-admin-error">{err}</div>}

        <Section title="Pending consents" count={pending.length} testId="avatar-admin-pending">
          {pending.length === 0 ? (
            <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] text-slate-500 text-sm">No pending consents.</div>
          ) : (
            <ul className="space-y-3">
              {pending.map(c => (
                <li key={c.id} className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5" data-testid={`avatar-admin-consent-${c.id}`}>
                  <div className="text-xs text-slate-400 mb-1">Clone {c.clone_id} · User {c.user_id}</div>
                  <div className="text-sm text-slate-200 mb-2"><strong className="text-amber-200">Phrase:</strong> "{c.consent_phrase_text}"</div>
                  <div className="text-xs text-slate-500 mb-3">Video: {c.selfie_video_url} · {c.selfie_video_size_bytes} bytes</div>
                  <div className="flex gap-2 flex-wrap">
                    <button onClick={() => action(c.clone_id, 'approve_consent', 'admin reviewed')}
                            disabled={!!busy}
                            className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-200 text-xs font-bold border border-emerald-500/40 disabled:opacity-50"
                            data-testid={`avatar-admin-approve-${c.clone_id}`}>
                      <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" /> Approve
                    </button>
                    <button onClick={() => action(c.clone_id, 'reject_consent', 'admin rejected')}
                            disabled={!!busy}
                            className="px-3 py-2 rounded-lg bg-rose-500/20 text-rose-200 text-xs font-bold border border-rose-500/40 disabled:opacity-50"
                            data-testid={`avatar-admin-reject-${c.clone_id}`}>
                      <XCircle className="w-3.5 h-3.5 inline mr-1" /> Reject
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="All clones" count={clones.length} testId="avatar-admin-clones">
          {clones.length === 0 ? (
            <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] text-slate-500 text-sm">No clones yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs text-slate-500 uppercase tracking-wider">
                  <tr>
                    <th className="text-left py-2 pr-3">Name</th>
                    <th className="text-left py-2 pr-3">Type</th>
                    <th className="text-left py-2 pr-3">Status</th>
                    <th className="text-left py-2 pr-3">User</th>
                    <th className="text-right py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {clones.map(c => (
                    <tr key={c.id} className="border-t border-white/5" data-testid={`avatar-admin-clone-${c.id}`}>
                      <td className="py-2 pr-3 font-semibold text-white">{c.clone_name}</td>
                      <td className="py-2 pr-3 text-slate-400">{c.clone_type}</td>
                      <td className="py-2 pr-3 text-slate-300">{c.status}</td>
                      <td className="py-2 pr-3 text-slate-500 text-xs">{(c.user_id || '').slice(0, 8)}…</td>
                      <td className="py-2 text-right">
                        {c.status === 'disabled' ? (
                          <button onClick={() => action(c.id, 'enable_clone', 'admin re-enabled')}
                                  disabled={!!busy}
                                  className="px-2.5 py-1.5 rounded-md bg-emerald-500/20 text-emerald-200 text-[11px] font-bold border border-emerald-500/40 disabled:opacity-50"
                                  data-testid={`avatar-admin-enable-${c.id}`}>
                            Enable
                          </button>
                        ) : (
                          <button onClick={() => action(c.id, 'disable_clone', 'admin disabled')}
                                  disabled={!!busy}
                                  className="px-2.5 py-1.5 rounded-md bg-rose-500/20 text-rose-200 text-[11px] font-bold border border-rose-500/40 disabled:opacity-50"
                                  data-testid={`avatar-admin-disable-${c.id}`}>
                            <Power className="w-3 h-3 inline mr-1" /> Disable
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section title="Abuse reports" count={reports.length} testId="avatar-admin-reports">
          {reports.length === 0 ? (
            <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] text-slate-500 text-sm">No reports.</div>
          ) : (
            <ul className="space-y-3">
              {reports.map(r => (
                <li key={r.id} className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/5" data-testid={`avatar-admin-report-${r.id}`}>
                  <div className="flex items-start gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-rose-300 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-xs text-slate-400">Status: <span className="font-semibold text-rose-200">{r.status}</span> · Reporter {(r.reporter_user_id || '').slice(0, 8)}…</div>
                      <div className="text-sm text-slate-200 mt-1">{r.reason}</div>
                    </div>
                  </div>
                  {r.status === 'open' && (
                    <div className="flex gap-2 flex-wrap">
                      <button onClick={() => reportAction(r.id, 'reviewing')} disabled={!!busy}
                              className="px-2.5 py-1.5 rounded-md bg-amber-500/20 text-amber-200 text-[11px] font-bold border border-amber-500/40 disabled:opacity-50"
                              data-testid={`avatar-admin-report-reviewing-${r.id}`}>Mark reviewing</button>
                      <button onClick={() => reportAction(r.id, 'actioned')} disabled={!!busy}
                              className="px-2.5 py-1.5 rounded-md bg-emerald-500/20 text-emerald-200 text-[11px] font-bold border border-emerald-500/40 disabled:opacity-50"
                              data-testid={`avatar-admin-report-actioned-${r.id}`}>Actioned</button>
                      <button onClick={() => reportAction(r.id, 'rejected')} disabled={!!busy}
                              className="px-2.5 py-1.5 rounded-md bg-slate-500/20 text-slate-200 text-[11px] font-bold border border-slate-500/40 disabled:opacity-50"
                              data-testid={`avatar-admin-report-rejected-${r.id}`}>Reject</button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </main>
    </div>
  );
}
