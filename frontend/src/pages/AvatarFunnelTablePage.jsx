import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, BarChart3, CheckCircle2, XCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AvatarFunnelTablePage() {
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    fetch(`${API}/api/avatar/admin/funnel-table?days=14`, {
      headers: { Authorization: `Bearer ${t}` },
    })
      .then(async r => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch(e => setErr(String(e.message || e)));
  }, []);

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-white" data-testid="avatar-funnel-page">
      <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => nav('/app/avatar')}
                  className="text-slate-300 hover:text-white flex items-center gap-1.5 text-sm"
                  data-testid="avatar-funnel-back">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-300">
            <BarChart3 className="w-3.5 h-3.5" /> Avatar funnel — last 14 days
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {err && (
          <div className="text-xs text-rose-300 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30"
               data-testid="avatar-funnel-error">
            Could not load funnel: {err}
          </div>
        )}

        {data?.day7_gate && (
          <div className="p-4 rounded-2xl border border-white/10 bg-white/[0.03] space-y-2"
               data-testid="avatar-funnel-day7-gate">
            <h2 className="text-base font-bold text-white">Day-7 decision gate</h2>
            <ul className="text-sm space-y-1">
              <GateRow label="≥ 20 users complete full flow"
                       value={data.day7_gate.users_completed_full_flow}
                       pass={data.day7_gate.users_completed_full_flow >= 20} />
              <GateRow label="≥ 5 users repeat usage"
                       value={data.day7_gate.users_repeated}
                       pass={data.day7_gate.users_repeated >= 5} />
              <GateRow label="≥ 1 organic share"
                       value={data.day7_gate.organic_shares}
                       pass={data.day7_gate.organic_shares >= 1} />
            </ul>
            <div className={`mt-2 text-sm font-bold ${data.day7_gate.passes_gate ? 'text-emerald-300' : 'text-amber-300'}`}
                 data-testid="avatar-funnel-day7-verdict">
              {data.day7_gate.passes_gate
                ? 'GATE PASSES — Phase 2 unlocked.'
                : 'GATE NOT MET — keep distributing or kill/pivot per directive.'}
            </div>
          </div>
        )}

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white">Daily rows</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="avatar-funnel-table">
              <thead className="text-xs text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="text-left py-2 pr-3">Day</th>
                  <th className="text-right py-2 px-2">Views</th>
                  <th className="text-right py-2 px-2">Demo plays</th>
                  <th className="text-right py-2 px-2">Signups</th>
                  <th className="text-right py-2 px-2">Consents</th>
                  <th className="text-right py-2 px-2">First exports</th>
                  <th className="text-right py-2 px-2">Repeats</th>
                  <th className="text-right py-2 px-2">Shares</th>
                </tr>
              </thead>
              <tbody>
                {(data?.rows || []).map(r => (
                  <tr key={r.day} className="border-t border-white/5"
                      data-testid={`avatar-funnel-row-${r.day}`}>
                    <td className="py-2 pr-3 font-mono text-slate-400 text-xs">{r.day}</td>
                    <td className="py-2 px-2 text-right">{r.views}</td>
                    <td className="py-2 px-2 text-right">{r.demo_plays}</td>
                    <td className="py-2 px-2 text-right">{r.signups}</td>
                    <td className="py-2 px-2 text-right">{r.consents}</td>
                    <td className="py-2 px-2 text-right text-emerald-300">{r.first_exports}</td>
                    <td className="py-2 px-2 text-right text-fuchsia-300">{r.repeats}</td>
                    <td className="py-2 px-2 text-right text-amber-300">{r.shares}</td>
                  </tr>
                ))}
              </tbody>
              {data?.last7_totals && (
                <tfoot>
                  <tr className="border-t border-white/20 font-bold text-xs">
                    <td className="py-2 pr-3 text-slate-400">last 7 totals</td>
                    <td className="py-2 px-2 text-right">{data.last7_totals.views}</td>
                    <td className="py-2 px-2 text-right">{data.last7_totals.demo_plays}</td>
                    <td className="py-2 px-2 text-right">{data.last7_totals.signups}</td>
                    <td className="py-2 px-2 text-right">{data.last7_totals.consents}</td>
                    <td className="py-2 px-2 text-right text-emerald-300">{data.last7_totals.first_exports}</td>
                    <td className="py-2 px-2 text-right text-fuchsia-300">{data.last7_totals.repeats}</td>
                    <td className="py-2 px-2 text-right text-amber-300">{data.last7_totals.shares}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
          <p className="text-xs text-slate-500">No charts. No fluff. Just numbers.</p>
        </section>
      </main>
    </div>
  );
}

function GateRow({ label, value, pass }) {
  return (
    <li className="flex items-center gap-2">
      {pass ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-rose-400" />}
      <span className={pass ? 'text-emerald-200' : 'text-slate-300'}>{label}</span>
      <span className="ml-auto text-slate-400 font-mono">{value}</span>
    </li>
  );
}
