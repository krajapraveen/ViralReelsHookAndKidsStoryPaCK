import React from 'react';
import { ArrowLeft, ShieldCheck, Shield, Lock } from 'lucide-react';
import { SectionTitle } from './shared';

const CHECKLIST = [
  { id: 'not_public_figure', text: 'This is not a celebrity, politician, or any public figure.' },
  { id: 'have_consent',      text: 'I am the person in the photo — OR — I have written consent from them.' },
  { id: 'no_fraud',          text: 'I will not use this avatar for OTP, banking, KYC, or deception.' },
  { id: 'no_impersonation',  text: 'I will not impersonate a doctor, lawyer, or advisor.' },
  { id: 'disclose_ai',       text: 'I agree every output is labeled AI-generated and watermarked.' },
];

export default function SafetyReviewStep({
  script,
  onScriptChange,
  acceptedRules,
  onToggleRule,
  onBack,
  onGenerate,
  submitting,
}) {
  const allAccepted = CHECKLIST.every(r => acceptedRules.includes(r.id));
  const scriptTrimmed = (script || '').trim();
  const scriptOk = scriptTrimmed.length === 0 || scriptTrimmed.length >= 8;
  const canGenerate = allAccepted && !submitting && scriptOk;

  return (
    <div className="space-y-6" data-testid="avatar-studio-safety-step">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white"
                data-testid="avatar-studio-safety-back-btn">
          <ArrowLeft className="w-4 h-4" /> Back to motion
        </button>
      </div>
      <SectionTitle
        eyebrow="Step 4 of 5"
        title="One last safety check"
        sub="AI avatars of real people deserve guardrails. Confirm you're within our usage policy. We auto-block celebrity names, political content, fraud phrases, and impersonation attempts."
      />

      <label className="block" data-testid="avatar-studio-safety-script-field">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-300">Script <span className="text-slate-500">(optional — we'll auto-fill if blank)</span></span>
          <span className="text-[11px] text-slate-500">{scriptTrimmed.length} / 1200</span>
        </div>
        <textarea
          value={script || ''}
          onChange={e => onScriptChange(e.target.value.slice(0, 1200))}
          rows={5}
          placeholder="Hello, welcome to my channel. Today I'll share three productivity tips…"
          className="mt-1 w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-500"
          data-testid="avatar-studio-safety-script-input"
        />
      </label>

      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid="avatar-studio-safety-checklist">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-300 mb-3">
          <ShieldCheck className="w-4 h-4" /> Usage policy — tick all
        </div>
        <ul className="space-y-2.5">
          {CHECKLIST.map(rule => {
            const checked = acceptedRules.includes(rule.id);
            return (
              <li key={rule.id}>
                <label
                  className={`flex items-start gap-3 p-2.5 rounded-lg cursor-pointer hover:bg-white/[0.03] transition-colors ${checked ? 'bg-emerald-500/5' : ''}`}
                  data-testid={`avatar-studio-safety-rule-${rule.id}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onToggleRule(rule.id)}
                    className="mt-0.5 w-[22px] h-[22px] rounded-[5px] border-2 border-white/30 accent-emerald-500 cursor-pointer shrink-0"
                    data-testid={`avatar-studio-safety-rule-${rule.id}-checkbox`}
                  />
                  <span className={`text-sm ${checked ? 'text-white' : 'text-slate-300'}`}>{rule.text}</span>
                </label>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex items-start gap-2.5 p-3 rounded-xl border border-cyan-500/25 bg-cyan-500/5 text-cyan-100">
        <Shield className="w-4 h-4 mt-0.5 shrink-0 text-cyan-300" />
        <div className="text-[11px] leading-relaxed">
          <span className="font-bold text-cyan-200">What happens if you break these rules?</span> The avatar is auto-disabled, consent revoked, and the export pulled from any share link. This is why we watermark every frame.
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-slate-500 flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-emerald-400" /> Outputs are disclosure-labeled
        </div>
        <button
          onClick={onGenerate}
          disabled={!canGenerate}
          className="px-6 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          data-testid="avatar-studio-safety-generate-btn"
        >
          {submitting ? 'Starting…' : 'Generate avatar video'}
        </button>
      </div>
    </div>
  );
}
