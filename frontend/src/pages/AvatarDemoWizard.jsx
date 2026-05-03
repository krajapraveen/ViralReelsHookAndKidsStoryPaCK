import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Lock, Sparkles } from 'lucide-react';

import AvatarTypeStep from '../components/avatar/AvatarTypeStep';
import AssetUploadStep from '../components/avatar/AssetUploadStep';
import MotionStep from '../components/avatar/MotionStep';
import SafetyReviewStep from '../components/avatar/SafetyReviewStep';
import GenerationProgress from '../components/avatar/GenerationProgress';
import { StepperHeader, API, DemoBadge } from '../components/avatar/shared';

/**
 * Public anonymous AI Cloning Studio demo.
 *
 * Entry point: /avatar-demo   (no auth required)
 *
 * Flow:
 *   Type → Upload → Motion → Safety → Progress → Result (gated)
 *
 * - No library step. Lands straight in Step 1.
 * - Pre-fills a sample photo + script so users CAN generate with zero
 *   friction. They can still replace both.
 * - Generation uses `POST /api/avatar/studio/anon-mock-generate` with a
 *   per-session id stored in localStorage (abuse guard: 2 generations
 *   per 24h per session).
 * - Signup gate applied ONLY at Result screen: Download, Save, Create
 *   real avatar → `/signup?from=avatar_demo`.
 */

const WIZARD_STEPS = [
  { id: 'type',     label: 'Type' },
  { id: 'upload',   label: 'Upload' },
  { id: 'motion',   label: 'Motion' },
  { id: 'safety',   label: 'Safety' },
  { id: 'progress', label: 'Generate' },
];

const SAMPLE_PHOTO_DATA_URL =
  'data:image/svg+xml;base64,' + btoa(`<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#6d28d9" />
        <stop offset="100%" stop-color="#db2777" />
      </linearGradient>
    </defs>
    <rect width="320" height="320" fill="url(#g)"/>
    <circle cx="160" cy="125" r="55" fill="#f5e6ff" opacity="0.9"/>
    <ellipse cx="160" cy="260" rx="95" ry="55" fill="#f5e6ff" opacity="0.9"/>
    <text x="160" y="315" font-family="system-ui" font-size="14" fill="#fff" text-anchor="middle" opacity="0.85">sample face</text>
  </svg>`);

const SAMPLE_SCRIPT =
  "Hey — I didn't record this video. This is my AI avatar. " +
  "Want your own? Make one in under a minute.";

const DEFAULT_FORM = {
  avatarType: 'quick_avatar',
  cloneName: 'My Demo Avatar',
  photo: { name: 'sample_face.svg', size: 1024, dataUrl: SAMPLE_PHOTO_DATA_URL, is_sample: true },
  voiceSample: null,
  motionStyle: 'talking_head',
  duration: 15,
  script: SAMPLE_SCRIPT,
  acceptedRules: [],
};

function getAnonSessionId() {
  let sid = localStorage.getItem('avatar_demo_session_id');
  if (!sid) {
    sid = 'anon_' + Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
    localStorage.setItem('avatar_demo_session_id', sid);
  }
  return sid;
}

function emitFunnel(step, meta) {
  try {
    fetch(`${API}/api/avatar/funnel/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step, session_id: getAnonSessionId(), meta: meta || {} }),
    }).catch(() => {});
  } catch {}
}

export default function AvatarDemoWizard() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [step, setStep] = useState('type');
  const [form, setForm] = useState(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [job, setJob] = useState(null);

  const anonSessionId = useMemo(() => getAnonSessionId(), []);

  // Capture UTM / ref into localStorage so the future /signup flow can
  // attribute it. Preserves prior avatar_attribution contract.
  useEffect(() => {
    const utm = {
      utm_source: params.get('utm_source') || null,
      utm_campaign: params.get('utm_campaign') || null,
      referrer_user_id: params.get('ref') || null,
      landing_path: '/avatar-demo',
      landed_at: new Date().toISOString(),
    };
    if ((utm.utm_source || utm.utm_campaign || utm.referrer_user_id)
        && !localStorage.getItem('avatar_attribution')) {
      try { localStorage.setItem('avatar_attribution', JSON.stringify(utm)); } catch {}
    }
    emitFunnel('avatar_landing_view', { path: '/avatar-demo', ...utm });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = (patch) => setForm(f => ({ ...f, ...patch }));

  const resetForm = useCallback(() => {
    setForm({ ...DEFAULT_FORM });
    setJob(null);
    setSubmitError(null);
    setStep('type');
  }, []);

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = {
        session_id: anonSessionId,
        avatar_type: form.avatarType,
        motion_style: form.motionStyle,
        duration_seconds: form.duration,
        script: form.script?.trim() || null,
        clone_name: form.cloneName?.trim() || null,
        safety_confirmed: form.acceptedRules.length === 5,
        assets: {
          photo_name: form.photo?.name || null,
          photo_is_sample: form.photo?.is_sample === true,
          voice_sample_name: form.voiceSample?.name || null,
        },
      };
      const r = await fetch(`${API}/api/avatar/studio/anon-mock-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        const code = body?.detail?.code || 'ANON_GENERATE_FAIL';
        const message = body?.detail?.message || 'Could not start generation. Please retry.';
        if (code === 'ANON_LIMIT_REACHED') {
          // redirect to signup when the session is out of free runs
          nav('/signup?from=avatar_demo&reason=limit_reached');
          return;
        }
        throw new Error(message);
      }
      setJob({ id: body.job_id, eta: body.eta_seconds });
      setStep('progress');
      emitFunnel('demo_generate_clicked', {
        job_id: body.job_id,
        avatar_type: form.avatarType,
        motion_style: form.motionStyle,
        duration_seconds: form.duration,
      });
    } catch (e) {
      setSubmitError(String(e.message || e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignupGate = (reason) => {
    emitFunnel('signup_after_demo', {
      reason,
      job_id: job?.id,
      avatar_type: form.avatarType,
    });
    nav(`/signup?from=avatar_demo&reason=${encodeURIComponent(reason || 'cta')}`);
  };

  const handleMakeAnother = () => {
    // fire retry event first so we measure intent even if the user bails
    emitFunnel('retry_after_demo', { prior_job_id: job?.id });
    resetForm();
  };

  const currentStepIdx = WIZARD_STEPS.findIndex(s => s.id === step);

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-white" data-testid="avatar-demo-wizard-page">
      <Header onExit={() => nav('/')} />
      <main className="max-w-4xl mx-auto px-4 py-6 sm:py-10">
        <DemoWelcomeBanner />
        <StepperHeader currentStep={Math.max(0, currentStepIdx)} steps={WIZARD_STEPS} />

        {step === 'type' && (
          <AvatarTypeStep
            value={form.avatarType}
            onChange={(v) => update({ avatarType: v })}
            onBack={() => nav('/')}
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
          <>
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
            {submitError && (
              <div className="mt-3 p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 text-xs"
                   data-testid="avatar-studio-safety-submit-error">
                {submitError}
              </div>
            )}
          </>
        )}

        {step === 'progress' && job?.id && (
          <GenerationProgress
            jobId={job.id}
            etaSeconds={job.eta}
            anonymous
            anonSessionId={anonSessionId}
            onMakeAnother={handleMakeAnother}
            onBackToLibrary={null}
            onSignupGate={handleSignupGate}
          />
        )}
      </main>
    </div>
  );
}

function Header({ onExit }) {
  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          onClick={onExit}
          className="text-slate-300 hover:text-white flex items-center gap-1.5 text-sm"
          data-testid="avatar-demo-header-back-btn"
        >
          <ArrowLeft className="w-4 h-4" /> Exit demo
        </button>
        <div className="ml-auto flex items-center gap-2">
          <DemoBadge />
          <span className="text-xs text-slate-400 hidden sm:inline">·</span>
          <span className="text-xs text-slate-400 hidden sm:flex items-center gap-1">
            <Lock className="w-3.5 h-3.5 text-emerald-400" /> No signup to try
          </span>
        </div>
      </div>
    </header>
  );
}

function DemoWelcomeBanner() {
  return (
    <div
      className="mb-6 p-4 rounded-2xl border border-violet-500/30 bg-gradient-to-br from-violet-500/10 via-fuchsia-500/5 to-transparent flex items-start gap-3"
      data-testid="avatar-demo-welcome-banner"
    >
      <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center shrink-0">
        <Sparkles className="w-5 h-5 text-violet-200" />
      </div>
      <div>
        <div className="text-sm font-bold text-white">Try the AI Cloning Studio — no signup</div>
        <div className="text-xs text-slate-400 mt-0.5">
          We pre-filled a sample photo and script so you can hit Generate in 30 seconds. Replace either if you want. You'll be asked to sign up only if you want to download or save.
        </div>
      </div>
    </div>
  );
}
