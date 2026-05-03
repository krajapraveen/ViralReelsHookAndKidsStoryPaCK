import React, { useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Image as ImageIcon, Mic, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { SectionTitle, DisclosureBanner } from './shared';

const MAX_PHOTO_BYTES = 8 * 1024 * 1024;    // 8 MB sanity
const MAX_VOICE_BYTES = 12 * 1024 * 1024;   // 12 MB sanity

/**
 * Step 2 — Asset upload.
 * Fully mocked: we read the file locally with FileReader for preview +
 * capture the filename. No upload to backend. Names travel in `assets`
 * payload when the mock job is submitted.
 */
export default function AssetUploadStep({
  avatarType,
  cloneName,
  onCloneNameChange,
  photo,
  onPhotoChange,
  voiceSample,
  onVoiceSampleChange,
  onBack,
  onNext,
}) {
  const [err, setErr] = useState(null);
  const photoInputRef = useRef(null);
  const voiceInputRef = useRef(null);

  const needsVoice = avatarType === 'voice_matched';

  const pickPhoto = (file) => {
    setErr(null);
    if (!file) return;
    if (file.size > MAX_PHOTO_BYTES) { setErr('Photo too large (max 8 MB).'); return; }
    if (!file.type.startsWith('image/')) { setErr('Please pick an image file (JPG/PNG).'); return; }
    const reader = new FileReader();
    reader.onload = () => onPhotoChange({ name: file.name, size: file.size, dataUrl: reader.result });
    reader.readAsDataURL(file);
  };
  const pickVoice = (file) => {
    setErr(null);
    if (!file) return;
    if (file.size > MAX_VOICE_BYTES) { setErr('Voice sample too large (max 12 MB).'); return; }
    if (!file.type.startsWith('audio/')) { setErr('Please pick an audio file (MP3/WAV/M4A).'); return; }
    onVoiceSampleChange({ name: file.name, size: file.size });
  };

  const readyToContinue = !!photo && (!needsVoice || !!voiceSample) && (cloneName || '').trim().length >= 2;

  return (
    <div className="space-y-6" data-testid="avatar-studio-upload-step">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white"
                data-testid="avatar-studio-upload-back-btn">
          <ArrowLeft className="w-4 h-4" /> Change type
        </button>
      </div>
      <SectionTitle
        eyebrow="Step 2 of 5"
        title="Upload your assets"
        sub="One photo of your face, plus a short voice sample if you chose Voice-Matched. We encrypt and auto-delete within 24h for demo runs."
      />
      <DisclosureBanner inline />

      <label className="block" data-testid="avatar-studio-upload-name-field">
        <span className="text-sm text-slate-300">Name your avatar</span>
        <input
          type="text"
          value={cloneName}
          onChange={e => onCloneNameChange(e.target.value)}
          placeholder="e.g. My Coaching Avatar"
          maxLength={60}
          className="mt-1 w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-500"
          data-testid="avatar-studio-upload-name-input"
        />
      </label>

      {/* Photo upload */}
      <div
        className={`rounded-2xl border-2 border-dashed p-5 transition-colors ${photo ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-white/15 bg-white/[0.02]'}`}
        data-testid="avatar-studio-upload-photo-drop"
      >
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center shrink-0">
            <ImageIcon className="w-5 h-5 text-violet-200" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-white">Face photo</div>
            <div className="text-xs text-slate-400 mt-0.5">Clear front-facing shot. JPG or PNG, up to 8 MB.</div>
            {photo ? (
              <div className="mt-3 flex items-center gap-3">
                <img src={photo.dataUrl} alt="preview" className="w-16 h-16 rounded-lg object-cover border border-white/10"
                     data-testid="avatar-studio-upload-photo-preview" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-emerald-300 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> {photo.name}</div>
                  <div className="text-[11px] text-slate-500">{(photo.size / 1024).toFixed(0)} KB</div>
                </div>
                <button
                  onClick={() => onPhotoChange(null)}
                  className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:text-white"
                  data-testid="avatar-studio-upload-photo-remove-btn"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => photoInputRef.current?.click()}
                className="mt-3 px-4 py-2 rounded-lg bg-violet-500/20 border border-violet-500/40 text-violet-100 text-xs font-bold hover:bg-violet-500/30"
                data-testid="avatar-studio-upload-photo-pick-btn"
              >
                Choose photo
              </button>
            )}
            <input
              ref={photoInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={e => pickPhoto(e.target.files?.[0])}
              data-testid="avatar-studio-upload-photo-input"
            />
          </div>
        </div>
      </div>

      {/* Voice upload — only for voice_matched */}
      {needsVoice && (
        <div
          className={`rounded-2xl border-2 border-dashed p-5 transition-colors ${voiceSample ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-white/15 bg-white/[0.02]'}`}
          data-testid="avatar-studio-upload-voice-drop"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center shrink-0">
              <Mic className="w-5 h-5 text-cyan-200" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-white">Voice sample</div>
              <div className="text-xs text-slate-400 mt-0.5">10–30 seconds of you speaking clearly. MP3 / WAV / M4A, up to 12 MB.</div>
              {voiceSample ? (
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-emerald-300 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> {voiceSample.name}</div>
                    <div className="text-[11px] text-slate-500">{(voiceSample.size / 1024).toFixed(0)} KB</div>
                  </div>
                  <button
                    onClick={() => onVoiceSampleChange(null)}
                    className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:text-white"
                    data-testid="avatar-studio-upload-voice-remove-btn"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => voiceInputRef.current?.click()}
                  className="mt-3 px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-100 text-xs font-bold hover:bg-cyan-500/30"
                  data-testid="avatar-studio-upload-voice-pick-btn"
                >
                  Choose audio
                </button>
              )}
              <input
                ref={voiceInputRef}
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={e => pickVoice(e.target.files?.[0])}
                data-testid="avatar-studio-upload-voice-input"
              />
            </div>
          </div>
        </div>
      )}

      {err && (
        <div className="flex items-center gap-2 text-xs text-rose-300 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30"
             data-testid="avatar-studio-upload-error">
          <AlertCircle className="w-3.5 h-3.5" /> {err}
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={!readyToContinue}
          className="px-6 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          data-testid="avatar-studio-upload-next-btn"
        >
          Continue to motion <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
