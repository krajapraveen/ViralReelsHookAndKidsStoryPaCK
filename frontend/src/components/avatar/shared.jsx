import React from 'react';
import { AlertTriangle, Sparkles } from 'lucide-react';

export const API = process.env.REACT_APP_BACKEND_URL;
export const VISIBLE_LABEL = 'AI-generated avatar';
export const DEMO_LABEL = 'Demo / simulated output';

export const authHeaders = (extra = {}) => {
  const t = localStorage.getItem('token');
  return { Authorization: `Bearer ${t}`, ...extra };
};

export function DisclosureBanner({ inline = false, testidSuffix = '' }) {
  return (
    <div
      className={`flex items-start gap-2.5 p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-100 ${inline ? '' : 'mb-4'}`}
      data-testid={`avatar-studio-disclosure-banner${testidSuffix ? '-' + testidSuffix : ''}`}
    >
      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-300" />
      <div className="text-xs leading-relaxed">
        <span className="font-bold text-amber-200">{VISIBLE_LABEL}.</span> Every clip from this studio carries a visible label and a forensic watermark. Outputs shown this session are <span className="font-bold text-amber-200">{DEMO_LABEL.toLowerCase()}</span> for demand-testing — real AI generation ships in Phase 2.
      </div>
    </div>
  );
}

export function DemoBadge({ className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-200 text-[10px] uppercase tracking-wider font-bold border border-amber-500/40 ${className}`}
      data-testid="avatar-studio-demo-badge"
    >
      <Sparkles className="w-2.5 h-2.5" /> {DEMO_LABEL}
    </span>
  );
}

export function StepperHeader({ currentStep, steps }) {
  return (
    <div className="flex items-center gap-1.5 mb-6 overflow-x-auto no-scrollbar" data-testid="avatar-studio-stepper">
      {steps.map((s, idx) => {
        const active = idx === currentStep;
        const done = idx < currentStep;
        return (
          <div key={s.id} className="flex items-center gap-1.5 shrink-0" data-testid={`avatar-studio-stepper-step-${s.id}`}>
            <div
              className={`flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold transition-colors ${
                done ? 'bg-emerald-500 text-white' : active ? 'bg-violet-500 text-white' : 'bg-white/10 text-slate-400'
              }`}
            >
              {done ? '✓' : idx + 1}
            </div>
            <span className={`text-xs ${active ? 'text-white font-semibold' : done ? 'text-emerald-300' : 'text-slate-500'}`}>
              {s.label}
            </span>
            {idx < steps.length - 1 && <span className="text-slate-600 text-xs mx-0.5">›</span>}
          </div>
        );
      })}
    </div>
  );
}

export function SectionTitle({ eyebrow, title, sub }) {
  return (
    <div>
      {eyebrow && (
        <div className="text-[10px] uppercase tracking-[0.18em] text-violet-300 font-bold mb-2">{eyebrow}</div>
      )}
      <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight">{title}</h1>
      {sub && <p className="text-sm text-slate-400 mt-2 max-w-2xl">{sub}</p>}
    </div>
  );
}
