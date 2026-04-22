import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  ArrowLeft, RefreshCw, Shield, Clock, User, FileText, Paperclip,
  Award, MessageSquare, Send, CheckCircle, XCircle,
} from 'lucide-react';

const STATUS_VALUES = ['NEW', 'ACKNOWLEDGED', 'TRIAGING', 'NEED_MORE_INFO', 'ACCEPTED', 'DUPLICATE', 'OUT_OF_SCOPE', 'INFORMATIVE', 'RESOLVED', 'CLOSED'];
const SEVERITY_VALUES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export default function AdminSecurityReportDetail() {
  const { report_id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noteText, setNoteText] = useState('');
  const [saving, setSaving] = useState(false);
  const [showGrant, setShowGrant] = useState(false);
  const [grantCredits, setGrantCredits] = useState('');
  const [grantReason, setGrantReason] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/security/admin/reports/${report_id}`);
      setData(data);
    } catch (e) {
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  }, [report_id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const patch = async (updates, successMsg) => {
    setSaving(true);
    try {
      await api.patch(`/api/security/admin/reports/${report_id}`, updates);
      toast.success(successMsg || 'Updated');
      fetchData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  const addNote = async () => {
    if (!noteText.trim()) return;
    setSaving(true);
    try {
      await api.post(`/api/security/admin/reports/${report_id}/notes`, { note: noteText.trim() });
      setNoteText('');
      toast.success('Note added');
      fetchData();
    } catch (e) {
      toast.error('Failed to add note');
    } finally {
      setSaving(false);
    }
  };

  const grantReward = async () => {
    setSaving(true);
    try {
      const payload = { reason: grantReason };
      if (grantCredits) payload.credits = Number(grantCredits);
      const { data } = await api.post(`/api/security/admin/reports/${report_id}/grant-reward`, payload);
      toast.success(`Granted ${data.credits} credits${data.has_account ? '' : ' (claim link generated)'}`);
      setShowGrant(false);
      setGrantCredits('');
      setGrantReason('');
      fetchData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Grant failed');
    } finally {
      setSaving(false);
    }
  };

  const rejectReward = async () => {
    if (!window.confirm('Mark reward as rejected?')) return;
    setSaving(true);
    try {
      await api.post(`/api/security/admin/reports/${report_id}/reject-reward`, {});
      toast.success('Reward rejected');
      fetchData();
    } catch (e) {
      toast.error('Failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
      </div>
    );
  }

  if (!data?.report) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <p className="text-slate-500">Report not found</p>
      </div>
    );
  }

  const { report, events, notes, attachments } = data;

  return (
    <div className="min-h-screen bg-slate-950 text-white" data-testid="admin-security-report-detail">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
          <Link to="/app/admin/security-reports" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" /> Back to list
          </Link>
          <button onClick={fetchData} className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {/* Title */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <span className="font-mono text-xs text-violet-300 px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/30">{report.report_id}</span>
            <span className={`text-[10px] px-2 py-0.5 rounded border ${sevBorder(report.internal_severity || report.severity)}`}>
              {report.internal_severity || report.severity}
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded border ${statusBorder(report.status)}`}>
              {report.status}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded border border-slate-700 text-slate-400">{report.category}</span>
            {report.is_spam && <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">SPAM FLAGGED</span>}
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{report.subject}</h1>
          <p className="text-xs text-slate-500 mt-1">Received {new Date(report.created_at).toLocaleString()}</p>
        </div>

        <div className="grid lg:grid-cols-[2fr,1fr] gap-6">
          {/* Left column */}
          <div className="space-y-5">
            {/* Reporter */}
            <Panel title="Reporter" icon={User}>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <InfoCell label="Name" value={report.full_name} />
                <InfoCell label="Email" value={report.from_email} />
                <InfoCell label="Consent Accepted" value={report.consent_accepted ? 'Yes' : 'No'} />
                <InfoCell label="Spam Score" value={(report.spam_score ?? 0).toFixed(2)} />
              </div>
            </Panel>

            {/* Body */}
            <Panel title="Report Body" icon={FileText}>
              <pre className="text-[13px] text-slate-200 whitespace-pre-wrap leading-relaxed font-sans" data-testid="report-body">
                {report.body}
              </pre>
            </Panel>

            {/* Attachments */}
            {attachments && attachments.length > 0 && (
              <Panel title="Attachments" icon={Paperclip}>
                <div className="space-y-2">
                  {attachments.map(a => (
                    <div key={a.key} className="flex items-center justify-between bg-slate-800/40 rounded-lg px-3 py-2" data-testid={`attachment-row-${a.key}`}>
                      <span className="text-xs font-mono text-slate-300 truncate">{a.key}</span>
                      {a.url ? (
                        <a href={a.url} target="_blank" rel="noreferrer" className="text-[11px] text-violet-400 hover:text-violet-300 whitespace-nowrap">Open (10m link)</a>
                      ) : <span className="text-[11px] text-slate-600">Unavailable</span>}
                    </div>
                  ))}
                </div>
              </Panel>
            )}

            {/* Timeline */}
            <Panel title="Activity Timeline" icon={Clock}>
              {events.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">No events yet</p>
              ) : (
                <div className="space-y-2.5">
                  {events.map(ev => (
                    <div key={ev.id} className="flex items-start gap-3 text-xs" data-testid={`event-${ev.event_type}`}>
                      <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-1.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-white font-medium">{ev.event_type.replace(/_/g, ' ')}</span>
                          <span className="text-slate-600">· {ev.actor_type}</span>
                          <span className="text-slate-500">{new Date(ev.created_at).toLocaleString()}</span>
                        </div>
                        {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                          <code className="text-[10px] text-slate-500 mt-0.5 block">{JSON.stringify(ev.metadata)}</code>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Panel>

            {/* Notes */}
            <Panel title="Internal Notes" icon={MessageSquare}>
              <div className="space-y-3 mb-4">
                {notes.length === 0 && <p className="text-xs text-slate-500 text-center py-2">No notes yet</p>}
                {notes.map(n => (
                  <div key={n.id} className="bg-slate-800/40 rounded-lg p-3" data-testid={`note-${n.id}`}>
                    <p className="text-sm text-slate-200 whitespace-pre-wrap">{n.note}</p>
                    <p className="text-[10px] text-slate-500 mt-1">{n.created_by_email || 'admin'} · {new Date(n.created_at).toLocaleString()}</p>
                  </div>
                ))}
              </div>
              <div className="flex items-end gap-2">
                <textarea
                  value={noteText}
                  onChange={e => setNoteText(e.target.value)}
                  placeholder="Add an internal note..."
                  rows={2}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-violet-500/50"
                  data-testid="note-input"
                />
                <button
                  onClick={addNote}
                  disabled={saving || !noteText.trim()}
                  className="px-3 py-2 rounded-lg bg-violet-500/20 border border-violet-500/40 text-violet-300 hover:bg-violet-500/30 disabled:opacity-40 text-xs font-medium inline-flex items-center gap-1"
                  data-testid="note-add-btn"
                >
                  <Send className="w-3 h-3" /> Add
                </button>
              </div>
            </Panel>
          </div>

          {/* Right column — controls */}
          <div className="space-y-5">
            <Panel title="Status" icon={Shield}>
              <select
                value={report.status}
                onChange={e => patch({ status: e.target.value }, `Status → ${e.target.value}`)}
                disabled={saving}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                data-testid="status-select"
              >
                {STATUS_VALUES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Panel>

            <Panel title="Internal Severity" icon={Shield}>
              <select
                value={report.internal_severity || ''}
                onChange={e => patch({ internal_severity: e.target.value }, `Severity → ${e.target.value}`)}
                disabled={saving}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                data-testid="severity-select"
              >
                <option value="">Use reported ({report.severity})</option>
                {SEVERITY_VALUES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Panel>

            <Panel title="Assignment" icon={User}>
              <input
                type="text"
                value={report.assigned_to || ''}
                onBlur={e => { if (e.target.value !== (report.assigned_to || '')) patch({ assigned_to: e.target.value }, 'Assigned'); }}
                onChange={() => {}}
                placeholder="admin email or id"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                data-testid="assigned-input"
              />
            </Panel>

            <Panel title="Duplicate Link" icon={FileText}>
              <input
                type="text"
                defaultValue={report.duplicate_of || ''}
                onBlur={e => { if (e.target.value !== (report.duplicate_of || '')) patch({ duplicate_of: e.target.value }, 'Duplicate linked'); }}
                placeholder="VSR-2026-000000"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono"
                data-testid="duplicate-input"
              />
            </Panel>

            <Panel title="Resolution Summary" icon={CheckCircle}>
              <textarea
                defaultValue={report.resolution_summary || ''}
                onBlur={e => { if (e.target.value !== (report.resolution_summary || '')) patch({ resolution_summary: e.target.value }, 'Resolution saved'); }}
                placeholder="What was fixed, when, and how..."
                rows={3}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                data-testid="resolution-input"
              />
            </Panel>

            <Panel title="Reward" icon={Award}>
              <div className="mb-3">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Current</p>
                {report.reward_status === 'GRANTED' ? (
                  <p className="text-emerald-400 text-sm font-semibold">
                    +{report.reward_amount} credits granted
                    {report.reward_claim_link && (
                      <a href={report.reward_claim_link} target="_blank" rel="noreferrer" className="block text-[10px] text-violet-400 mt-1 break-all">{report.reward_claim_link}</a>
                    )}
                  </p>
                ) : report.reward_status === 'REJECTED' ? (
                  <p className="text-slate-500 text-sm">Rejected</p>
                ) : (
                  <p className="text-slate-500 text-sm">None</p>
                )}
              </div>
              {report.reward_status !== 'GRANTED' && (
                <>
                  {!showGrant ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => setShowGrant(true)}
                        className="flex-1 px-3 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 text-xs font-medium inline-flex items-center justify-center gap-1"
                        data-testid="grant-reward-btn"
                      >
                        <Award className="w-3 h-3" /> Grant
                      </button>
                      {report.reward_status !== 'REJECTED' && (
                        <button
                          onClick={rejectReward}
                          className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:bg-slate-700 text-xs inline-flex items-center gap-1"
                          data-testid="reject-reward-btn"
                        >
                          <XCircle className="w-3 h-3" /> Reject
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <input
                        type="number"
                        value={grantCredits}
                        onChange={e => setGrantCredits(e.target.value)}
                        placeholder={`Auto: ${defaultCredits(report.internal_severity || report.severity)}`}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                        data-testid="grant-credits-input"
                      />
                      <input
                        type="text"
                        value={grantReason}
                        onChange={e => setGrantReason(e.target.value)}
                        placeholder="Reason (optional)"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                        data-testid="grant-reason-input"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={grantReward}
                          disabled={saving}
                          className="flex-1 px-3 py-2 rounded-lg bg-emerald-500 text-white hover:bg-emerald-400 disabled:opacity-40 text-xs font-semibold"
                          data-testid="grant-confirm-btn"
                        >
                          Confirm Grant
                        </button>
                        <button
                          onClick={() => setShowGrant(false)}
                          className="px-3 py-2 rounded-lg border border-slate-700 text-slate-400 hover:bg-slate-800 text-xs"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}

function Panel({ title, icon: Icon, children }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
        <Icon className="w-3.5 h-3.5" /> {title}
      </h3>
      {children}
    </div>
  );
}

function InfoCell({ label, value }) {
  return (
    <div>
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
      <p className="text-sm text-white break-all">{value || '—'}</p>
    </div>
  );
}

function defaultCredits(sev) {
  return { LOW: 100, MEDIUM: 300, HIGH: 700, CRITICAL: 1500 }[sev] || 100;
}

function sevBorder(sev) {
  return ({
    LOW: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    MEDIUM: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    HIGH: 'bg-orange-500/10 text-orange-300 border-orange-500/30',
    CRITICAL: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  })[sev] || 'bg-slate-500/10 text-slate-300 border-slate-500/30';
}

function statusBorder(status) {
  return ({
    NEW: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
    ACKNOWLEDGED: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    TRIAGING: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
    NEED_MORE_INFO: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    ACCEPTED: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    DUPLICATE: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
    OUT_OF_SCOPE: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
    INFORMATIVE: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
    RESOLVED: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
    CLOSED: 'bg-slate-700/30 text-slate-500 border-slate-700/40',
  })[status] || 'bg-slate-700/30 text-slate-500 border-slate-700/40';
}
