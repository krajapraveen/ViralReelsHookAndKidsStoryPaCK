import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
  Film, Download, Loader2, AlertCircle, CheckCircle,
  Monitor, Smartphone, X
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

let ffmpegInstance = null;

async function getFFmpeg() {
  if (ffmpegInstance?.loaded) return ffmpegInstance;
  const { FFmpeg } = await import('@ffmpeg/ffmpeg');
  ffmpegInstance = new FFmpeg();
  return ffmpegInstance;
}

// Proxy R2 URLs through backend to bypass CORS restrictions
function proxyUrl(url) {
  if (!url) return url;
  // Only proxy cross-origin R2 URLs
  if (url.includes('r2.cloudflarestorage.com') || url.includes('r2.dev')) {
    return `${API_URL}/api/pipeline/asset-proxy?url=${encodeURIComponent(url)}`;
  }
  return url;
}

// Draw watermark branding on canvas
function drawWatermark(ctx, W, H) {
  const text = 'Created with Visionary Suite AI  |  visionary-suite.com';
  ctx.save();
  ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
  ctx.font = '12px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  // Semi-transparent bar at bottom
  ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
  ctx.fillRect(0, H - 28, W, 28);
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
  ctx.fillText(text, W / 2, H - 8);
  ctx.restore();
}

function detectExportMode() {
  const hasMediaRecorder = typeof MediaRecorder !== 'undefined';
  const canWebM = hasMediaRecorder && MediaRecorder.isTypeSupported?.('video/webm;codecs=vp8,opus');
  const hasSAB = typeof SharedArrayBuffer !== 'undefined';
  const isIsolated = typeof window !== 'undefined' && window.crossOriginIsolated === true;
  const hasWasm = typeof WebAssembly !== 'undefined';

  if ((hasSAB || isIsolated) && hasWasm) {
    return { mode: 'ffmpeg', label: 'MP4 Export', format: 'mp4' };
  }
  if (canWebM) {
    return { mode: 'mediarecorder', label: 'WebM Export', format: 'webm' };
  }
  return { mode: 'none', label: 'Export unavailable', reason: 'Browser does not support video export. Use Chrome or Firefox for best results.' };
}

// Fetch image as blob URL via backend proxy to avoid CORS issues
async function loadImageAsBlob(url) {
  const proxied = proxyUrl(url);
  const res = await fetch(proxied);
  if (!res.ok) throw new Error(`Image fetch failed (${res.status}): ${url.substring(0, 60)}`);
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ img, blobUrl });
    img.onerror = () => reject(new Error(`Image decode failed: ${url.substring(0, 60)}`));
    img.src = blobUrl;
  });
}

// Fetch audio as ArrayBuffer via backend proxy and decode for AudioContext
async function loadAudioBuffer(url, audioCtx) {
  const proxied = proxyUrl(url);
  const res = await fetch(proxied);
  if (!res.ok) throw new Error(`Audio fetch failed (${res.status})`);
  const arrayBuf = await res.arrayBuffer();
  const audioBuf = await audioCtx.decodeAudioData(arrayBuf);
  return audioBuf;
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

export default function BrowserVideoExport({ scenes, title, jobId, onClose }) {
  const [phase, setPhase] = useState('ready');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoBlob, setVideoBlob] = useState(null);
  const [renderTime, setRenderTime] = useState(0);
  const [exportMode, setExportMode] = useState(null);
  const [debugLog, setDebugLog] = useState([]);
  const ffmpegRef = useRef(null);
  const abortRef = useRef(false);

  useEffect(() => { setExportMode(detectExportMode()); }, []);

  const log = useCallback((msg) => {
    console.log(`[BrowserExport] ${msg}`);
    setDebugLog(prev => [...prev.slice(-19), msg]);
  }, []);

  // ─── FFmpeg.wasm MP4 Export ─────────────────────────────────────────────
  const exportWithFFmpeg = useCallback(async () => {
    const { fetchFile } = await import('@ffmpeg/util');
    const startTime = Date.now();

    setPhase('loading');
    setMessage('Loading video encoder...');
    setProgress(5);
    log('Loading ffmpeg.wasm...');

    const ffmpeg = await getFFmpeg();
    ffmpegRef.current = ffmpeg;

    if (!ffmpeg.loaded) {
      ffmpeg.on('progress', ({ progress: p }) => {
        setProgress(Math.min(40 + Math.round(p * 55), 95));
      });
      // Load from same-origin public directory to avoid CORS/COEP Worker import issues
      const baseURL = window.location.origin + '/ffmpeg-core';
      log(`Loading ffmpeg core from: ${baseURL}`);
      await ffmpeg.load({
        coreURL: `${baseURL}/ffmpeg-core.js`,
        wasmURL: `${baseURL}/ffmpeg-core.wasm`,
      });
    }

    if (abortRef.current) return;
    setProgress(15);
    log('ffmpeg loaded');

    const validScenes = scenes.filter(s => s.image_url);
    if (!validScenes.length) throw new Error('No scene images available');

    setPhase('downloading');
    setMessage('Downloading scene assets...');

    // Download images via backend proxy to avoid CORS
    for (let i = 0; i < validScenes.length; i++) {
      if (abortRef.current) return;
      setMessage(`Downloading image ${i + 1}/${validScenes.length}...`);
      setProgress(15 + Math.round((i / validScenes.length) * 15));
      const imgData = await fetchFile(proxyUrl(validScenes[i].image_url));
      await ffmpeg.writeFile(`img_${i}.png`, imgData);
      log(`Image ${i + 1} downloaded (${imgData.length} bytes)`);
    }

    const audioScenes = validScenes.filter(s => s.audio_url);
    for (let i = 0; i < audioScenes.length; i++) {
      if (abortRef.current) return;
      setMessage(`Downloading audio ${i + 1}/${audioScenes.length}...`);
      setProgress(30 + Math.round((i / audioScenes.length) * 10));
      const audioData = await fetchFile(proxyUrl(audioScenes[i].audio_url));
      await ffmpeg.writeFile(`audio_${i}.mp3`, audioData);
      log(`Audio ${i + 1} downloaded (${audioData.length} bytes)`);
    }

    if (abortRef.current) return;

    setPhase('rendering');
    setMessage('Rendering video...');
    setProgress(40);

    const W = 1280, H = 720, FPS = 15;
    const concatLines = [];

    for (let i = 0; i < validScenes.length; i++) {
      const scene = validScenes[i];
      const dur = scene.duration || 5;
      const audioIdx = audioScenes.indexOf(scene);

      if (audioIdx >= 0) {
        const ret1 = await ffmpeg.exec([
          '-loop', '1', '-i', `img_${i}.png`,
          '-i', `audio_${audioIdx}.mp3`,
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
          '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}`,
          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
          '-shortest', '-movflags', '+faststart', `segment_${i}.mp4`
        ]);
        if (ret1 !== 0) log(`Warning: segment ${i} with audio exited with code ${ret1}`);
      } else {
        const ret2 = await ffmpeg.exec([
          '-loop', '1', '-t', `${dur}`, '-i', `img_${i}.png`,
          '-f', 'lavfi', '-t', `${dur}`, '-i', 'anullsrc=r=44100:cl=stereo',
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
          '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}`,
          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest',
          '-movflags', '+faststart', `segment_${i}.mp4`
        ]);
        if (ret2 !== 0) log(`Warning: segment ${i} without audio exited with code ${ret2}`);
      }

      concatLines.push(`file 'segment_${i}.mp4'`);
      setProgress(40 + Math.round(((i + 1) / validScenes.length) * 45));
      setMessage(`Rendering scene ${i + 1}/${validScenes.length}...`);
      log(`Scene ${i + 1} rendered`);
    }

    setMessage('Assembling final video...');
    setProgress(90);

    await ffmpeg.writeFile('concat.txt', concatLines.join('\n'));
    const concatRet = await ffmpeg.exec(['-f', 'concat', '-safe', '0', '-i', 'concat.txt', '-c', 'copy', '-movflags', '+faststart', 'output.mp4']);
    if (concatRet !== 0) log(`Warning: concat exited with code ${concatRet}`);

    const data = await ffmpeg.readFile('output.mp4');
    const blob = new Blob([data.buffer], { type: 'video/mp4' });

    log(`Final MP4: ${(blob.size / 1024 / 1024).toFixed(2)}MB`);

    if (blob.size < 1024) {
      throw new Error(`Export produced empty video (${blob.size} bytes). Please retry.`);
    }

    // Cleanup
    for (let i = 0; i < validScenes.length; i++) {
      try { await ffmpeg.deleteFile(`img_${i}.png`); } catch {}
      try { await ffmpeg.deleteFile(`segment_${i}.mp4`); } catch {}
      try { await ffmpeg.deleteFile(`audio_${i}.mp3`); } catch {}
    }
    try { await ffmpeg.deleteFile('concat.txt'); } catch {}
    try { await ffmpeg.deleteFile('output.mp4'); } catch {}

    return { url: URL.createObjectURL(blob), blob, time: Math.round((Date.now() - startTime) / 1000), format: 'mp4' };
  }, [scenes, log]);

  // ─── MediaRecorder WebM Export (frame-accurate) ─────────────────────────
  const exportWithMediaRecorder = useCallback(async () => {
    const startTime = Date.now();
    const validScenes = scenes.filter(s => s.image_url);
    if (!validScenes.length) throw new Error('No scene images available');

    // Step 1: Preload ALL assets before recording
    setPhase('downloading');
    setMessage('Preloading images...');
    setProgress(5);
    log(`Preloading ${validScenes.length} scenes...`);

    const loadedImages = [];
    const blobUrls = [];
    for (let i = 0; i < validScenes.length; i++) {
      if (abortRef.current) return;
      setMessage(`Loading image ${i + 1}/${validScenes.length}...`);
      setProgress(5 + Math.round((i / validScenes.length) * 15));
      try {
        const { img, blobUrl } = await loadImageAsBlob(validScenes[i].image_url);
        loadedImages.push(img);
        blobUrls.push(blobUrl);
        log(`Image ${i + 1}: ${img.naturalWidth}x${img.naturalHeight} loaded`);
      } catch (err) {
        log(`Image ${i + 1} failed: ${err.message}`);
        loadedImages.push(null);
        blobUrls.push(null);
      }
    }

    // Step 2: Create canvas
    const W = 960, H = 540;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    // Draw first frame immediately to ensure stream has content
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, W, H);
    if (loadedImages[0] && loadedImages[0].naturalWidth > 0) {
      const img = loadedImages[0];
      const scale = Math.min(W / img.naturalWidth, H / img.naturalHeight);
      const sw = img.naturalWidth * scale;
      const sh = img.naturalHeight * scale;
      ctx.drawImage(img, (W - sw) / 2, (H - sh) / 2, sw, sh);
    }
    log('First frame drawn to canvas');

    // Step 3: Preload audio buffers
    setMessage('Preloading audio...');
    setProgress(25);

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
    const dest = audioCtx.createMediaStreamDestination();

    const audioBuffers = [];
    for (let i = 0; i < validScenes.length; i++) {
      if (validScenes[i].audio_url) {
        try {
          const buf = await loadAudioBuffer(validScenes[i].audio_url, audioCtx);
          audioBuffers.push(buf);
          log(`Audio ${i + 1}: ${buf.duration.toFixed(1)}s loaded`);
        } catch (err) {
          log(`Audio ${i + 1} failed: ${err.message}`);
          audioBuffers.push(null);
        }
      } else {
        audioBuffers.push(null);
      }
    }

    if (abortRef.current) { audioCtx.close(); return; }

    // Step 4: Capture canvas stream + audio destination
    const videoStream = canvas.captureStream(15);
    const combinedStream = new MediaStream([
      ...videoStream.getVideoTracks(),
      ...dest.stream.getAudioTracks(),
    ]);
    log(`Stream: ${combinedStream.getVideoTracks().length} video, ${combinedStream.getAudioTracks().length} audio tracks`);

    // Step 5: Start MediaRecorder
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
      ? 'video/webm;codecs=vp8,opus'
      : 'video/webm';
    const recorder = new MediaRecorder(combinedStream, { mimeType, videoBitsPerSecond: 2500000 });

    const chunks = [];
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };

    const recordingDone = new Promise(resolve => { recorder.onstop = resolve; });
    recorder.start(200); // Collect data every 200ms
    log('MediaRecorder started');

    // Wait a tick so recorder captures the first frame
    await sleep(100);

    // Step 6: Render each scene while recording
    setPhase('rendering');
    let framesRendered = 0;

    for (let i = 0; i < validScenes.length; i++) {
      if (abortRef.current) { recorder.stop(); audioCtx.close(); return; }

      const sceneDur = validScenes[i].duration || 5;
      setMessage(`Recording scene ${i + 1}/${validScenes.length}...`);
      setProgress(30 + Math.round(((i + 1) / validScenes.length) * 60));
      log(`Scene ${i + 1}: drawing for ${sceneDur}s`);

      // Draw image to canvas
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, W, H);
      const img = loadedImages[i];
      if (img && img.naturalWidth > 0) {
        const scale = Math.min(W / img.naturalWidth, H / img.naturalHeight);
        const sw = img.naturalWidth * scale;
        const sh = img.naturalHeight * scale;
        ctx.drawImage(img, (W - sw) / 2, (H - sh) / 2, sw, sh);
        drawWatermark(ctx, W, H);
        framesRendered++;
      } else {
        // Draw placeholder with scene number
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = '#ffffff';
        ctx.font = '32px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`Scene ${i + 1}`, W / 2, H / 2);
        framesRendered++;
      }

      // Play audio for this scene
      let audioSource = null;
      if (audioBuffers[i]) {
        audioSource = audioCtx.createBufferSource();
        audioSource.buffer = audioBuffers[i];
        audioSource.connect(dest);
        audioSource.start(0);
      }

      // Keep canvas alive during scene — full redraw at 15fps to ensure frames captured
      const frameInterval = 1000 / 15;
      const sceneEnd = Date.now() + (sceneDur * 1000);
      let tick = 0;
      while (Date.now() < sceneEnd) {
        if (abortRef.current) break;
        tick++;
        // Full redraw each frame to guarantee captureStream emits data
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, W, H);
        if (img && img.naturalWidth > 0) {
          const sc = Math.min(W / img.naturalWidth, H / img.naturalHeight);
          const sw2 = img.naturalWidth * sc;
          const sh2 = img.naturalHeight * sc;
          ctx.drawImage(img, (W - sw2) / 2, (H - sh2) / 2, sw2, sh2);
        } else {
          ctx.fillStyle = '#1a1a2e';
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = '#ffffff';
          ctx.font = '32px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(`Scene ${i + 1}`, W / 2, H / 2);
        }
        drawWatermark(ctx, W, H);
        await sleep(frameInterval);
      }

      // Stop audio source for this scene
      if (audioSource) {
        try { audioSource.stop(); } catch {}
      }

      log(`Scene ${i + 1} recorded (${framesRendered} frames total)`);
    }

    // Step 7: Stop recording and create blob
    setMessage('Finalizing video...');
    setProgress(92);
    recorder.stop();
    await recordingDone;
    audioCtx.close();

    // Cleanup blob URLs
    blobUrls.forEach(u => { if (u) URL.revokeObjectURL(u); });

    log(`Recording done: ${chunks.length} chunks, ${framesRendered} frames`);

    // Verify we actually recorded something
    if (chunks.length === 0) {
      throw new Error('No video frames were recorded. Try using Chrome or Firefox.');
    }

    const blob = new Blob(chunks, { type: mimeType });
    const sizeMB = (blob.size / 1024 / 1024).toFixed(2);
    log(`Final WebM: ${sizeMB}MB, ${chunks.length} chunks`);

    if (blob.size < 1024) {
      throw new Error(`Export produced empty video (${blob.size} bytes). Please retry or download Story Pack.`);
    }

    return { url: URL.createObjectURL(blob), blob, time: Math.round((Date.now() - startTime) / 1000), format: 'webm' };
  }, [scenes, log]);

  // ─── Main export handler ──────────────────────────────────────────────────
  const startExport = useCallback(async () => {
    abortRef.current = false;
    setDebugLog([]);
    try {
      let result;
      if (exportMode?.mode === 'ffmpeg') {
        result = await exportWithFFmpeg();
      } else if (exportMode?.mode === 'mediarecorder') {
        result = await exportWithMediaRecorder();
      }

      if (!result || abortRef.current) return;

      setVideoUrl(result.url);
      setVideoBlob(result.blob);
      setRenderTime(result.time);
      setPhase('done');
      setProgress(100);
      setMessage(`${result.format.toUpperCase()} ready!`);
      toast.success(`Video exported! (${result.format.toUpperCase()}, ${(result.blob.size / 1024 / 1024).toFixed(1)}MB)`);
    } catch (err) {
      console.error('Export failed:', err);

      // If FFmpeg failed, try MediaRecorder fallback
      if (exportMode?.mode === 'ffmpeg') {
        const canFallback = typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported?.('video/webm;codecs=vp8,opus');
        if (canFallback) {
          toast.info('MP4 export failed — trying WebM fallback...');
          try {
            const result = await exportWithMediaRecorder();
            if (result && !abortRef.current) {
              setVideoUrl(result.url);
              setVideoBlob(result.blob);
              setRenderTime(result.time);
              setPhase('done');
              setProgress(100);
              setMessage('WebM ready (fallback)!');
              toast.success(`Video exported as WebM! (${(result.blob.size / 1024 / 1024).toFixed(1)}MB)`);
              return;
            }
          } catch (fallbackErr) {
            console.error('WebM fallback also failed:', fallbackErr);
          }
        }
      }

      setPhase('error');
      setMessage(err.message || 'Export failed');
      toast.error('Video export failed. Try downloading the Story Pack instead.');
    }
  }, [exportMode, exportWithFFmpeg, exportWithMediaRecorder]);

  const downloadVideo = () => {
    if (!videoUrl || !videoBlob) return;
    const ext = videoBlob.type.includes('webm') ? 'webm' : 'mp4';
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = `${title || 'story'}_${jobId?.slice(0, 8) || 'video'}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const abort = () => {
    abortRef.current = true;
    setPhase('ready');
    setProgress(0);
    setMessage('');
  };

  if (exportMode && exportMode.mode === 'none') {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="browser-export-unsupported">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-white font-semibold">Browser Export Not Available</h3>
            <p className="text-slate-400 text-sm mt-1">{exportMode.reason}</p>
            <p className="text-slate-400 text-sm mt-2">
              Download the <strong className="text-teal-400">Story Pack</strong> or use the <strong className="text-emerald-400">Instant Preview</strong> instead.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const formatLabel = videoBlob
    ? (videoBlob.type.includes('webm') ? 'WebM' : 'MP4')
    : (exportMode?.mode === 'ffmpeg' ? 'MP4' : 'WebM');
  const doneSize = videoBlob ? (videoBlob.size / (1024 * 1024)).toFixed(1) : '0';

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="browser-video-export">
      <div className="px-5 py-4 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
            phase === 'done' ? 'bg-emerald-500/20' : phase === 'error' ? 'bg-red-500/20' : 'bg-purple-500/20'
          }`}>
            {phase === 'done' ? <CheckCircle className="w-5 h-5 text-emerald-400" />
              : phase === 'error' ? <AlertCircle className="w-5 h-5 text-red-400" />
              : <Film className="w-5 h-5 text-purple-400" />}
          </div>
          <div>
            <h3 className="text-white font-semibold text-sm">Export {formatLabel} in Browser</h3>
            <p className="text-xs text-slate-400">
              {phase === 'done'
                ? `Rendered in ${renderTime}s — ${doneSize}MB`
                : exportMode?.mode === 'ffmpeg'
                  ? 'High-quality MP4 — rendered in your browser, no server needed'
                  : 'WebM video — rendered in your browser, no server needed'}
            </p>
          </div>
        </div>
        {onClose && <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400"><X className="w-4 h-4" /></Button>}
      </div>

      <div className="p-5 space-y-4">
        {phase === 'ready' && (
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-4 text-sm text-slate-400">
              <span className="flex items-center gap-1"><Monitor className="w-4 h-4" /> {exportMode?.mode === 'ffmpeg' ? '720p' : '540p'}</span>
              <span className="flex items-center gap-1"><Film className="w-4 h-4" /> {formatLabel}</span>
              <span className="flex items-center gap-1"><Smartphone className="w-4 h-4" /> {scenes.length} scenes</span>
            </div>
            {exportMode?.mode === 'mediarecorder' && (
              <p className="text-xs text-amber-400/80 bg-amber-500/10 rounded-lg px-3 py-2">
                Your browser will record the video as WebM. Plays in all modern browsers and devices.
              </p>
            )}
            <Button onClick={startExport} className="bg-purple-600 hover:bg-purple-700 px-8" data-testid="start-export-btn">
              <Film className="w-4 h-4 mr-2" /> Export {formatLabel} Video
            </Button>
          </div>
        )}

        {['loading', 'downloading', 'rendering'].includes(phase) && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-white font-medium flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-purple-400" /> {message}
              </span>
              <span className="text-slate-400">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
            <Button variant="outline" size="sm" onClick={abort} className="text-slate-400 border-slate-700">Cancel</Button>
          </div>
        )}

        {phase === 'done' && videoUrl && (
          <div className="space-y-4">
            <video src={videoUrl} controls className="w-full rounded-lg bg-black aspect-video" data-testid="exported-video-player" />
            <div className="flex items-center gap-3">
              <Button onClick={downloadVideo} className="bg-emerald-600 hover:bg-emerald-700 flex-1" data-testid="download-exported-video">
                <Download className="w-4 h-4 mr-2" /> Download {formatLabel} ({doneSize}MB)
              </Button>
              <Button onClick={() => { setPhase('ready'); setVideoUrl(null); setVideoBlob(null); setDebugLog([]); }} variant="outline" className="border-slate-700 text-slate-300">
                Re-export
              </Button>
            </div>
          </div>
        )}

        {phase === 'error' && (
          <div className="text-center space-y-3">
            <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
            <p className="text-red-400 text-sm">{message}</p>
            <div className="flex items-center justify-center gap-3">
              <Button onClick={startExport} className="bg-purple-600 hover:bg-purple-700" data-testid="retry-export-btn">
                Retry Export
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              If export keeps failing, download the <strong>Story Pack</strong> instead.
            </p>
          </div>
        )}

        {/* Debug log — visible during export and on error */}
        {debugLog.length > 0 && ['rendering', 'downloading', 'error', 'done'].includes(phase) && (
          <details className="text-xs">
            <summary className="text-slate-500 cursor-pointer hover:text-slate-400">Export log ({debugLog.length} entries)</summary>
            <div className="mt-2 bg-slate-900/50 rounded-lg p-3 max-h-32 overflow-y-auto font-mono text-slate-500 space-y-0.5">
              {debugLog.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
