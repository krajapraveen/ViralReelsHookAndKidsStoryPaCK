import React, { useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Upload, X, Loader2, ShieldCheck, ArrowLeft, ArrowRight, Check, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORIES = [
  ['AUTHENTICATION', 'Authentication'],
  ['AUTHORIZATION', 'Authorization'],
  ['IDOR', 'IDOR'],
  ['XSS', 'XSS'],
  ['CSRF', 'CSRF'],
  ['SSRF', 'SSRF'],
  ['RCE', 'RCE'],
  ['INJECTION', 'Injection'],
  ['FILE_UPLOAD', 'File Upload'],
  ['SESSION_MANAGEMENT', 'Session Management'],
  ['PAYMENT_BILLING', 'Billing / Credits'],
  ['INFO_DISCLOSURE', 'Information Disclosure'],
  ['RATE_LIMIT_BYPASS', 'Rate Limit Bypass'],
  ['OTHER', 'Other'],
];

const SEVERITIES = [
  ['LOW', 'Low'],
  ['MEDIUM', 'Medium'],
  ['HIGH', 'High'],
  ['CRITICAL', 'Critical'],
];

const ALLOWED_EXT = ['png', 'jpg', 'jpeg', 'pdf', 'txt'];
const MAX_FILES = 3;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function SecurityReportPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({
    full_name: '',
    from_email: '',
    subject: '',
    category: '',
    severity: '',
    body: '',
    consent_accepted: false,
    honeypot: '',
  });
  const [attachments, setAttachments] = useState([]); // {file_key, filename, size}
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const now = new Date();
  const formattedDate = now.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: '2-digit' });
  const formattedTime = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (!form.full_name || form.full_name.trim().length < 2) e.full_name = 'Required (min 2 chars)';
    if (!form.from_email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.from_email)) e.from_email = 'Valid email required';
    if (!form.subject || form.subject.trim().length < 10) e.subject = 'Subject must be at least 10 characters';
    if (!form.category) e.category = 'Select a category';
    if (!form.severity) e.severity = 'Select a severity';
    if (!form.body || form.body.trim().length < 50) e.body = 'Description must be at least 50 characters';
    if (!form.consent_accepted) e.consent_accepted = 'You must accept the disclosure policy';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleFileSelect = async (files) => {
    const arr = Array.from(files);
    const remaining = MAX_FILES - attachments.length;
    if (remaining <= 0) return;
    const toUpload = arr.slice(0, remaining);
    setUploading(true);
    try {
      for (const file of toUpload) {
        const ext = (file.name.split('.').pop() || '').toLowerCase();
        if (!ALLOWED_EXT.includes(ext)) {
          setErrors(p => ({ ...p, attachments: `File type .${ext} not allowed` }));
          continue;
        }
        if (file.size > MAX_FILE_BYTES) {
          setErrors(p => ({ ...p, attachments: `${file.name} exceeds 10 MB` }));
          continue;
        }
        const fd = new FormData();
        fd.append('file', file);
        const { data } = await axios.post(`${API}/api/security/attachment/upload`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        if (data.success) {
          setAttachments(a => [...a, { file_key: data.file_key, filename: data.filename, size: data.size }]);
          setErrors(p => ({ ...p, attachments: undefined }));
        }
      }
    } catch (err) {
      setErrors(p => ({ ...p, attachments: err?.response?.data?.detail || 'Upload failed' }));
    } finally {
      setUploading(false);
    }
  };

  const removeAttachment = (key) => {
    setAttachments(a => a.filter(x => x.file_key !== key));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload = {
        full_name: form.full_name.trim(),
        from_email: form.from_email.trim().toLowerCase(),
        subject: form.subject.trim(),
        category: form.category,
        severity: form.severity,
        body: form.body.trim(),
        consent_accepted: form.consent_accepted,
        honeypot: form.honeypot,
        attachment_keys: attachments.map(a => a.file_key),
      };
      const { data } = await axios.post(`${API}/api/security/report`, payload);
      if (data.success) {
        navigate(`/security/report/submitted?id=${encodeURIComponent(data.report_id)}`);
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Submission failed. Please try again.';
      setErrors(p => ({ ...p, _global: msg }));
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setForm({
      full_name: '', from_email: '', subject: '', category: '', severity: '',
      body: '', consent_accepted: false, honeypot: '',
    });
    setAttachments([]);
    setErrors({});
  };

  return (
    <div className="min-h-screen bg-[#0B0F1A] text-white" data-testid="security-report-page">
      <header className="border-b border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link to="/security" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors" data-testid="back-to-security">
            <ArrowLeft className="w-4 h-4" /> Back to Security
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-semibold tracking-tight">Visionary Suite</span>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-14">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/30 text-[11px] tracking-[0.12em] text-violet-300 font-medium mb-6">
          RESPONSIBLE DISCLOSURE
        </div>
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">Report a Vulnerability</h1>
        <p className="text-lg text-slate-400 leading-relaxed mb-12 max-w-2xl">
          Thank you for helping improve Visionary Suite security. Please provide as much detail as possible so our team can reproduce and resolve the issue quickly.
        </p>

        <form onSubmit={handleSubmit} className="space-y-10" noValidate>
          {/* Reporter Details */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-6 h-6 rounded-full border border-violet-500/40 bg-violet-500/10 flex items-center justify-center text-[11px] font-bold text-violet-300">1</div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-400">Reporter Details</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <Field label="Full Name or Alias" error={errors.full_name}>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={e => update('full_name', e.target.value)}
                  placeholder="Researcher alias"
                  className="input"
                  data-testid="input-full-name"
                  autoComplete="name"
                />
              </Field>
              <Field label="From Email" error={errors.from_email}>
                <input
                  type="email"
                  value={form.from_email}
                  onChange={e => update('from_email', e.target.value)}
                  placeholder="researcher@example.com"
                  className="input"
                  data-testid="input-from-email"
                  autoComplete="email"
                />
              </Field>
              <Field label="To Email" helper="Reports are routed to our security inboxes.">
                <input
                  type="text"
                  value="krajapraveen@visionary-suite.com, admin@visionary-suite.com"
                  readOnly
                  className="input opacity-60 cursor-not-allowed"
                  data-testid="input-to-email"
                />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Date">
                  <input type="text" value={formattedDate} readOnly className="input opacity-60 cursor-not-allowed" data-testid="input-date" />
                </Field>
                <Field label="Time">
                  <input type="text" value={formattedTime} readOnly className="input opacity-60 cursor-not-allowed" data-testid="input-time" />
                </Field>
              </div>
            </div>
          </section>

          {/* Report Details */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-6 h-6 rounded-full border border-violet-500/40 bg-violet-500/10 flex items-center justify-center text-[11px] font-bold text-violet-300">2</div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-400">Report Details</h2>
            </div>
            <div className="space-y-4">
              <Field label="Subject" error={errors.subject}>
                <input
                  type="text"
                  value={form.subject}
                  onChange={e => update('subject', e.target.value)}
                  placeholder="Example: IDOR vulnerability in shared video endpoint"
                  className="input"
                  data-testid="input-subject"
                />
              </Field>
              <div className="grid md:grid-cols-2 gap-4">
                <Field label="Vulnerability Category" error={errors.category}>
                  <select
                    value={form.category}
                    onChange={e => update('category', e.target.value)}
                    className="input"
                    data-testid="select-category"
                  >
                    <option value="">Select category</option>
                    {CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Field>
                <Field label="Estimated Severity" error={errors.severity}>
                  <select
                    value={form.severity}
                    onChange={e => update('severity', e.target.value)}
                    className="input"
                    data-testid="select-severity"
                  >
                    <option value="">Select severity</option>
                    {SEVERITIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Field>
              </div>
              <Field label="What is the issue? How can we reproduce it? What's the impact?" error={errors.body}>
                <textarea
                  value={form.body}
                  onChange={e => update('body', e.target.value)}
                  rows={12}
                  placeholder={'Describe the vulnerability clearly.\n\nInclude:\n- What is vulnerable (affected URL / endpoint)\n- Steps to reproduce\n- Proof of concept\n- Expected behavior\n- Actual behavior\n- Impact on users or systems'}
                  className="input font-mono text-[13px] leading-relaxed"
                  data-testid="textarea-body"
                />
                <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                  <span>Minimum 50 characters</span>
                  <span>{form.body.length}</span>
                </div>
              </Field>
            </div>
          </section>

          {/* Attachments */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-6 h-6 rounded-full border border-violet-500/40 bg-violet-500/10 flex items-center justify-center text-[11px] font-bold text-violet-300">3</div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-400">Evidence (optional)</h2>
            </div>
            <div
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); handleFileSelect(e.dataTransfer.files); }}
              className="rounded-xl border border-dashed border-white/[0.12] bg-white/[0.02] p-8 text-center hover:border-violet-500/40 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
              data-testid="dropzone"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".png,.jpg,.jpeg,.pdf,.txt"
                className="hidden"
                onChange={e => handleFileSelect(e.target.files)}
                data-testid="file-input"
              />
              {uploading ? (
                <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin" /> Uploading…
                </div>
              ) : (
                <>
                  <Upload className="w-6 h-6 text-slate-500 mx-auto mb-3" />
                  <p className="text-sm text-slate-300">
                    <span className="font-medium">Drop files here</span> or click to browse
                  </p>
                  <p className="text-xs text-slate-500 mt-1">PNG, JPG, PDF, TXT · max 10 MB each · up to 3 files</p>
                </>
              )}
            </div>
            {errors.attachments && <p className="text-xs text-rose-400 mt-2 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> {errors.attachments}</p>}
            {attachments.length > 0 && (
              <div className="mt-4 space-y-2" data-testid="attachment-list">
                {attachments.map(a => (
                  <div key={a.file_key} className="flex items-center justify-between bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2.5" data-testid={`attachment-${a.file_key}`}>
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-md bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0">
                        <Check className="w-4 h-4 text-emerald-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm text-white truncate">{a.filename}</p>
                        <p className="text-[10px] text-slate-500">{(a.size / 1024).toFixed(1)} KB</p>
                      </div>
                    </div>
                    <button type="button" onClick={() => removeAttachment(a.file_key)} className="text-slate-500 hover:text-rose-400 p-1" data-testid={`remove-${a.file_key}`}>
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Honeypot */}
          <div className="absolute -left-[9999px]" aria-hidden="true">
            <label>Website</label>
            <input type="text" tabIndex={-1} autoComplete="off" value={form.honeypot} onChange={e => update('honeypot', e.target.value)} />
          </div>

          {/* Consent */}
          <section>
            <label className="flex items-start gap-3 cursor-pointer group" data-testid="consent-label">
              <input
                type="checkbox"
                checked={form.consent_accepted}
                onChange={e => update('consent_accepted', e.target.checked)}
                className="mt-1 w-4 h-4 accent-violet-500"
                data-testid="checkbox-consent"
              />
              <span className="text-sm text-slate-300 leading-relaxed">
                I confirm this report is submitted in good faith and follows Visionary Suite's{' '}
                <Link to="/security" className="text-violet-300 hover:text-violet-200 underline">responsible disclosure policy</Link>.
                I have not accessed data beyond what was necessary to validate the issue.
              </span>
            </label>
            {errors.consent_accepted && <p className="text-xs text-rose-400 mt-2 ml-7 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> {errors.consent_accepted}</p>}
          </section>

          {errors._global && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/[0.05] p-4 flex items-start gap-3" data-testid="global-error">
              <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
              <p className="text-sm text-rose-300">{errors._global}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              data-testid="submit-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              {submitting ? 'Submitting…' : 'Submit Security Report'}
              {!submitting && <ArrowRight className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={resetForm}
              disabled={submitting}
              className="px-5 py-3 rounded-xl border border-white/10 text-slate-300 hover:bg-white/5 disabled:opacity-40 transition-colors text-sm"
              data-testid="reset-btn"
            >
              Reset Form
            </button>
          </div>
        </form>

        <p className="text-xs text-slate-500 mt-12 leading-relaxed">
          We review every legitimate report carefully. Duplicate, abusive, or out-of-scope submissions may not receive a response. Reports are private and handled under our <Link to="/security" className="text-violet-300 underline">responsible disclosure policy</Link>.
        </p>
      </main>

      <style>{`
        .input {
          width: 100%;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 10px;
          padding: 11px 14px;
          color: #fff;
          font-size: 14px;
          outline: none;
          transition: all 0.15s;
        }
        .input:focus { border-color: rgba(139,92,246,0.5); background: rgba(255,255,255,0.05); }
        .input::placeholder { color: rgba(255,255,255,0.3); }
        select.input { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 32px; }
        select.input option { background: #0B0F1A; color: #fff; }
      `}</style>
    </div>
  );
}

function Field({ label, helper, error, children }) {
  return (
    <label className="block">
      <span className="block text-xs text-slate-400 mb-1.5 font-medium">{label}</span>
      {children}
      {helper && !error && <p className="text-[10px] text-slate-600 mt-1">{helper}</p>}
      {error && <p className="text-[11px] text-rose-400 mt-1 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> {error}</p>}
    </label>
  );
}
