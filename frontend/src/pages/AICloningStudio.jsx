import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Lock } from 'lucide-react';

import LibraryStep from '../components/avatar/LibraryStep';
import AvatarTypeStep from '../components/avatar/AvatarTypeStep';
import AssetUploadStep from '../components/avatar/AssetUploadStep';
import MotionStep from '../components/avatar/MotionStep';
import SafetyReviewStep from '../components/avatar/SafetyReviewStep';
import GenerationProgress from '../components/avatar/GenerationProgress';
import { StepperHeader, API, authHeaders } from '../components/avatar/shared';

/**
 * AI Cloning Studio — 5-step mocked wizard.
 *
 * Flow:
 *   step=library   → pick saved avatar or + Create new
 *   step=type      → Quick / Voice-Matched / Motion / Template
 *   step=upload    → Photo (+ voice sample if voice_matched), name
 *   step=motion    → Talking-head / Gesture / Full-body / Static + duration
 *   step=safety    → script + 5-rule checklist
 *   step=progress  → polls mock job → auto-completes in 20–60s with demo output
 *
 * Backend contract (fully mocked):
 *   POST /api/avatar/studio/mock-generate → { job_id, eta_seconds }
 *   GET  /api/avatar/jobs/:id             → progress + completed url
 */

const WIZARD_STEPS = [
  { id: 'type',     label: 'Type' },
  { id: 'upload',   label: 'Upload' },
  { id: 'motion',   label: 'Motion' },
  { id: 'safety',   label: 'Safety' },
  { id: 'progress', label: 'Generate' },
];

const DEFAULT_FORM = {
  avatarType: null,
  cloneName: '',
  photo: null,
  voiceSample: null,
  motionStyle: 'talking_head',
  duration: 15,
  script: '',
  acceptedRules: [],
};

export default function AICloningStudio() {
  const nav = useNavigate();
  const [step, setStep] = useState('library');
  const [clones, setClones] = useState([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [job, setJob] = useState(null);

  const fetchClones = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/avatar/clones`, { headers: authHeaders() });
      if (r.status === 401) { nav('/login'); return; }
      if (!r.ok) return;
      const d = await r.json();
      setClones(d.clones || []);
    } catch {}
  }, [nav]);

  useEffect(() => { fetchClones(); }, [fetchClones]);

  // Lazy referral attribution (preserves prior funnel wiring)
  useEffect(() => {
    if (localStorage.getItem('avatar_attribution_attached') === '1') return;
    let attribution = null;
    try { attribution = JSON.parse(localStorage.getItem('avatar_attribution') || 'null'); } catch {}
    if (!attribution) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/api/avatar/referral/attribute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(attribution),
    }).then(r => r.ok && localStorage.setItem('avatar_attribution_attached', '1')).catch(() => {});
  }, []);

  const update = (patch) => setForm(f => ({ ...f, ...patch }));

  const resetAndStartNew = () => {
    setForm(DEFAULT_FORM);
    setJob(null);
    setSubmitError(null);
    setStep('type');
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = {
        avatar_type: form.avatarType,
        motion_style: form.motionStyle,
        duration_seconds: form.duration,
        script: form.script?.trim() || null,
        clone_name: form.cloneName?.trim() || null,
        safety_confirmed: form.acceptedRules.length === 5,
        assets: {
          photo_name: form.photo?.name || null,
          voice_sample_name: form.voiceSample?.name || null,
        },
      };
      const r = await fetch(`${API}/api/avatar/studio/mock-generate`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(body?.detail?.message || body?.detail || 'Could not start generation. Please retry.');
      }
      setJob({ id: body.job_id, eta: body.eta_seconds });
      setStep('progress');
      // funnel emit — consent_submitted analogue for the mocked flow
      fetch(`${API}/api/avatar/funnel/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: 'avatar_consent_submitted', meta: { is_mocked: true, avatar_type: form.avatarType } }),
      }).catch(() => {});
    } catch (e) {
      setSubmitError(String(e.message || e));
    } finally {
      setSubmitting(false);
    }
  };

  const currentStepIdx = WIZARD_STEPS.findIndex(s => s.id === step);
  const showStepper = step !== 'library';

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-white" data-testid="avatar-studio-page">
      <Header onBack={() => step === 'library' ? nav('/app') : setStep('library')} />
      <main className="max-w-4xl mx-auto px-4 py-6 sm:py-10">
        {showStepper && (
          <StepperHeader currentStep={Math.max(0, currentStepIdx)} steps={WIZARD_STEPS} />
        )}

        {step === 'library' && (
          <LibraryStep
            clones={clones}
            onCreateNew={resetAndStartNew}
            onPickAvatar={(c) => {
              // Re-using a saved avatar still walks the wizard so we capture
              // fresh motion/script/safety — but we prefill the clone name
              // and jump straight to Type so they feel velocity.
              setForm({ ...DEFAULT_FORM, cloneName: c.clone_name || '' });
              setJob(null);
              setSubmitError(null);
              setStep('type');
            }}
          />
        )}

        {step === 'type' && (
          <AvatarTypeStep
            value={form.avatarType}
            onChange={(v) => update({ avatarType: v })}
            onBack={() => setStep('library')}
            onNext={() => setStep('upload')}
          />
        )}

        {step === 'upload' && (
          <AssetUploadStep
            avatarType={form.avatarType}
            cloneName={form.cloneName}
            onCloneNameChange={(v) => update({ cloneName: v })}
            photo={form.photo}
            onPhotoChange={(v) => update({ photo: v })}
            voiceSample={form.voiceSample}
            onVoiceSampleChange={(v) => update({ voiceSample: v })}
            onBack={() => setStep('type')}
            onNext={() => setStep('motion')}
          />
        )}

        {step === 'motion' && (
          <MotionStep
            motionStyle={form.motionStyle}
            onMotionChange={(v) => update({ motionStyle: v })}
            duration={form.duration}
            onDurationChange={(v) => update({ duration: v })}
            onBack={() => setStep('upload')}
            onNext={() => setStep('safety')}
          />
        )}

        {step === 'safety' && (
          <SafetyReviewStep
            script={form.script}
            onScriptChange={(v) => update({ script: v })}
            acceptedRules={form.acceptedRules}
            onToggleRule={(id) => setForm(f => ({
              ...f,
              acceptedRules: f.acceptedRules.includes(id)
                ? f.acceptedRules.filter(x => x !== id)
                : [...f.acceptedRules, id],
            }))}
            onBack={() => setStep('motion')}
            onGenerate={handleSubmit}
            submitting={submitting}
          />
        )}

        {step === 'safety' && submitError && (
          <div className="mt-3 p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 text-xs"
               data-testid="avatar-studio-safety-submit-error">
            {submitError}
          </div>
        )}

        {step === 'progress' && job?.id && (
          <GenerationProgress
            jobId={job.id}
            etaSeconds={job.eta}
            onMakeAnother={() => { resetAndStartNew(); }}
            onBackToLibrary={() => { fetchClones(); setStep('library'); }}
          />
        )}
      </main>
    </div>
  );
}

function Header({ onBack }) {
  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-slate-300 hover:text-white flex items-center gap-1.5 text-sm"
          data-testid="avatar-studio-header-back-btn"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
          <Lock className="w-3.5 h-3.5 text-emerald-400" /> Consent + disclosure enforced
        </div>
      </div>
    </header>
  );
}
