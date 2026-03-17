import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Wand2, Loader2, Download, Check, Image,
  Sparkles, Coins, Crown, Lock, X, Camera, Zap, Shield,
  Grid3X3, User, Palette, RefreshCw, BookOpen, Share2,
  Copy, Twitter, MessageCircle, ExternalLink, ChevronRight,
  GitBranch, TrendingUp
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';

// ─── Constants ─────────────────────────────────────────────────────────
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
  { id: 'action', name: 'Action' }, { id: 'comedy', name: 'Comedy' },
  { id: 'romance', name: 'Romance' }, { id: 'adventure', name: 'Adventure' },
  { id: 'fantasy', name: 'Fantasy' }, { id: 'scifi', name: 'Sci-Fi' },
  { id: 'kids_friendly', name: 'Kids' },
];

const BLOCKED = [
  'marvel', 'dc', 'disney', 'naruto', 'pokemon', 'avengers', 'spiderman',
  'batman', 'superman', 'ironman', 'hulk', 'thor', 'captain america',
  'wonder woman', 'flash', 'joker', 'mickey', 'goku', 'pikachu', 'sonic'
];

const API = process.env.REACT_APP_BACKEND_URL;

export default function PhotoToComic() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // State
  const [credits, setCredits] = useState(null); // null = loading, not 0
  const [isUnlimited, setIsUnlimited] = useState(false);
  const [userPlan, setUserPlan] = useState('free');
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [storageKey, setStorageKey] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [mode, setMode] = useState('avatar');
  const [style, setStyle] = useState('cartoon_fun');
  const [genre, setGenre] = useState('action');
  const [panelCount, setPanelCount] = useState(4);
  const [storyPrompt, setStoryPrompt] = useState('');
  const [hd, setHd] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState('');
  const [result, setResult] = useState(null);
  const [validated, setValidated] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showRating, setShowRating] = useState(false);
  const [continuing, setContinuing] = useState(false);

  useEffect(() => {
    (async () => {
      // Attempt 1: credits/balance API
      try {
        const cr = await api.get('/api/credits/balance');
        const d = cr.data;
        setCredits(d.credits ?? d.balance ?? 0);
        setUserPlan(d.plan || 'free');
        if (d.unlimited) setIsUnlimited(true);
        return; // success
      } catch { /* fall through to retry */ }

      // Attempt 2: retry once
      try {
        const cr = await api.get('/api/credits/balance');
        const d = cr.data;
        setCredits(d.credits ?? d.balance ?? 0);
        setUserPlan(d.plan || 'free');
        if (d.unlimited) setIsUnlimited(true);
        return;
      } catch { /* fall through to auth/me fallback */ }

      // Attempt 3: fallback to /auth/me
      try {
        const ur = await api.get('/api/auth/me');
        const u = ur.data.user || ur.data;
        const role = (u.role || '').toUpperCase();
        const plan = u.plan || 'free';
        const isAdmin = role === 'ADMIN' || plan === 'admin';
        setUserPlan(isAdmin ? 'pro' : plan);
        if (isAdmin) {
          setIsUnlimited(true);
          setCredits(999999);
        } else {
          setCredits(u.credits ?? 0);
        }
      } catch {
        // Absolute last resort: do NOT default to 0 — set null to show loading
        setCredits(null);
      }
    })();
  }, []);

  // ─── Upload to R2 (via server proxy — no CORS issues) ────────
  const uploadToR2 = useCallback(async (file) => {
    setUploadProgress(10);
    try {
      const formData = new FormData();
      formData.append('file', file);
      setUploadProgress(30);

      const res = await api.post('/api/storage/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round(30 + (e.loaded / e.total) * 60));
        },
      });

      setUploadProgress(100);
      setStorageKey(res.data.storage_key);
      return res.data.storage_key;
    } catch (err) {
      console.warn('R2 upload failed, using fallback:', err.message);
      setUploadProgress(100);
      setStorageKey(null);
      return null;
    }
  }, []);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) { toast.error('Please upload an image'); return; }
    if (file.size > 15 * 1024 * 1024) { toast.error('Max 15MB'); return; }
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
    setResult(null);
    setJobId(null);

    // Upload to R2 in background
    uploadToR2(file);
  }, [uploadToR2]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer?.files?.[0]);
  }, [handleFile]);

  const removePhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
    setStorageKey(null);
    setUploadProgress(0);
  };

  // ─── Cost ────────────────────────────────────────────────────────
  const cost = (() => {
    let c = mode === 'avatar' ? 3 : ({ 3: 5, 4: 6, 6: 8 }[panelCount] || 6);
    if (hd) c += 2;
    const disc = { creator: 0.8, pro: 0.7, studio: 0.6 }[userPlan] || 1;
    return Math.max(1, Math.round(c * disc));
  })();
  const isPaid = !['free', ''].includes(userPlan);
  const isLocked = (tier) => tier === 'paid' && !isPaid;
  const canAfford = isUnlimited || (credits !== null && credits >= cost);

  // ─── Generate ────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!photoFile) { toast.error('Upload a photo first'); return; }
    if (!canAfford) { toast.error(`Need ${cost} credits`); navigate('/app/billing'); return; }
    if (storyPrompt) {
      const lower = storyPrompt.toLowerCase();
      for (const kw of BLOCKED) {
        if (lower.includes(kw)) { toast.error(`Copyrighted content: "${kw}"`); return; }
      }
    }

    setGenerating(true);
    setProgress(0);
    setProgressMsg('Starting generation...');
    setResult(null);

    try {
      const formData = new FormData();
      if (storageKey) {
        formData.append('storage_key', storageKey);
      } else {
        formData.append('photo', photoFile);
      }
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
      toast.error(err.response?.data?.detail || 'Generation failed');
      setGenerating(false);
    }
  };

  const pollJob = async (id) => {
    let attempts = 0;
    let lastProgressAt = Date.now();
    let lastProgress = -1;
    const STAGE_TIMEOUT = 60000; // 60s no progress = stale

    const poll = async () => {
      attempts++;
      try {
        const res = await api.get(`/api/photo-to-comic/job/${id}`);
        const job = res.data;
        const currentProgress = job.progress || 0;

        setProgress(currentProgress);
        setProgressMsg(job.progressMessage || 'Processing...');

        // Track real progress changes
        if (currentProgress !== lastProgress) {
          lastProgress = currentProgress;
          lastProgressAt = Date.now();
        }

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

        // Check for stale job — no progress update for 60s
        const staleMs = Date.now() - lastProgressAt;
        if (staleMs > STAGE_TIMEOUT && currentProgress < 90) {
          setProgressMsg('Taking longer than usual — hang tight or retry');
        }

        // Hard timeout: 3 minutes total
        if (attempts > 90) {
          setGenerating(false);
          toast.error('Generation timed out. Please try again.');
          return;
        }
      } catch {
        // Network error — keep trying
        if (attempts > 5) {
          setProgressMsg('Connection issue — retrying...');
        }
      }
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
          a.href = url; a.download = `comic_${jobId.slice(0, 8)}.png`;
          a.target = '_blank';
          document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }
        toast.success('Downloading!');
      }
    } catch { toast.error('Download failed'); }
    setDownloading(false);
  };

  // ─── Continue Story ──────────────────────────────────────────────
  const handleContinueStory = async (prompt = '') => {
    if (!jobId) return;
    if (!isUnlimited && credits < 6) { toast.error('Need at least 6 credits'); navigate('/app/billing'); return; }
    setContinuing(true);
    setGenerating(true);
    setProgress(0);
    setProgressMsg('Continuing your story...');
    try {
      const res = await api.post('/api/photo-to-comic/continue-story', {
        parentJobId: jobId,
        prompt,
        panelCount: 4,
        keepStyle: true,
      });
      if (res.data.success && res.data.jobId) {
        setJobId(res.data.jobId);
        setCredits(p => p - (res.data.estimatedCredits || 6));
        toast.success('Continuing your story!');
        pollJob(res.data.jobId);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Continue failed');
      setGenerating(false);
    }
    setContinuing(false);
  };

  // ─── Continue with Direction ────────────────────────────────────
  const [showDirections, setShowDirections] = useState(false);
  const [customContinuePrompt, setCustomContinuePrompt] = useState('');

  const CONTINUE_DIRECTIONS = [
    { id: 'next', label: 'Continue the Story', desc: 'Pick up right where it left off', prompt: '', icon: ChevronRight, color: 'border-blue-500/30 text-blue-400 hover:bg-blue-500/10' },
    { id: 'twist', label: 'Add a Plot Twist', desc: 'Surprise turn nobody expects', prompt: 'Add an unexpected plot twist that changes the direction of the story.', icon: Zap, color: 'border-amber-500/30 text-amber-400 hover:bg-amber-500/10' },
    { id: 'escalate', label: 'Raise the Stakes', desc: 'Bigger conflict, higher tension', prompt: 'Escalate the conflict dramatically. The hero faces a much bigger challenge.', icon: Sparkles, color: 'border-red-500/30 text-red-400 hover:bg-red-500/10' },
    { id: 'custom', label: 'Your Direction', desc: 'Write your own next chapter', prompt: '', icon: BookOpen, color: 'border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10' },
  ];

  // ─── Remix ───────────────────────────────────────────────────────
  const handleRemix = (newStyle) => {
    if (newStyle) setStyle(newStyle);
    setResult(null);
    setJobId(null);
    setValidated(false);
    // Keep photo + storage key, go back to builder with new style
  };

  // ─── Share ───────────────────────────────────────────────────────
  const handleShare = async (platform) => {
    const imageUrl = result?.resultUrl || result?.resultUrls?.[0] || result?.panels?.[0]?.imageUrl;
    const shareUrl = `${window.location.origin}/share/comic/${jobId}`;
    const text = 'Check out my AI-generated comic!';

    if (platform === 'copy') {
      try {
        await navigator.clipboard.writeText(shareUrl);
        toast.success('Link copied!');
      } catch { toast.error('Copy failed'); }
      return;
    }
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + shareUrl)}`,
    };
    if (urls[platform]) window.open(urls[platform], '_blank');
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

  // ─── RENDER ──────────────────────────────────────────────────────

  // === POST-GENERATION EXPERIENCE ===
  if (result) {
    const imageUrl = result.resultUrl || result.resultUrls?.[0];
    const panels = result.panels;
    const isStrip = result.mode === 'strip' || panels?.length > 0;
    return (
      <div className="min-h-screen bg-slate-950">
        <Header credits={credits} isUnlimited={isUnlimited} />
        <main className="max-w-5xl mx-auto px-4 py-8" data-testid="result-view">
          <div className="grid lg:grid-cols-[1fr_340px] gap-6">
            {/* LEFT: Result display */}
            <div className="space-y-4">
              {imageUrl && !panels && (
                <div className="rounded-2xl overflow-hidden border border-slate-700 bg-slate-900">
                  <img src={imageUrl} alt="Comic" className="w-full" crossOrigin="anonymous" data-testid="result-image" />
                </div>
              )}
              {panels?.length > 0 && (
                <div className="grid grid-cols-2 gap-3" data-testid="result-panels">
                  {panels.map((p, i) => (
                    <div key={i} className="rounded-xl overflow-hidden border border-slate-700 bg-slate-900 group">
                      <img src={p.imageUrl} alt={`Panel ${i + 1}`} className="w-full" crossOrigin="anonymous" />
                      {p.dialogue && (
                        <div className="p-2.5 text-xs text-slate-300 bg-slate-800/80 border-t border-slate-700">
                          {p.dialogue}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* RIGHT: Action Panel */}
            <div className="space-y-4 lg:sticky lg:top-20 self-start" data-testid="action-panel">
              {/* Status */}
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center shrink-0">
                  <Check className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">Comic Ready</p>
                  <p className="text-emerald-400/70 text-xs">Permanent asset — download anytime</p>
                </div>
              </div>

              {/* Primary actions */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                <Button
                  onClick={handleDownload}
                  disabled={downloading || !validated}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 py-4"
                  data-testid="download-btn"
                >
                  {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                  {downloading ? 'Downloading...' : !validated ? 'Validating...' : 'Download PNG'}
                </Button>

                {/* Share row */}
                <div className="flex gap-2" data-testid="share-actions">
                  <Button
                    variant="outline" size="sm"
                    onClick={() => handleShare('copy')}
                    className="flex-1 border-slate-700 text-slate-300 hover:text-white text-xs"
                    data-testid="share-copy-btn"
                  >
                    <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy Link
                  </Button>
                  <Button
                    variant="outline" size="sm"
                    onClick={() => handleShare('twitter')}
                    className="border-slate-700 text-slate-300 hover:text-white px-3"
                    data-testid="share-twitter-btn"
                  >
                    <Twitter className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="outline" size="sm"
                    onClick={() => handleShare('whatsapp')}
                    className="border-slate-700 text-slate-300 hover:text-white px-3"
                    data-testid="share-whatsapp-btn"
                  >
                    <MessageCircle className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>

              {/* Continue Story — upgraded with directions */}
              {isStrip && (
                <div className="bg-slate-900/80 border border-indigo-500/30 rounded-xl p-4 space-y-3" data-testid="continue-story-section">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-indigo-400" />
                      <h3 className="text-sm font-semibold text-white">Continue Story</h3>
                    </div>
                    <span className="text-[10px] text-indigo-400/70 bg-indigo-500/10 px-2 py-0.5 rounded-full">
                      {Math.max(1, Math.round(6 * ({ creator: 0.8, pro: 0.7, studio: 0.6 }[userPlan] || 1)))} cr
                    </span>
                  </div>

                  {!showDirections ? (
                    <>
                      <p className="text-xs text-slate-400">Choose a direction for your next 4 panels.</p>
                      <Button
                        onClick={() => setShowDirections(true)}
                        disabled={continuing || (!isUnlimited && credits < 6)}
                        className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                        data-testid="continue-story-btn"
                      >
                        <Sparkles className="w-4 h-4 mr-2" /> Choose Direction
                      </Button>
                    </>
                  ) : (
                    <div className="space-y-2" data-testid="continue-directions">
                      {CONTINUE_DIRECTIONS.map(d => (
                        <button
                          key={d.id}
                          onClick={() => {
                            if (d.id === 'custom') {
                              if (customContinuePrompt.trim()) {
                                handleContinueStory(customContinuePrompt);
                              }
                              return;
                            }
                            handleContinueStory(d.prompt);
                          }}
                          disabled={continuing || (!isUnlimited && credits < 6) || (d.id === 'custom' && !customContinuePrompt.trim())}
                          className={`w-full text-left flex items-center gap-3 p-3 rounded-lg border transition-all disabled:opacity-50 ${d.color}`}
                          data-testid={`direction-${d.id}`}
                        >
                          <d.icon className="w-4 h-4 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold">{d.label}</p>
                            <p className="text-[10px] opacity-70">{d.desc}</p>
                          </div>
                          {d.id !== 'custom' && <ChevronRight className="w-3.5 h-3.5 opacity-50" />}
                        </button>
                      ))}
                      <input
                        type="text"
                        value={customContinuePrompt}
                        onChange={(e) => setCustomContinuePrompt(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && customContinuePrompt.trim() && handleContinueStory(customContinuePrompt)}
                        placeholder="Your custom direction..."
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        data-testid="custom-direction-input"
                      />
                      <button
                        onClick={() => setShowDirections(false)}
                        className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Remix — try different style */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3" data-testid="remix-section">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-pink-400" />
                  <h3 className="text-sm font-semibold text-white">Remix</h3>
                </div>
                <p className="text-xs text-slate-400">Same photo, different style. Quick re-create.</p>
                <div className="grid grid-cols-4 gap-1.5">
                  {STYLES.filter(s => s.id !== style).slice(0, 4).map(s => (
                    <button
                      key={s.id}
                      onClick={() => handleRemix(s.id)}
                      className="rounded-lg overflow-hidden group hover:ring-2 hover:ring-pink-500 transition-all"
                      data-testid={`remix-style-${s.id}`}
                    >
                      <div className={`aspect-square bg-gradient-to-br ${s.color} flex items-center justify-center`}>
                        <RefreshCw className="w-3 h-3 text-white/0 group-hover:text-white/80 transition-all" />
                      </div>
                      <p className="text-[9px] text-slate-500 text-center py-0.5 bg-slate-800 truncate">{s.name}</p>
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => handleRemix(null)}
                  className="text-xs text-pink-400 hover:text-pink-300 flex items-center gap-1 transition-colors"
                  data-testid="remix-all-styles-btn"
                >
                  See all styles <ChevronRight className="w-3 h-3" />
                </button>
              </div>

              {/* Story Chain link */}
              <Button
                variant="outline"
                onClick={() => navigate(`/app/story-chain/${jobId}`)}
                className="w-full border-slate-700 text-slate-300 hover:text-white hover:border-purple-500/40"
                data-testid="view-story-chain-btn"
              >
                <GitBranch className="w-4 h-4 mr-2 text-purple-400" /> View Story Chain
              </Button>

              {/* Create new */}
              <Button
                variant="outline"
                onClick={resetAll}
                className="w-full border-slate-700 text-slate-400 hover:text-white"
                data-testid="create-another-btn"
              >
                <Camera className="w-4 h-4 mr-2" /> New Photo
              </Button>

              {!isPaid && (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-3 text-center">
                  <p className="text-slate-500 text-xs mb-2">Unlock premium styles & HD</p>
                  <Button onClick={() => navigate('/app/subscription')} size="sm" className="bg-purple-600 hover:bg-purple-700 text-xs h-7 px-3">
                    <Crown className="w-3 h-3 mr-1" /> Upgrade
                  </Button>
                </div>
              )}
            </div>
          </div>
        </main>
        <RatingModal isOpen={showRating} onClose={() => setShowRating(false)} featureKey="photo_to_comic" relatedRequestId={jobId} onSubmitSuccess={() => setShowRating(false)} />
      </div>
    );
  }

  // === GENERATING VIEW ===
  if (generating) {
    return (
      <div className="min-h-screen bg-slate-950">
        <Header credits={credits} isUnlimited={isUnlimited} />
        <main className="max-w-lg mx-auto px-4 py-20 text-center space-y-6" data-testid="generating-view">
          <div className="w-20 h-20 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto">
            <Loader2 className="w-10 h-10 text-purple-400 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-white">Creating Your Comic</h2>
          <p className="text-slate-400">{progressMsg}</p>
          <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-700 ease-out" style={{ width: `${Math.max(progress, 5)}%` }} />
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
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} data-testid="photo-input" />
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
          /* ── Builder ─────────────────────────────────────────── */
          <div className="grid lg:grid-cols-[1fr_320px] gap-6">
            <div className="space-y-5">
              {/* Photo preview + upload progress */}
              <div className="relative rounded-2xl overflow-hidden border border-slate-700 bg-slate-900 max-h-72 flex items-center justify-center" data-testid="photo-preview">
                <img src={photoPreview} alt="Your photo" className="max-h-72 object-contain" />
                <button onClick={removePhoto} className="absolute top-3 right-3 w-8 h-8 bg-slate-900/80 backdrop-blur rounded-full flex items-center justify-center hover:bg-red-600 transition-colors" data-testid="remove-photo-btn">
                  <X className="w-4 h-4 text-white" />
                </button>
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <div className="absolute bottom-0 left-0 right-0 bg-slate-900/80 p-2">
                    <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 text-center">Uploading to CDN...</p>
                  </div>
                )}
                {uploadProgress >= 100 && (
                  <div className="absolute bottom-3 right-3 bg-emerald-500/20 backdrop-blur rounded-full px-2 py-1 flex items-center gap-1">
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-[10px] text-emerald-400">CDN ready</span>
                  </div>
                )}
              </div>

              {/* Mode toggle */}
              <div className="flex gap-2" data-testid="mode-toggle">
                {[
                  { id: 'avatar', label: 'Comic Avatar', icon: User, desc: 'Single character' },
                  { id: 'strip', label: 'Comic Strip', icon: Grid3X3, desc: '3-6 panel story' },
                ].map((m) => (
                  <button
                    key={m.id} onClick={() => setMode(m.id)}
                    className={`flex-1 p-3 rounded-xl border-2 transition-all text-left ${
                      mode === m.id ? 'border-purple-500 bg-purple-500/10' : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
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
                        key={s.id} onClick={() => !locked && setStyle(s.id)} disabled={locked}
                        className={`relative p-2 rounded-xl text-center transition-all ${
                          selected ? 'ring-2 ring-purple-500 ring-offset-2 ring-offset-slate-950 scale-105'
                          : locked ? 'opacity-40 cursor-not-allowed' : 'hover:scale-105'
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
                        <button key={g.id} onClick={() => setGenre(g.id)} className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${genre === g.id ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`} data-testid={`genre-${g.id}`}>{g.name}</button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-400 mb-1.5 block">Panels</label>
                    <div className="flex gap-2" data-testid="panel-picker">
                      {[3, 4, 6].map(n => (
                        <button key={n} onClick={() => setPanelCount(n)} className={`w-12 h-10 rounded-lg font-bold text-sm transition-all ${panelCount === n ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`} data-testid={`panels-${n}`}>{n}</button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-400 mb-1.5 block">Story Prompt (optional)</label>
                    <textarea value={storyPrompt} onChange={e => setStoryPrompt(e.target.value.slice(0, 300))} placeholder="Describe the story..." rows={2} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none resize-none" data-testid="story-prompt-input" />
                    <p className="text-[10px] text-slate-600 mt-0.5">{storyPrompt.length}/300</p>
                  </div>
                </div>
              )}
            </div>

            {/* RIGHT: Cost sidebar */}
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
                  {hd && <div className="flex justify-between text-slate-400"><span>HD Export</span><span>+2 cr</span></div>}
                </div>
                <div className="border-t border-slate-700 pt-3 flex justify-between items-center">
                  <span className="text-white font-bold">Total</span>
                  <span className="text-xl font-bold text-purple-400">{cost} cr</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Balance</span>
                  <span className={canAfford ? 'text-emerald-400' : 'text-red-400'}>
                    {isUnlimited ? 'Unlimited' : credits === null ? '...' : `${credits} cr`}
                  </span>
                </div>
                <button onClick={() => setHd(!hd)} className={`w-full p-2.5 rounded-lg border text-sm flex items-center justify-between transition-all ${hd ? 'border-purple-500 bg-purple-500/10 text-white' : 'border-slate-700 text-slate-400 hover:border-slate-600'}`} data-testid="hd-toggle">
                  <span className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border flex items-center justify-center ${hd ? 'bg-purple-500 border-purple-500' : 'border-slate-500'}`}>{hd && <Check className="w-3 h-3 text-white" />}</div>
                    HD Export
                  </span>
                  <span className="text-purple-400 text-xs font-medium">+2 cr</span>
                </button>
                <Button onClick={handleGenerate} disabled={!canAfford || credits === null} className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 py-5 text-base font-semibold" data-testid="generate-btn">
                  <Wand2 className="w-5 h-5 mr-2" /> Create My Comic
                </Button>
                {!canAfford && credits !== null && (
                  <Button variant="outline" onClick={() => navigate('/app/billing')} className="w-full border-yellow-600/50 text-yellow-400 hover:bg-yellow-600/10 text-xs">
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

function Header({ credits, isUnlimited }) {
  return (
    <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/app">
            <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white px-2"><ArrowLeft className="w-4 h-4" /></Button>
          </Link>
          <div>
            <h1 className="text-base font-bold text-white">Photo to Comic</h1>
            <p className="text-[10px] text-slate-500 hidden sm:block">Upload a photo, get original comic art</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-800/50 rounded-full px-3 py-1.5 border border-slate-700">
          <Coins className="w-3.5 h-3.5 text-yellow-400" />
          <span className="font-bold text-white text-sm" data-testid="credit-display">
            {isUnlimited ? '∞' : credits === null ? '...' : credits}
          </span>
        </div>
      </div>
    </header>
  );
}
