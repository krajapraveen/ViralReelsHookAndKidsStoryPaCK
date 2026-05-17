import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Wand2, Camera, Loader2, Download,
  Check, AlertTriangle, Shield, Sparkles, Image,
  Smile, Heart, Zap, Flame, PackageOpen, RefreshCw,
  Share2, Copy, ExternalLink, X, ChevronRight, Lock,
  Film, BookOpen, Palette,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import { toastErrorSafe, extractRequestId } from '../utils/toastSafe';
import RatingModal from '../components/RatingModal';
import UpsellModal from '../components/UpsellModal';
import BedtimePaywallModal from '../components/BedtimePaywallModal';
import { useNotifications } from '../contexts/NotificationContext';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ─── P0 2026-05 — Admin / unlimited detection (mirrors backend
// services/entitlement.is_unlimited_user / has_full_content_access).
const _UNLIMITED_ROLES = ['admin', 'owner', 'dev', 'qa', 'qa_user', 'test'];
function _detectUnlimitedFromLocalStorage() {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}');
    const role = String(u?.role || '').toLowerCase();
    return Boolean(u?.is_unlimited) || _UNLIMITED_ROLES.includes(role);
  } catch (_) { return false; }
}

// ════════════════════════════════════════════
// REACTIONS
// ════════════════════════════════════════════
const REACTIONS = [
  { id: 'happy', emoji: '😀', name: 'Happy', color: 'from-yellow-400 to-amber-500' },
  { id: 'laughing', emoji: '😂', name: 'LOL', color: 'from-yellow-500 to-orange-500' },
  { id: 'love', emoji: '😍', name: 'Love', color: 'from-pink-400 to-rose-500' },
  { id: 'cool', emoji: '😎', name: 'Cool', color: 'from-blue-400 to-cyan-500' },
  { id: 'surprised', emoji: '😮', name: 'Shocked', color: 'from-purple-400 to-violet-500' },
  { id: 'sad', emoji: '😢', name: 'Sad', color: 'from-blue-500 to-indigo-600' },
  { id: 'celebrate', emoji: '👏', name: 'Celebrate', color: 'from-green-400 to-emerald-500' },
  { id: 'waving', emoji: '👋', name: 'Hello', color: 'from-orange-400 to-amber-500' },
  { id: 'wow', emoji: '🔥', name: 'Fire', color: 'from-red-500 to-orange-600' },
];

// ════════════════════════════════════════════
// STYLE PACKS
// ════════════════════════════════════════════
const STYLE_PACKS = [
  { id: 'classic', name: 'Classic', emoji: '🎨', styles: ['cartoon_motion', 'comic_bounce', 'sticker_style', 'neon_glow', 'minimal_clean'] },
  { id: 'meme', name: 'Meme Pack', emoji: '😂', styles: ['meme_classic', 'meme_deepfried'] },
  { id: 'pixar', name: '3D Animated', emoji: '🎬', styles: ['pixar_3d', 'pixar_clay'] },
  { id: 'anime', name: 'Anime Pack', emoji: '🔥', styles: ['anime_shonen', 'anime_chibi'] },
  { id: 'desi', name: 'Desi Pack', emoji: '🇮🇳', styles: ['desi_bollywood', 'desi_comic'] },
  { id: 'corporate', name: 'Corporate', emoji: '💼', styles: ['corporate_clean', 'corporate_flat'] },
];

const ALL_STYLES = {
  cartoon_motion: 'Cartoon Motion',
  comic_bounce: 'Comic Bounce',
  sticker_style: 'Sticker Style',
  neon_glow: 'Neon Glow',
  minimal_clean: 'Minimal Clean',
  meme_classic: 'Meme Classic',
  meme_deepfried: 'Deep Fried',
  pixar_3d: '3D Animated',
  pixar_clay: 'Claymation',
  anime_shonen: 'Anime Shonen',
  anime_chibi: 'Anime Chibi',
  desi_bollywood: 'Indian Cinema',
  desi_comic: 'Desi Comic',
  corporate_clean: 'Office Humor',
  corporate_flat: 'Flat Vector',
};

// Random auto-select
const pickRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];
const AUTO_REACTIONS = ['laughing', 'surprised', 'wow', 'cool', 'love'];
const AUTO_STYLES = ['cartoon_motion', 'pixar_3d', 'anime_shonen', 'meme_classic'];

// ════════════════════════════════════════════
// COMPONENT
// ════════════════════════════════════════════
export default function PhotoReactionGIF() {
  const navigate = useNavigate();
  // Core state
  const [phase, setPhase] = useState('upload'); // upload | generating | result
  const [credits, setCredits] = useState(0);
  const [firstFree, setFirstFree] = useState(false);
  // P0 2026-05 — admin / unlimited / subscriber detection
  const [isUnlimitedUser, setIsUnlimitedUser] = useState(_detectUnlimitedFromLocalStorage);
  const [paywall, setPaywall] = useState({ open: false, reason: null });

  // Upload
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);

  // Selection
  const [selectedReaction, setSelectedReaction] = useState(pickRandom(AUTO_REACTIONS));
  const [selectedPack, setSelectedPack] = useState('classic');
  const [selectedStyle, setSelectedStyle] = useState('cartoon_motion');

  // Generation
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const pollingRef = useRef(null);
  const completedRef = useRef(new Set());
  // ─── P0 2026-05-22 — Connection-loss resilience refs ─────────────
  // Bug-class elimination (see ENGINEERING_DOCTRINE.md → Bug-Class
  // Elimination Mandate). A single transient poll failure must NOT
  // declare the entire generation lost; the backend job keeps running
  // and the user must be able to recover on reconnect.
  const consecutiveFailRef = useRef(0);
  const lostToastShownRef = useRef(false);
  const lastRequestIdRef = useRef(null);
  const POLL_FAIL_TOLERANCE = 5;        // ~10s of transient failures absorbed silently
  const POLL_HARD_LIMIT = 90;           // ~3 minutes total before we give up

  // ─── P0 2026-05-22 — Asset-readiness gate (false-success fix) ────
  // The backend now marks `assetVerified=true` only when the file
  // on disk passed a magic-byte / size check. In addition, the
  // frontend MUST run its own in-browser image preload probe before
  // exposing share / download / copy-link actions, because a CDN
  // cache, network fault, or content-type mismatch can still make
  // a backend-verified file fail to render here.
  const [previewReady, setPreviewReady] = useState(false);
  const [previewProbing, setPreviewProbing] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const previewProbeAttemptsRef = useRef(0);
  const PREVIEW_PROBE_MAX_ATTEMPTS = 5;
  const PREVIEW_PROBE_TIMEOUT_MS = 8000;

  // Modals
  const [showRating, setShowRating] = useState(false);
  const [showUpsell, setShowUpsell] = useState(false);
  const [showShare, setShowShare] = useState(false);
  const [packDownloading, setPackDownloading] = useState(false);

  const { notifyGenerationComplete, notifyGenerationFailed, refetchNotifications } = useNotifications();

  // P0 2026-05 — effective access flag. Backend is the source of truth via
  // job.access.full_access; local isUnlimitedUser is the defense-in-depth.
  // IMPORTANT: Must be defined before useEffect that references it.
  const canAccessFull = isUnlimitedUser || Boolean(job?.access?.full_access);

  useEffect(() => {
    fetchInit();
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, []);

  // P0 2026-05 — Block copy/save/print shortcuts while result is shown,
  // for non-premium users. Frontend deterrent only; the real protection
  // is the backend gate on /download/:job_id.
  useEffect(() => {
    if (phase !== 'result' || canAccessFull) return undefined;
    const onKey = (e) => {
      const k = (e.key || '').toLowerCase();
      if (!(e.metaKey || e.ctrlKey)) return;
      if (['c', 'x', 's', 'p', 'a'].includes(k)) {
        e.preventDefault();
        e.stopPropagation();
        if (k === 's' || k === 'p') {
          setPaywall({ open: true, reason: 'download' });
        } else {
          setPaywall({ open: true, reason: 'copy' });
        }
      }
    };
    const onCopy = (e) => { e.preventDefault(); setPaywall({ open: true, reason: 'copy' }); };
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('copy', onCopy, true);
    window.addEventListener('cut', onCopy, true);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      window.removeEventListener('copy', onCopy, true);
      window.removeEventListener('cut', onCopy, true);
    };
  }, [phase, canAccessFull]);

  const fetchInit = async () => {
    try {
      const [credRes, reactRes] = await Promise.all([
        api.get('/api/credits/balance'),
        api.get('/api/reaction-gif/reactions'),
      ]);
      setCredits(credRes.data.balance ?? credRes.data.credits ?? 0);
      setFirstFree(reactRes.data.first_free || false);
      if (credRes.data.is_unlimited === true || credRes.data.unlimited === true) {
        setIsUnlimitedUser(true);
      }
    } catch {
      toast.error('Failed to load tool data. Try refreshing.');
    }
  };

  // ── Photo handlers ──
  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { toast.error('Image too large. Max 10MB.'); return; }
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
    setJob(null);
    setPhase('upload');
  };

  const clearPhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(null);
    setPhotoPreview(null);
    setJob(null);
    setPhase('upload');
  };

  // ── Style pack handler ──
  const handlePackSelect = (packId) => {
    setSelectedPack(packId);
    const pack = STYLE_PACKS.find(p => p.id === packId);
    if (pack) setSelectedStyle(pack.styles[0]);
  };

  // ── Generate ──
  const generate = async (reactionOverride, styleOverride) => {
    if (!photo) { toast.error('Upload a photo first'); return; }
    const reaction = reactionOverride || selectedReaction;
    const style = styleOverride || selectedStyle;

    const cost = firstFree ? 0 : 8;
    if (!firstFree && credits < cost) {
      toast.error(`Need ${cost} credits`);
      setShowUpsell(true);
      return;
    }

    setLoading(true);
    setPhase('generating');
    setJob(null);
    // ─── P0 2026-05-22 — reset asset-readiness gate on new submission
    setPreviewReady(false);
    setPreviewProbing(false);
    setPreviewFailed(false);
    previewProbeAttemptsRef.current = 0;

    try {
      const formData = new FormData();
      formData.append('photo', photo);
      formData.append('mode', 'single');
      formData.append('reaction', reaction);
      formData.append('style', style);
      formData.append('hd_quality', false);
      formData.append('transparent_bg', false);
      formData.append('caption', '');
      formData.append('commercial_license', false);

      const res = await api.post('/api/reaction-gif/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setJob({ id: res.data.jobId, status: 'QUEUED', progress: 0 });
      setSelectedReaction(reaction);
      setSelectedStyle(style);

      // Reset connection-loss resilience state for the new job.
      consecutiveFailRef.current = 0;
      lostToastShownRef.current = false;
      lastRequestIdRef.current =
        res.headers?.['x-request-id'] || res.headers?.['X-Request-Id'] || null;
      try { toast.dismiss('reaction-gif-connection-lost'); } catch (_) { /* noop */ }
      try {
        sessionStorage.setItem('reaction_gif_active_job_id', res.data.jobId);
      } catch (_) { /* noop */ }

      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = setInterval(() => pollJob(res.data.jobId), 2000);
    } catch (e) {
      setLoading(false);
      setPhase('upload');
      toast.error(e.response?.data?.detail || 'Generation failed');
    }
  };

  // ── Beacon helper (best-effort, never throws) ──
  const _emitBeacon = useCallback((metric, meta = {}) => {
    try {
      api.post('/api/diagnostics/beacon', {
        events: [{
          metric,
          ts: Date.now(),
          page: '/app/gif-maker',
          meta: { request_id: lastRequestIdRef.current, ...meta },
        }],
      }).catch(() => {});
    } catch (_) { /* never break UX */ }
  }, []);

  // ── P0 2026-05-22 — In-browser asset readiness probe ──
  // The backend's `assetVerified` flag asserts the file on disk is a
  // real image. The frontend STILL has to confirm the browser can
  // actually fetch and decode it — a CDN cache miss, content-type
  // mismatch, or temporary 5xx between job COMPLETION and first
  // render will all produce the same broken-image bug we are
  // eliminating. The probe retries with exponential backoff and only
  // flips `previewReady=true` on a clean decode.
  const runPreviewProbe = useCallback((rawUrl) => {
    if (!rawUrl) {
      setPreviewFailed(true);
      _emitBeacon('reaction_gif_broken_preview_total', { reason: 'no_url' });
      return;
    }
    _emitBeacon('reaction_gif_asset_verify_started_total', {});
    setPreviewProbing(true);
    setPreviewFailed(false);

    const absolute = rawUrl.startsWith('http') ? rawUrl : `${API_URL}${rawUrl}`;

    const attempt = () => {
      previewProbeAttemptsRef.current += 1;
      const att = previewProbeAttemptsRef.current;
      // Cache-bust on retries so a stale CDN 404 doesn't lock us out.
      const cacheBust = att === 1 ? '' : (absolute.includes('?') ? `&_p=${att}_${Date.now()}` : `?_p=${att}_${Date.now()}`);
      const probeUrl = absolute + cacheBust;

      const img = new window.Image();
      let settled = false;

      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        // eslint-disable-next-line no-use-before-define
        onFail('timeout');
      }, PREVIEW_PROBE_TIMEOUT_MS);

      const onLoad = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        // naturalWidth/Height guard rules out 0x0 "loaded" decoder errors.
        if (img.naturalWidth > 0 && img.naturalHeight > 0) {
          setPreviewProbing(false);
          setPreviewReady(true);
          setPreviewFailed(false);
        } else {
          onFail('zero_dimensions');
        }
      };

      const onFail = (reason) => {
        if (att < PREVIEW_PROBE_MAX_ATTEMPTS) {
          // Exponential backoff: 800ms, 1600ms, 3200ms, 6400ms.
          const delay = 800 * Math.pow(2, att - 1);
          setTimeout(attempt, delay);
          return;
        }
        // Exhausted retries → record false-success-prevented and
        // surface a safe message. Never expose share/download.
        setPreviewProbing(false);
        setPreviewReady(false);
        setPreviewFailed(true);
        _emitBeacon('reaction_gif_broken_preview_total', {
          reason,
          attempts: att,
        });
        _emitBeacon('reaction_gif_false_success_prevented_total', {
          reason,
          attempts: att,
        });
        toastErrorSafe(
          'Your reaction was created, but the media file is still being finalized. We are retrying — please hold on.',
          {
            requestId: lastRequestIdRef.current,
            code: 'REACTION_GIF_PREVIEW_NOT_READY',
            page: '/app/gif-maker',
            id: 'reaction-gif-preview-not-ready',
            duration: 8000,
          }
        );
      };

      img.onload = onLoad;
      img.onerror = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        onFail('image_error');
      };
      img.src = probeUrl;
    };

    attempt();
  // POLL constants/refs are stable; _emitBeacon is the only external dep.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_emitBeacon]);

  // ── Poll (P0 2026-05-22 — connection-loss resilient) ──
  // Bug-class elimination per /app/memory/ENGINEERING_DOCTRINE.md:
  //  • single transient poll failure is NOT terminal
  //  • backend job continues regardless of polling hiccups
  //  • after threshold the user gets a structured, request_id-carrying
  //    toast and polling keeps trying — never dead UX
  //  • recovery dismisses the lost-state toast automatically
  const pollJob = useCallback(async (jobId) => {
    try {
      const res = await api.get(`/api/reaction-gif/job/${jobId}`);
      // Successful poll — track request_id from middleware for support.
      lastRequestIdRef.current =
        res.headers?.['x-request-id'] ||
        res.headers?.['X-Request-Id'] ||
        lastRequestIdRef.current;

      // ─── Recovery branch: we were in a lost state and the network
      // came back. Dismiss the warning and emit a recovered metric.
      if (consecutiveFailRef.current >= POLL_FAIL_TOLERANCE && lostToastShownRef.current) {
        try { toast.dismiss('reaction-gif-connection-lost'); } catch (_) { /* noop */ }
        toast.success('Reconnected — picking up where we left off.', {
          id: 'reaction-gif-reconnected',
          duration: 3000,
        });
        _emitBeacon('reaction_gif_poll_recovered_total', {
          consecutive_fail: consecutiveFailRef.current,
        });
      }
      consecutiveFailRef.current = 0;
      lostToastShownRef.current = false;

      setJob(res.data);

      const status = res.data.status;
      const terminalSuccess = (status === 'COMPLETED' || status === 'PARTIAL_READY');
      const terminalFail = (status === 'FAILED');
      if (terminalSuccess || terminalFail) {
        if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
        setLoading(false);
        try { sessionStorage.removeItem('reaction_gif_active_job_id'); } catch (_) { /* noop */ }
        fetchInit();

        if (!completedRef.current.has(jobId)) {
          completedRef.current.add(jobId);
          if (terminalSuccess) {
            // ─── P0 2026-05-22 — Asset-readiness gate (false-success fix).
            // Do NOT trust the backend's COMPLETED status alone. The
            // canonical contract is `assetVerified === true` from the
            // backend AND an in-browser image preload probe must pass
            // before we expose share / download / copy-link.
            const backendVerified = res.data.assetVerified === true;
            const previewUrl = res.data.resultUrl;
            if (!backendVerified || !previewUrl) {
              _emitBeacon('reaction_gif_download_url_missing_total', {
                backend_verified: backendVerified,
                has_url: Boolean(previewUrl),
                status,
              });
              setPhase('upload');
              toastErrorSafe(
                'Your reaction was created, but the media file is still being finalized. Please try again in a moment.',
                {
                  requestId: lastRequestIdRef.current,
                  code: 'REACTION_GIF_ASSET_MISSING',
                  page: '/app/gif-maker',
                  id: 'reaction-gif-asset-missing',
                  duration: 7000,
                }
              );
              return;
            }
            setPhase('result');
            const msg = status === 'PARTIAL_READY'
              ? 'Part of your reaction pack is ready — others are still finishing.'
              : 'Your reaction is ready!';
            toast.success(msg);
            notifyGenerationComplete({
              feature: 'reaction_gif', featureName: 'Reaction GIF',
              jobId, downloadUrl: previewUrl,
              actionUrl: '/app/reaction-gif', showToast: false
            });
            refetchNotifications?.();
            // Kick off the browser-side preload probe. Share / download
            // remain hidden until the probe succeeds.
            previewProbeAttemptsRef.current = 0;
            setPreviewReady(false);
            setPreviewFailed(false);
            runPreviewProbe(previewUrl);
            setTimeout(() => setShowRating(true), 3000);
          } else {
            setPhase('upload');
            const err = res.data.error || 'Generation failed';
            const friendly = err.includes('budget')
              ? 'AI service temporarily unavailable. No credits deducted.'
              : 'Generation failed. No credits deducted.';
            toastErrorSafe(friendly, {
              requestId: lastRequestIdRef.current,
              code: 'REACTION_GIF_FAILED',
              page: '/app/gif-maker',
              id: 'reaction-gif-failed',
              duration: 6000,
            });
            notifyGenerationFailed({
              feature: 'reaction_gif', featureName: 'Reaction GIF',
              jobId, error: err, showToast: false
            });
          }
        }
      }
    } catch (err) {
      // Transient poll failure. The backend job is still running. We
      // ABSORB up to POLL_FAIL_TOLERANCE failures silently, then surface
      // a structured, request_id-carrying status — and keep polling so
      // the UI auto-recovers on reconnect. Never dead state, never
      // zombie interval.
      consecutiveFailRef.current += 1;
      const requestId = extractRequestId(err) || lastRequestIdRef.current;
      if (requestId) lastRequestIdRef.current = requestId;

      if (consecutiveFailRef.current === POLL_FAIL_TOLERANCE && !lostToastShownRef.current) {
        lostToastShownRef.current = true;
        toastErrorSafe(
          'Reaction generation was interrupted on your network. We are still checking the job status — your work is safe.',
          {
            requestId,
            code: 'REACTION_GIF_POLL_LOST',
            page: '/app/gif-maker',
            id: 'reaction-gif-connection-lost',
            duration: 8000,
          }
        );
        _emitBeacon('reaction_gif_connection_lost_total', {
          consecutive_fail: consecutiveFailRef.current,
          err_status: err?.response?.status || 0,
        });
      }

      // Hard ceiling. Backend may genuinely be unreachable for several
      // minutes; stop the interval but PRESERVE the job_id in session
      // storage so a refresh / online event can resume.
      if (consecutiveFailRef.current >= POLL_HARD_LIMIT) {
        if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
        setLoading(false);
        setPhase('upload');
        toastErrorSafe(
          'We could not reach the generation service. When you are back online, click Make My Reaction again and we will resume the same job.',
          {
            requestId: lastRequestIdRef.current,
            code: 'REACTION_GIF_POLL_GAVE_UP',
            page: '/app/gif-maker',
            id: 'reaction-gif-gave-up',
            duration: 10000,
          }
        );
      }
      // Otherwise: do nothing. The setInterval will fire again in 2s.
    }
  }, [notifyGenerationComplete, notifyGenerationFailed, refetchNotifications, _emitBeacon]);

  // ── Network recovery hooks ──
  // On `online` / window focus, fire an immediate extra poll so the UI
  // recovers instantly instead of waiting up to 2s for the interval.
  useEffect(() => {
    const forcePoll = () => {
      const jid = job?.id || (() => {
        try { return sessionStorage.getItem('reaction_gif_active_job_id'); } catch (_) { return null; }
      })();
      if (jid && pollingRef.current) {
        pollJob(jid);
      }
    };
    window.addEventListener('online', forcePoll);
    window.addEventListener('focus', forcePoll);
    return () => {
      window.removeEventListener('online', forcePoll);
      window.removeEventListener('focus', forcePoll);
    };
  }, [job?.id, pollJob]);

  // ── Quick generate another reaction ──
  const tryAnotherReaction = (reactionId) => {
    setSelectedReaction(reactionId);
    generate(reactionId, selectedStyle);
  };

  // ── Shuffle style and regenerate ──
  const tryRandomStyle = () => {
    const randomStyle = pickRandom(Object.keys(ALL_STYLES));
    setSelectedStyle(randomStyle);
    generate(selectedReaction, randomStyle);
  };

  // ── Download ──
  const resolveUrl = (url) => url?.startsWith('http') ? url : `${API_URL}${url}`;

  const downloadResult = async () => {
    if (!job?.id) {
      toast.error('Generated asset is not available yet. Please wait.');
      return;
    }
    // Backend gate: route the request through /download/:job_id so free
    // users cannot bypass the paywall by hitting the raw R2 URL.
    try {
      const dl = await api.post(`/api/reaction-gif/download/${job.id}`);
      const urls = dl.data?.downloadUrls || [];
      const target = urls[0] || job.resultUrl;
      if (!target) {
        toast.error('Generated asset is not available. Please try again.');
        return;
      }
      const url = resolveUrl(target);
      const resp = await fetch(url);
      const blob = await resp.blob();
      saveAs(blob, `reaction_${selectedReaction}_${job.id?.slice(0, 8)}.png`);
      toast.success('Downloaded!');
    } catch (e) {
      const status = e?.response?.status;
      if (status === 402 || status === 403) {
        setPaywall({ open: true, reason: 'download' });
        return;
      }
      if (status === 404) {
        toast.error('Generated asset is not available. Please try again.');
        return;
      }
      toast.error('Download failed. Please try again.');
    }
  };

  const downloadAllAsZip = async () => {
    if (!job?.results?.length) {
      toast.error('No assets available to download yet.');
      return;
    }
    // Verify access via the same backend gate before bulk download.
    try {
      await api.post(`/api/reaction-gif/download/${job.id}`);
    } catch (e) {
      const status = e?.response?.status;
      if (status === 402 || status === 403) {
        setPaywall({ open: true, reason: 'download' });
        return;
      }
    }
    setPackDownloading(true);
    try {
      const zip = new JSZip();
      await Promise.all(job.results.map(async (r, i) => {
        try {
          const resp = await fetch(resolveUrl(r.url));
          const blob = await resp.blob();
          zip.file(`reaction_${r.reaction || i + 1}.png`, blob);
        } catch {}
      }));
      const blob = await zip.generateAsync({ type: 'blob' });
      saveAs(blob, `reaction_pack_${job.id?.slice(0, 8)}.zip`);
      toast.success('Pack downloaded!');
    } catch { toast.error('Download failed. Please try again.'); }
    setPackDownloading(false);
  };

  // ── Share ──
  const getShareUrl = () => {
    if (!job?.resultUrl) return '';
    return resolveUrl(job.resultUrl);
  };

  const shareWhatsApp = () => {
    const url = getShareUrl();
    if (!url) {
      toast.error('Generated asset is not available yet. Please wait.');
      return;
    }
    const text = `Check out my AI reaction! Made on Visionary Suite`;
    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(text + ' ' + url)}`, '_blank');
  };

  const shareToStory = async () => {
    if (!job?.id) {
      toast.error('Generated asset is not available yet. Please wait.');
      return;
    }
    if (!canAccessFull) {
      setPaywall({ open: true, reason: 'share' });
      return;
    }
    // Prefer native Web Share with the file when supported (mobile).
    try {
      const dl = await api.post(`/api/reaction-gif/download/${job.id}`);
      const urls = dl.data?.downloadUrls || [];
      const target = urls[0] || job.resultUrl;
      if (!target) {
        toast.error('Generated asset is not available.');
        return;
      }
      const url = resolveUrl(target);
      const resp = await fetch(url);
      const blob = await resp.blob();
      const file = new File([blob], `reaction_${selectedReaction}.png`, { type: blob.type || 'image/png' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: 'My AI Reaction',
          text: 'Check out my AI reaction!',
        });
        return;
      }
      // Fallback — save the file so the user can attach it to their Story.
      saveAs(blob, `reaction_${selectedReaction}.png`);
      toast.success('Image downloaded — share it to your Story from your gallery.');
    } catch (e) {
      if (e?.name === 'AbortError') return; // user cancelled native share
      const status = e?.response?.status;
      if (status === 402 || status === 403) {
        setPaywall({ open: true, reason: 'share' });
        return;
      }
      toast.error('Could not share. Please try again.');
    }
  };

  const copyLink = async () => {
    if (!canAccessFull) {
      setPaywall({ open: true, reason: 'copy' });
      return;
    }
    const url = getShareUrl();
    if (!url) {
      toast.error('Generated asset is not available yet. Please wait.');
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Link copied!');
    } catch {
      toast.error('Could not copy link. Try again.');
    }
  };

  // ── Reset ──
  const startOver = () => {
    setPhase('upload');
    setJob(null);
    setSelectedReaction(pickRandom(AUTO_REACTIONS));
  };

  // ════════════════════════════════════════════
  // RENDER: Upload + Controls (single screen)
  // ════════════════════════════════════════════
  const renderUploadPhase = () => (
    <div className="max-w-5xl mx-auto" data-testid="upload-phase">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEFT: Upload + Quick select */}
        <div className="space-y-6">
          {/* Upload Zone */}
          <div
            className="relative border-2 border-dashed border-slate-600 rounded-2xl p-8 text-center hover:border-pink-500 transition-all cursor-pointer group"
            onClick={() => document.getElementById('photo-input').click()}
            data-testid="upload-zone"
          >
            {photoPreview ? (
              <div className="relative">
                <img src={photoPreview} alt="Preview" className="max-h-56 mx-auto rounded-xl shadow-lg" />
                <button
                  onClick={(e) => { e.stopPropagation(); clearPhoto(); }}
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white hover:bg-red-500 transition-colors"
                  data-testid="clear-photo-btn"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <Camera className="w-14 h-14 mx-auto text-slate-500 mb-3 group-hover:text-pink-400 transition-colors" />
                <p className="text-base text-slate-300 mb-1">Upload your photo</p>
                <p className="text-xs text-slate-500">PNG, JPG, WEBP up to 10MB</p>
              </>
            )}
          </div>
          <input
            id="photo-input" type="file" accept="image/*" className="hidden"
            onChange={handlePhotoUpload} data-testid="photo-input"
          />

          {/* Reaction Quick Select */}
          <div>
            <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wider">Reaction</p>
            <div className="flex flex-wrap gap-2" data-testid="reaction-selector">
              {REACTIONS.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelectedReaction(r.id)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                    selectedReaction === r.id
                      ? `bg-gradient-to-r ${r.color} text-white shadow-lg scale-105`
                      : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                  data-testid={`reaction-${r.id}`}
                >
                  <span className="text-lg">{r.emoji}</span>
                  <span className="hidden sm:inline">{r.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Style Pack Selector */}
          <div>
            <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wider">Style Pack</p>
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin" data-testid="pack-selector">
              {STYLE_PACKS.map((pack) => (
                <button
                  key={pack.id}
                  onClick={() => handlePackSelect(pack.id)}
                  className={`flex-shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                    selectedPack === pack.id
                      ? 'bg-pink-500/20 text-pink-300 border border-pink-500/40 shadow-lg shadow-pink-500/10'
                      : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700 border border-transparent'
                  }`}
                  data-testid={`pack-${pack.id}`}
                >
                  <span className="text-lg">{pack.emoji}</span>
                  {pack.name}
                </button>
              ))}
            </div>

            {/* Individual styles within pack */}
            <div className="flex gap-2 mt-2 flex-wrap">
              {STYLE_PACKS.find(p => p.id === selectedPack)?.styles.map((styleId) => (
                <button
                  key={styleId}
                  onClick={() => setSelectedStyle(styleId)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    selectedStyle === styleId
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'bg-slate-800/40 text-slate-500 hover:text-slate-300'
                  }`}
                  data-testid={`style-${styleId}`}
                >
                  {ALL_STYLES[styleId]}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT: Generate CTA */}
        <div className="flex flex-col justify-center items-center space-y-6">
          <div className="w-full bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
            {/* Hero text */}
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">
                {REACTIONS.find(r => r.id === selectedReaction)?.emoji} {REACTIONS.find(r => r.id === selectedReaction)?.name} Reaction
              </h2>
              <p className="text-sm text-slate-500">{ALL_STYLES[selectedStyle]} style</p>
            </div>

            {/* Cost */}
            <div className="py-3">
              {firstFree ? (
                <div className="space-y-1">
                  <span className="text-3xl font-black text-emerald-400">FREE</span>
                  <p className="text-xs text-emerald-500/80">Your first reaction is on us!</p>
                </div>
              ) : (
                <div className="space-y-1">
                  <span className="text-3xl font-black text-pink-400">8 <span className="text-base font-medium text-slate-400">credits</span></span>
                  <p className="text-xs text-slate-500">You have {credits.toLocaleString()} credits</p>
                </div>
              )}
            </div>

            {/* Generate Button */}
            <Button
              onClick={() => generate()}
              disabled={!photo || loading}
              className="w-full py-6 text-lg bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 shadow-xl shadow-pink-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
              data-testid="generate-btn"
            >
              {!photo ? (
                <><Upload className="w-5 h-5 mr-2" /> Upload photo to start</>
              ) : (
                <><Wand2 className="w-5 h-5 mr-2" /> Make My Reaction</>
              )}
            </Button>

            {!photo && (
              <p className="text-xs text-slate-600">Upload a clear face photo for best results</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  // ════════════════════════════════════════════
  // RENDER: Generating
  // ════════════════════════════════════════════
  const renderGenerating = () => {
    const msgs = [
      "Analyzing your face...",
      "Applying AI magic...",
      `Creating ${REACTIONS.find(r => r.id === selectedReaction)?.emoji} reaction...`,
      "Adding style effects...",
      "Almost there...",
    ];
    const msgIndex = Math.min(Math.floor((job?.progress || 0) / 25), msgs.length - 1);

    return (
      <div className="max-w-lg mx-auto text-center py-16" data-testid="generating-phase">
        <div className="relative mb-8">
          {photoPreview && (
            <img src={photoPreview} alt="" className="w-32 h-32 rounded-full mx-auto object-cover border-4 border-pink-500/30 shadow-2xl" />
          )}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-36 h-36 rounded-full border-4 border-pink-500/50 border-t-transparent animate-spin" />
          </div>
        </div>

        <h3 className="text-xl font-bold text-white mb-2">
          {msgs[msgIndex]}
        </h3>
        <p className="text-sm text-slate-400 mb-6">
          {job?.progress || 0}% complete
        </p>

        {/* Progress bar */}
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-gradient-to-r from-pink-500 to-purple-500 rounded-full transition-all duration-500"
            style={{ width: `${job?.progress || 5}%` }}
          />
        </div>

        <p className="text-xs text-slate-600">Usually takes 15-30 seconds</p>

        {/* P0 2026-05 — Waiting suggestions: keep users engaged while
            their reaction generates. Polling continues in the background. */}
        <div
          className="mt-10 text-left rounded-2xl border border-slate-800 bg-slate-900/40 p-5"
          data-testid="waiting-feature-panel"
        >
          <p className="text-sm text-slate-300 font-medium mb-1">
            Your Reaction GIF is being created.
          </p>
          <p className="text-xs text-slate-500 mb-4">
            While you wait, try Story Video, Photo to Comic, Comic Story Book or Bedtime Stories.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/app/story-video-studio')}
              className="border-slate-700 text-slate-300 hover:bg-slate-800 justify-start"
              data-testid="waiting-feature-story-video"
            >
              <Film className="w-3.5 h-3.5 mr-1.5" /> Story Video
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/app/photo-to-comic')}
              className="border-slate-700 text-slate-300 hover:bg-slate-800 justify-start"
              data-testid="waiting-feature-photo-to-comic"
            >
              <Palette className="w-3.5 h-3.5 mr-1.5" /> Photo to Comic
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/app/comic-storybook')}
              className="border-slate-700 text-slate-300 hover:bg-slate-800 justify-start"
              data-testid="waiting-feature-comic-storybook"
            >
              <BookOpen className="w-3.5 h-3.5 mr-1.5" /> Comic Story Book
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/app/bedtime-story-builder')}
              className="border-slate-700 text-slate-300 hover:bg-slate-800 justify-start"
              data-testid="waiting-feature-bedtime"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Bedtime Stories
            </Button>
          </div>
          <p className="text-[10px] text-slate-600 mt-3 text-center">
            We&apos;ll bring you back here as soon as your reaction is ready.
          </p>
        </div>
      </div>
    );
  };

  // ════════════════════════════════════════════
  // RENDER: Result — Addictive Loop
  // ════════════════════════════════════════════
  const renderResult = () => {
    if (!job || (job.status !== 'COMPLETED' && job.status !== 'PARTIAL_READY')) return null;
    const resultUrl = resolveUrl(job.resultUrl);
    // P0 2026-05-22 — Asset-readiness gate. Share / Download / Copy
    // actions render ONLY when the in-browser preload probe has
    // successfully decoded the asset. previewProbing means "in
    // flight, please wait"; previewFailed means "we gave up after
    // retries — show a safe retry CTA instead of dead UI".
    const showActions = previewReady;
    const showFinalizing = previewProbing && !previewReady && !previewFailed;
    const showRetry = previewFailed && !previewReady;
    const retryPreview = () => {
      previewProbeAttemptsRef.current = 0;
      setPreviewFailed(false);
      runPreviewProbe(job.resultUrl);
    };

    return (
      <div className="max-w-5xl mx-auto" data-testid="result-phase">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* LEFT: Result image */}
          <div className="space-y-4">
            <div
              className="rounded-2xl overflow-hidden border border-slate-700 bg-slate-900/60 shadow-2xl relative group select-none"
              data-testid="result-protected-wrapper"
              onContextMenu={canAccessFull ? undefined : (e) => { e.preventDefault(); setPaywall({ open: true, reason: 'copy' }); }}
              style={canAccessFull ? undefined : {
                userSelect: 'none',
                WebkitUserSelect: 'none',
                MozUserSelect: 'none',
                msUserSelect: 'none',
                WebkitTouchCallout: 'none',
              }}
            >
              <img
                src={resultUrl}
                alt="Your Reaction"
                className="w-full"
                data-testid="result-image"
                draggable={false}
                onDragStart={(e) => e.preventDefault()}
                onContextMenu={canAccessFull ? undefined : (e) => { e.preventDefault(); setPaywall({ open: true, reason: 'copy' }); }}
                style={{ pointerEvents: canAccessFull ? 'auto' : 'none', WebkitUserDrag: 'none' }}
              />
              {/* P0 2026-05-22 — Finalizing skeleton: covers the image
                  while the in-browser preload probe is still running so
                  users never see a broken-image flash. */}
              {showFinalizing && (
                <div
                  className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/85 backdrop-blur-sm"
                  data-testid="result-finalizing-overlay"
                >
                  <Loader2 className="w-8 h-8 text-pink-400 animate-spin mb-2" />
                  <p className="text-sm text-slate-200 text-center px-6">
                    Finalizing your reaction…
                  </p>
                  <p className="text-xs text-slate-400 text-center px-6 mt-1">
                    Verifying the preview before we hand it to you.
                  </p>
                </div>
              )}
              {/* P0 2026-05-22 — Retry CTA: shown when the preload
                  probe exhausted retries. NEVER expose share/download
                  in this state. */}
              {showRetry && (
                <div
                  className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/90 backdrop-blur-sm p-6"
                  data-testid="result-preview-retry"
                >
                  <AlertTriangle className="w-8 h-8 text-amber-400 mb-3" />
                  <p className="text-sm text-slate-100 text-center font-medium">
                    Preview is still finalizing
                  </p>
                  <p className="text-xs text-slate-400 text-center mt-1 mb-4">
                    Your reaction was created, but the media file is not ready yet.
                  </p>
                  <Button
                    onClick={retryPreview}
                    className="bg-pink-600 hover:bg-pink-500 text-white"
                    data-testid="result-preview-retry-btn"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" /> Retry preview
                  </Button>
                </div>
              )}
              {!canAccessFull && (
                <div className="pointer-events-none absolute inset-0 flex items-end justify-end p-2">
                  <span className="text-[10px] uppercase tracking-wider text-white/70 bg-black/40 backdrop-blur px-2 py-0.5 rounded">
                    Preview · Subscribe to download
                  </span>
                </div>
              )}
            </div>

            {/* Pack results grid */}
            {job.results?.length > 1 && (
              <div className="grid grid-cols-3 gap-2">
                {job.results.map((r, i) => (
                  <div key={i} className="rounded-lg overflow-hidden border border-slate-700 relative group cursor-pointer hover:border-pink-500 transition-colors">
                    <img src={resolveUrl(r.url)} alt={r.reaction} className="w-full" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <button
                        onClick={() => {
                          fetch(resolveUrl(r.url)).then(r => r.blob()).then(b => saveAs(b, `reaction_${r.reaction || i}.png`));
                        }}
                        className="p-2 rounded-full bg-white/20 text-white"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* RIGHT: Actions — Addictive Loop */}
          <div className="space-y-5">
            {/* P0 2026-05-22 — Asset-readiness gate.
                Share / Download / Copy NEVER render until the
                in-browser preload probe succeeds. While probing or
                after a probe failure, we show a safe placeholder so
                the user never lands on dead actions tied to a broken
                preview (the false-success bug class this gate
                eliminates). */}
            {!showActions && (
              <div
                className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 text-center"
                data-testid="result-actions-gated"
              >
                {showRetry ? (
                  <>
                    <AlertTriangle className="w-6 h-6 text-amber-400 mx-auto mb-2" />
                    <p className="text-sm text-slate-100 font-medium">
                      Sharing unlocks once the preview loads.
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Tap “Retry preview” on the image to try again.
                    </p>
                  </>
                ) : (
                  <>
                    <Loader2 className="w-6 h-6 text-pink-400 mx-auto animate-spin mb-2" />
                    <p className="text-sm text-slate-200">
                      Preparing share & download…
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      We verify the preview before exposing actions.
                    </p>
                  </>
                )}
              </div>
            )}

            {showActions && (
            <>
            {/* Share-First Cluster (PRIMARY) */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5" data-testid="share-section">
              <p className="text-xs text-slate-400 mb-3 font-medium uppercase tracking-wider">Share your reaction</p>
              <div className="space-y-2">
                <Button
                  onClick={shareWhatsApp}
                  className="w-full py-4 bg-[#25D366] hover:bg-[#20BD5A] text-white text-base font-semibold"
                  data-testid="share-whatsapp"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                  Share via Message
                </Button>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={shareToStory}
                    variant="outline"
                    className="py-3 text-slate-300 border-slate-700 hover:bg-slate-800"
                    data-testid="share-instagram"
                  >
                    <ExternalLink className="w-4 h-4 mr-1.5" /> Share to Story
                  </Button>
                  <Button
                    onClick={copyLink}
                    variant="outline"
                    className="py-3 text-slate-300 border-slate-700 hover:bg-slate-800"
                    data-testid="copy-link"
                  >
                    <Copy className="w-4 h-4 mr-1.5" /> Copy Link
                  </Button>
                </div>
              </div>
            </div>

            {/* Download */}
            <div className="flex gap-2">
              <Button
                onClick={downloadResult}
                className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white border border-slate-700"
                data-testid="download-btn"
              >
                <Download className="w-4 h-4 mr-1.5" /> Download
              </Button>
              {job.results?.length > 1 && (
                <Button
                  onClick={downloadAllAsZip}
                  disabled={packDownloading}
                  className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white border border-slate-700"
                  data-testid="download-pack-btn"
                >
                  {packDownloading ? <Loader2 className="w-4 h-4 animate-spin mr-1.5" /> : <PackageOpen className="w-4 h-4 mr-1.5" />}
                  Download Pack
                </Button>
              )}
            </div>
            </>
            )}
            {/* End of asset-readiness gate (P0 2026-05-22) */}

            {/* ── ADDICTIVE LOOP ── */}
            <div className="bg-gradient-to-r from-pink-500/10 to-purple-500/10 border border-pink-500/20 rounded-2xl p-5" data-testid="loop-section">
              <p className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-pink-400" /> Try another reaction
              </p>
              <div className="flex flex-wrap gap-2 mb-4">
                {REACTIONS.filter(r => r.id !== selectedReaction).slice(0, 5).map((r) => (
                  <button
                    key={r.id}
                    onClick={() => tryAnotherReaction(r.id)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800/60 text-slate-300 hover:bg-pink-500/20 hover:text-pink-300 transition-all text-sm"
                    data-testid={`try-reaction-${r.id}`}
                  >
                    <span className="text-lg">{r.emoji}</span> {r.name}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={tryRandomStyle}
                  variant="outline"
                  className="py-3 text-slate-300 border-slate-700 hover:bg-slate-800 text-sm"
                  data-testid="try-random-style"
                >
                  <RefreshCw className="w-4 h-4 mr-1.5" /> Random Style
                </Button>
                <Button
                  onClick={startOver}
                  variant="outline"
                  className="py-3 text-slate-300 border-slate-700 hover:bg-slate-800 text-sm"
                  data-testid="start-over"
                >
                  <Camera className="w-4 h-4 mr-1.5" /> New Photo
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ════════════════════════════════════════════
  // MAIN RENDER
  // ════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/50 to-slate-950" data-testid="reaction-gif-page">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link to="/app" className="flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors text-sm" data-testid="back-link">
                <ArrowLeft className="w-4 h-4" /> Dashboard
              </Link>
              <div className="hidden sm:flex items-center gap-2">
                <Smile className="w-5 h-5 text-pink-400" />
                <h1 className="text-lg font-bold text-white">Reaction GIF Creator</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {firstFree && phase === 'upload' && (
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full font-medium animate-pulse" data-testid="first-free-badge">
                  First one FREE
                </span>
              )}
              <div className="bg-pink-500/10 border border-pink-500/20 rounded-full px-3 py-1.5">
                <span className="text-pink-300 text-sm font-medium">{credits.toLocaleString()} cr</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Hero (only on upload phase) */}
      {phase === 'upload' && (
        <div className="text-center py-8 max-w-2xl mx-auto px-4">
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-2" data-testid="hero-title">
            Your face. Infinite reactions.
          </h2>
          <p className="text-base text-slate-400">
            Upload once, create viral reactions in any style
          </p>
        </div>
      )}

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-4">
        {phase === 'upload' && renderUploadPhase()}
        {phase === 'generating' && renderGenerating()}
        {phase === 'result' && renderResult()}
      </main>

      {/* Legal */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-slate-800/20 rounded-xl p-3 border border-slate-800 flex items-center gap-2">
          <Shield className="w-4 h-4 text-pink-400/60 flex-shrink-0" />
          <p className="text-[10px] text-slate-500">
            Upload only images you own. Brand-based or copyrighted content is not allowed.
          </p>
        </div>
      </div>

      {/* Modals */}
      <RatingModal
        isOpen={showRating}
        onClose={() => setShowRating(false)}
        featureKey="reaction_gif"
        relatedRequestId={job?.id}
        onSubmitSuccess={() => setShowRating(false)}
      />
      {showUpsell && (
        <UpsellModal
          isOpen={showUpsell}
          credits={0}
          onClose={() => setShowUpsell(false)}
        />
      )}

      {/* P0 2026-05 — Subscription paywall for Download / Share to Story / Copy */}
      <BedtimePaywallModal
        open={paywall.open}
        reason={paywall.reason}
        onClose={() => setPaywall({ open: false, reason: null })}
      />
    </div>
  );
}
