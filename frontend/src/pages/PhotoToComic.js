import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Wand2, Loader2, Download, Check, Image,
  Sparkles, Coins, Crown, Lock, X, Camera, Zap, Shield,
  ChevronDown, Grid3X3, User, Palette
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';
import ShareCreation from '../components/ShareCreation';

// ─── Style Presets ─────────────────────────────────────────────────────
const STYLES = [
  { id: 'bold_superhero', name: 'Bold Hero', color: 'from-red-600 to-orange-500', tier: 'free' },
  { id: 'cartoon_fun', name: 'Cartoon', color: 'from-yellow-500 to-amber-400', tier: 'free' },
  { id: 'retro_action', name: 'Retro Pop', color: 'from-pink-500 to-rose-400', tier: 'free' },
  { id: 'soft_manga', name: 'Manga', color: 'from-indigo-500 to-violet-400', tier: 'free' },
  { id: 'cute_chibi', name: 'Chibi', color: 'from-emerald-500 to-teal-400', tier: 'free' },
  { id: 'kids_storybook', name: 'Storybook', color: 'from-sky-500 to-cyan-400', tier: 'free' },
  { id: 'noir_comic', name: 'Noir', color: 'from-slate-600 to-zinc-500', tier: 'free' },
  { id: 'scifi_neon', name: 'Sci-Fi Neon', color: 'from-fuchsia-600 to-purple-500', tier: 'paid' },
  { id: 'cyberpunk_comic', name: 'Cyberpunk', color: 'from-cyan-500 to-blue-600', tier: 'paid' },
  { id: 'magical_fantasy', name: 'Fantasy', color: 'from-violet-600 to-indigo-500', tier: 'paid' },
  { id: 'dreamy_pastel', name: 'Pastel', color: 'from-rose-400 to-pink-300', tier: 'paid' },
  { id: 'black_white_ink', name: 'Ink Art', color: 'from-gray-700 to-gray-500', tier: 'paid' },
];

const GENRES = [
  { id: 'action', name: 'Action' },
  { id: 'comedy', name: 'Comedy' },
  { id: 'romance', name: 'Romance' },
  { id: 'adventure', name: 'Adventure' },
  { id: 'fantasy', name: 'Fantasy' },
  { id: 'scifi', name: 'Sci-Fi' },
  { id: 'kids_friendly', name: 'Kids' },
];

const BLOCKED = [
  'marvel', 'dc', 'disney', 'naruto', 'pokemon', 'avengers', 'spiderman',
  'batman', 'superman', 'ironman', 'hulk', 'thor', 'captain america',
  'wonder woman', 'flash', 'joker', 'mickey', 'goku', 'pikachu', 'sonic'
];

export default function PhotoToComic() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const dropRef = useRef(null);

  // ─── State ───────────────────────────────────────────────────────
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');

  // Upload
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [storageKey, setStorageKey] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Config
  const [mode, setMode] = useState('avatar');
  const [style, setStyle] = useState('cartoon_fun');
  const [genre, setGenre] = useState('action');
  const [panelCount, setPanelCount] = useState(4);
  const [storyPrompt, setStoryPrompt] = useState('');
  const [hd, setHd] = useState(false);

  // Generation
  const [generating, setGenerating] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState('');
  const [result, setResult] = useState(null);
  const [validated, setValidated] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showRating, setShowRating] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [cr, ur] = await Promise.all([
          api.get('/api/credits/balance'),
          api.get('/api/auth/me')
        ]);
        setCredits(cr.data.credits || 0);
        setUserPlan(ur.data.user?.plan || ur.data.plan || 'free');
      } catch { /* noop */ }
    })();
  }, []);

  // ─── Photo handling ──────────────────────────────────────────────
  const handleFile = useCallback((file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) { toast.error('Please upload an image'); return; }
    if (file.size > 15 * 1024 * 1024) { toast.error('Max 15MB'); return; }
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
    setResult(null);
    setJobId(null);
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    handleFile(file);
  }, [handleFile]);

  const removePhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
    setStorageKey(null);
  };

  // ─── Cost ────────────────────────────────────────────────────────
  const cost = (() => {
    let c = mode === 'avatar' ? 3 : ({ 3: 5, 4: 6, 6: 8 }[panelCount] || 6);
    if (hd) c += 2;
    const disc = { creator: 0.8, pro: 0.7, studio: 0.6 }[userPlan] || 1;
    return Math.max(1, Math.round(c * disc));
  })();

  // ─── Generate ────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!photoFile) { toast.error('Upload a photo first'); return; }
    if (credits < cost) { toast.error(`Need ${cost} credits`); navigate('/app/billing'); return; }

    if (storyPrompt) {
      const lower = storyPrompt.toLowerCase();
      for (const kw of BLOCKED) {
        if (lower.includes(kw)) { toast.error(`Copyrighted content: "${kw}"`); return; }
      }
    }

    setGenerating(true);
    setProgress(0);
    setProgressMsg('Uploading...');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('photo', photoFile);
      formData.append('mode', mode);
      formData.append('style', style);
      formData.append('genre', genre);
      formData.append('panel_count', String(panelCount));
      formData.append('hd_export', String(hd));
      formData.append('include_dialogue', 'true');
      if (mode === 'strip' && storyPrompt) {
        formData.append('story_prompt', storyPrompt);
      }

      const res = await api.post('/api/photo-to-comic/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (res.data.success && res.data.jobId) {
        setJobId(res.data.jobId);
        setCredits(p => p - cost);
        toast.success('Creating your comic!');
        pollJob(res.data.jobId);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Generation failed';
      toast.error(msg);
      setGenerating(false);
    }
  };

  const pollJob = async (id) => {
    let attempts = 0;
    const poll = async () => {
      if (attempts++ > 90) { setGenerating(false); toast.error('Timed out'); return; }
      try {
        const res = await api.get(`/api/photo-to-comic/job/${id}`);
        const job = res.data;
        setProgress(job.progress || 0);
        setProgressMsg(job.progressMessage || 'Processing...');

        if (job.status === 'COMPLETED') {
          setGenerating(false);
          setResult(job);
          validateAsset(id);
          setTimeout(() => setShowRating(true), 3000);
          return;
        }
        if (job.status === 'FAILED') {
          setGenerating(false);
          toast.error(job.error || 'Generation failed. Credits refunded.');
          return;
        }
      } catch { /* retry */ }
      setTimeout(poll, 2000);
    };
    poll();
  };

  const validateAsset = async (id) => {
    try {
      const res = await api.get(`/api/photo-to-comic/validate-asset/${id}`);
      setValidated(res.data.valid === true);
    } catch { setValidated(true); }
  };

  const handleDownload = async () => {
    if (!jobId) return;
    setDownloading(true);
    try {
      const res = await api.post(`/api/photo-to-comic/download/${jobId}`);
      if (res.data.downloadUrls?.length) {
        for (const url of res.data.downloadUrls) {
          const a = document.createElement('a');
          a.href = url;
          a.download = `comic_${jobId.slice(0, 8)}.png`;
          a.target = '_blank';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
        toast.success('Downloading!');
      }
    } catch { toast.error('Download failed'); }
    setDownloading(false);
  };

  const resetAll = () => {
    removePhoto();
    setMode('avatar');
    setStyle('cartoon_fun');
    setGenre('action');
    setPanelCount(4);
    setStoryPrompt('');
    setHd(false);
    setResult(null);
    setJobId(null);
    setProgress(0);
    setGenerating(false);
    setValidated(false);
  };

  const isPaid = !['free', ''].includes(userPlan);
  const isLocked = (tier) => tier === 'paid' && !isPaid;

  // ─── RENDER ──────────────────────────────────────────────────────

  // === RESULT VIEW ===
  if (result) {
    const imageUrl = result.resultUrl || result.resultUrls?.[0];
    const panels = result.panels;
    return (
      <div className="min-h-screen bg-slate-950">
        <Header credits={credits} />
        <main className="max-w-4xl mx-auto px-4 py-8 space-y-6" data-testid="result-view">
          <div className="text-center space-y-3">
            <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-white">Your Comic is Ready</h2>
            <p className="text-slate-400 text-sm">Permanent asset — download anytime</p>
          </div>

          {imageUrl && !panels && (
            <div className="max-w-md mx-auto rounded-2xl overflow-hidden border border-slate-700 bg-slate-900">
              <img src={imageUrl} alt="Comic" className="w-full" crossOrigin="anonymous" data-testid="result-image" />
            </div>
          )}

          {panels?.length > 0 && (
            <div className="grid grid-cols-2 gap-3 max-w-2xl mx-auto" data-testid="result-panels">
              {panels.map((p, i) => (
                <div key={i} className="rounded-xl overflow-hidden border border-slate-700 bg-slate-900">
                  <img src={p.imageUrl} alt={`Panel ${i + 1}`} className="w-full" crossOrigin="anonymous" />
                  {p.dialogue && <div className="p-2 text-xs text-slate-300 bg-slate-800">{p.dialogue}</div>}
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3 justify-center flex-wrap pt-2">
            <Button
              onClick={handleDownload}
              disabled={downloading || !validated}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
              data-testid="download-btn"
            >
              {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
              {downloading ? 'Downloading...' : !validated ? 'Validating...' : 'Download'}
            </Button>
            <ShareCreation
              type={mode === 'avatar' ? 'COMIC_AVATAR' : 'COMIC_STRIP'}
              title="My Comic"
              preview="Made with Visionary Suite"
              generationId={jobId}
            />
            <Button variant="outline" onClick={resetAll} className="border-slate-600 text-slate-300 hover:text-white" data-testid="create-another-btn">
              Create Another
            </Button>
          </div>

          {!isPaid && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 max-w-sm mx-auto text-center">
              <p className="text-slate-400 text-sm mb-2">Unlock premium styles & HD export</p>
              <Button onClick={() => navigate('/app/subscription')} size="sm" className="bg-purple-600 hover:bg-purple-700">
                <Crown className="w-4 h-4 mr-1" /> Upgrade
              </Button>
            </div>
          )}
        </main>
        <RatingModal isOpen={showRating} onClose={() => setShowRating(false)} featureKey="photo_to_comic" relatedRequestId={jobId} onSubmitSuccess={() => setShowRating(false)} />
      </div>
    );
  }

  // === GENERATING VIEW ===
  if (generating) {
    return (
      <div className="min-h-screen bg-slate-950">
        <Header credits={credits} />
        <main className="max-w-lg mx-auto px-4 py-20 text-center space-y-6" data-testid="generating-view">
          <div className="w-20 h-20 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto">
            <Loader2 className="w-10 h-10 text-purple-400 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-white">Creating Your Comic</h2>
          <p className="text-slate-400">{progressMsg}</p>
          <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${Math.max(progress, 5)}%` }}
            />
          </div>
          <p className="text-xs text-slate-500">{progress}%</p>
        </main>
      </div>
    );
  }

  // === MAIN BUILDER VIEW (Upload-first) ===
  return (
    <div className="min-h-screen bg-slate-950">
      <Header credits={credits} />

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* ── Hero Upload Zone ─────────────────────────────────── */}
        {!photoPreview ? (
          <div
            ref={dropRef}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative cursor-pointer rounded-2xl border-2 border-dashed transition-all duration-300 ${
              isDragging
                ? 'border-purple-400 bg-purple-500/10 scale-[1.01]'
                : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
            } py-16 px-8 text-center`}
            data-testid="upload-zone"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
              data-testid="photo-input"
            />
            <div className="space-y-4">
              <div className="w-20 h-20 bg-purple-500/15 rounded-2xl flex items-center justify-center mx-auto">
                <Camera className="w-10 h-10 text-purple-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Drop your photo here</h2>
                <p className="text-slate-400 mt-1">or click to browse — PNG, JPG up to 15MB</p>
              </div>
              <div className="flex items-center justify-center gap-6 text-xs text-slate-500 pt-2">
                <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" /> Face photos work best</span>
                <span className="flex items-center gap-1"><Shield className="w-3.5 h-3.5" /> 100% original art</span>
                <span className="flex items-center gap-1"><Zap className="w-3.5 h-3.5" /> ~30s generation</span>
              </div>
            </div>
          </div>
        ) : (
          /* ── Photo uploaded → show builder ──────────────────── */
          <div className="grid lg:grid-cols-[1fr_320px] gap-6">
            {/* LEFT: Preview + Config */}
            <div className="space-y-5">
              {/* Photo preview */}
              <div className="relative rounded-2xl overflow-hidden border border-slate-700 bg-slate-900 max-h-72 flex items-center justify-center" data-testid="photo-preview">
                <img src={photoPreview} alt="Your photo" className="max-h-72 object-contain" />
                <button
                  onClick={removePhoto}
                  className="absolute top-3 right-3 w-8 h-8 bg-slate-900/80 backdrop-blur rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
                  data-testid="remove-photo-btn"
                >
                  <X className="w-4 h-4 text-white" />
                </button>
              </div>

              {/* Mode toggle */}
              <div className="flex gap-2" data-testid="mode-toggle">
                {[
                  { id: 'avatar', label: 'Comic Avatar', icon: User, desc: 'Single character' },
                  { id: 'strip', label: 'Comic Strip', icon: Grid3X3, desc: '3-6 panel story' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setMode(m.id)}
                    className={`flex-1 p-3 rounded-xl border-2 transition-all text-left ${
                      mode === m.id
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
                    }`}
                    data-testid={`mode-${m.id}`}
                  >
                    <div className="flex items-center gap-2">
                      <m.icon className={`w-4 h-4 ${mode === m.id ? 'text-purple-400' : 'text-slate-500'}`} />
                      <span className={`font-medium text-sm ${mode === m.id ? 'text-white' : 'text-slate-300'}`}>{m.label}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 ml-6">{m.desc}</p>
                  </button>
                ))}
              </div>

              {/* Style grid */}
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-1.5">
                  <Palette className="w-3.5 h-3.5" /> Style
                </h3>
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-2" data-testid="style-grid">
                  {STYLES.map((s) => {
                    const locked = isLocked(s.tier);
                    const selected = style === s.id;
                    return (
                      <button
                        key={s.id}
                        onClick={() => !locked && setStyle(s.id)}
                        disabled={locked}
                        className={`relative p-2 rounded-xl text-center transition-all ${
                          selected
                            ? 'ring-2 ring-purple-500 ring-offset-2 ring-offset-slate-950 scale-105'
                            : locked
                            ? 'opacity-40 cursor-not-allowed'
                            : 'hover:scale-105'
                        }`}
                        data-testid={`style-${s.id}`}
                      >
                        <div className={`w-full aspect-square rounded-lg bg-gradient-to-br ${s.color} mb-1.5 flex items-center justify-center`}>
                          {locked && <Lock className="w-4 h-4 text-white/70" />}
                          {selected && <Check className="w-5 h-5 text-white drop-shadow" />}
                        </div>
                        <span className="text-[10px] font-medium text-slate-400 leading-tight block">{s.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Strip-specific options */}
              {mode === 'strip' && (
                <div className="space-y-3 bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                  <div>
                    <label className="text-sm font-medium text-slate-400 mb-1.5 block">Genre</label>
                    <div className="flex flex-wrap gap-1.5" data-testid="genre-picker">
                      {GENRES.map(g => (
                        <button
                          key={g.id}
                          onClick={() => setGenre(g.id)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                            genre === g.id
                              ? 'bg-purple-600 text-white'
                              : 'bg-slate-800 text-slate-400 hover:text-white'
                          }`}
                          data-testid={`genre-${g.id}`}
                        >
                          {g.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-400 mb-1.5 block">Panels</label>
                    <div className="flex gap-2" data-testid="panel-picker">
                      {[3, 4, 6].map(n => (
                        <button
                          key={n}
                          onClick={() => setPanelCount(n)}
                          className={`w-12 h-10 rounded-lg font-bold text-sm transition-all ${
                            panelCount === n
                              ? 'bg-purple-600 text-white'
                              : 'bg-slate-800 text-slate-400 hover:text-white'
                          }`}
                          data-testid={`panels-${n}`}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-400 mb-1.5 block">Story Prompt (optional)</label>
                    <textarea
                      value={storyPrompt}
                      onChange={e => setStoryPrompt(e.target.value.slice(0, 300))}
                      placeholder="Describe the story for your comic strip..."
                      rows={2}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none resize-none"
                      data-testid="story-prompt-input"
                    />
                    <p className="text-[10px] text-slate-600 mt-0.5">{storyPrompt.length}/300</p>
                  </div>
                </div>
              )}
            </div>

            {/* RIGHT: Sticky sidebar — cost + generate */}
            <div className="lg:sticky lg:top-20 space-y-4 self-start">
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4" data-testid="cost-summary">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <Coins className="w-4 h-4 text-yellow-400" /> Summary
                </h3>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-slate-300">
                    <span>{mode === 'avatar' ? 'Comic Avatar' : `${panelCount}-Panel Strip`}</span>
                    <span>{mode === 'avatar' ? 3 : ({ 3: 5, 4: 6, 6: 8 }[panelCount] || 6)} cr</span>
                  </div>
                  {hd && (
                    <div className="flex justify-between text-slate-400">
                      <span>HD Export</span>
                      <span>+2 cr</span>
                    </div>
                  )}
                </div>

                <div className="border-t border-slate-700 pt-3 flex justify-between items-center">
                  <span className="text-white font-bold">Total</span>
                  <span className="text-xl font-bold text-purple-400">{cost} cr</span>
                </div>

                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Balance</span>
                  <span className={credits >= cost ? 'text-emerald-400' : 'text-red-400'}>{credits} cr</span>
                </div>

                {/* HD toggle */}
                <button
                  onClick={() => setHd(!hd)}
                  className={`w-full p-2.5 rounded-lg border text-sm flex items-center justify-between transition-all ${
                    hd ? 'border-purple-500 bg-purple-500/10 text-white' : 'border-slate-700 text-slate-400 hover:border-slate-600'
                  }`}
                  data-testid="hd-toggle"
                >
                  <span className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border flex items-center justify-center ${hd ? 'bg-purple-500 border-purple-500' : 'border-slate-500'}`}>
                      {hd && <Check className="w-3 h-3 text-white" />}
                    </div>
                    HD Export
                  </span>
                  <span className="text-purple-400 text-xs font-medium">+2 cr</span>
                </button>

                <Button
                  onClick={handleGenerate}
                  disabled={credits < cost}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 py-5 text-base font-semibold"
                  data-testid="generate-btn"
                >
                  <Wand2 className="w-5 h-5 mr-2" />
                  Create My Comic
                </Button>

                {credits < cost && (
                  <Button
                    variant="outline"
                    onClick={() => navigate('/app/billing')}
                    className="w-full border-yellow-600/50 text-yellow-400 hover:bg-yellow-600/10 text-xs"
                  >
                    <Coins className="w-3.5 h-3.5 mr-1" /> Get Credits
                  </Button>
                )}
              </div>

              <div className="text-[10px] text-slate-600 text-center flex items-center justify-center gap-1">
                <Shield className="w-3 h-3" /> 100% original art, no copyrighted characters
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ─── Header sub-component ──────────────────────────────────────────────
function Header({ credits }) {
  return (
    <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/app">
            <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white px-2">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-base font-bold text-white">Photo to Comic</h1>
            <p className="text-[10px] text-slate-500 hidden sm:block">Upload a photo, get original comic art</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-800/50 rounded-full px-3 py-1.5 border border-slate-700">
          <Coins className="w-3.5 h-3.5 text-yellow-400" />
          <span className="font-bold text-white text-sm">{credits}</span>
        </div>
      </div>
    </header>
  );
}
