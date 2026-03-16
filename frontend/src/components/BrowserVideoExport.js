import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
  Film, Download, Loader2, AlertCircle, CheckCircle,
  Monitor, Smartphone, X
} from 'lucide-react';
import { toast } from 'sonner';

let ffmpegInstance = null;

async function getFFmpeg() {
  if (ffmpegInstance?.loaded) return ffmpegInstance;
  const { FFmpeg } = await import('@ffmpeg/ffmpeg');
  ffmpegInstance = new FFmpeg();
  return ffmpegInstance;
}

// Detect export capabilities
function detectExportMode() {
  const hasSAB = typeof SharedArrayBuffer !== 'undefined';
  const isIsolated = typeof window !== 'undefined' && window.crossOriginIsolated === true;
  const hasWasm = typeof WebAssembly !== 'undefined';
  const hasMediaRecorder = typeof MediaRecorder !== 'undefined';
  const canWebM = hasMediaRecorder && MediaRecorder.isTypeSupported?.('video/webm;codecs=vp8,opus');

  if ((hasSAB || isIsolated) && hasWasm) {
    return { mode: 'ffmpeg', label: 'MP4 Export', format: 'mp4' };
  }
  if (canWebM) {
    return { mode: 'mediarecorder', label: 'WebM Export', format: 'webm' };
  }
  return { mode: 'none', label: 'Export unavailable', reason: 'Browser does not support video export. Use Chrome or Firefox for best results.' };
}

export default function BrowserVideoExport({ scenes, title, jobId, onClose }) {
  const [phase, setPhase] = useState('ready');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoBlob, setVideoBlob] = useState(null);
  const [renderTime, setRenderTime] = useState(0);
  const [exportMode, setExportMode] = useState(null);
  const ffmpegRef = useRef(null);
  const abortRef = useRef(false);
  const canvasRef = useRef(null);

  useEffect(() => {
    setExportMode(detectExportMode());
  }, []);

  // ─── FFmpeg.wasm MP4 Export ─────────────────────────────────────────────────
  const exportWithFFmpeg = useCallback(async () => {
    const { toBlobURL, fetchFile } = await import('@ffmpeg/util');
    const startTime = Date.now();

    setPhase('loading');
    setMessage('Loading video encoder...');
    setProgress(5);

    const ffmpeg = await getFFmpeg();
    ffmpegRef.current = ffmpeg;

    if (!ffmpeg.loaded) {
      ffmpeg.on('progress', ({ progress: p }) => {
        setProgress(Math.min(40 + Math.round(p * 55), 95));
      });
      const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm';
      await ffmpeg.load({
        coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
        wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
      });
    }

    if (abortRef.current) return;
    setProgress(15);

    const validScenes = scenes.filter(s => s.image_url);
    if (!validScenes.length) throw new Error('No scene images available');

    setPhase('downloading');
    setMessage('Downloading scene assets...');

    for (let i = 0; i < validScenes.length; i++) {
      if (abortRef.current) return;
      setMessage(`Downloading image ${i + 1}/${validScenes.length}...`);
      setProgress(15 + Math.round((i / validScenes.length) * 15));
      try {
        const imgData = await fetchFile(validScenes[i].image_url);
        await ffmpeg.writeFile(`img_${i}.png`, imgData);
      } catch (err) { console.warn(`Image ${i} download failed:`, err); }
    }

    const audioScenes = validScenes.filter(s => s.audio_url);
    for (let i = 0; i < audioScenes.length; i++) {
      if (abortRef.current) return;
      setMessage(`Downloading audio ${i + 1}/${audioScenes.length}...`);
      setProgress(30 + Math.round((i / audioScenes.length) * 10));
      try {
        const audioData = await fetchFile(audioScenes[i].audio_url);
        await ffmpeg.writeFile(`audio_${i}.mp3`, audioData);
      } catch (err) { console.warn(`Audio ${i} download failed:`, err); }
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
        await ffmpeg.exec([
          '-loop', '1', '-i', `img_${i}.png`,
          '-i', `audio_${audioIdx}.mp3`,
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
          '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}`,
          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
          '-shortest', '-movflags', '+faststart', `segment_${i}.mp4`
        ]);
      } else {
        await ffmpeg.exec([
          '-loop', '1', '-t', `${dur}`, '-i', `img_${i}.png`,
          '-f', 'lavfi', '-t', `${dur}`, '-i', 'anullsrc=r=44100:cl=stereo',
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
          '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}`,
          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest',
          '-movflags', '+faststart', `segment_${i}.mp4`
        ]);
      }

      concatLines.push(`file 'segment_${i}.mp4'`);
      setProgress(40 + Math.round(((i + 1) / validScenes.length) * 45));
      setMessage(`Rendering scene ${i + 1}/${validScenes.length}...`);
    }

    setMessage('Assembling final video...');
    setProgress(90);

    await ffmpeg.writeFile('concat.txt', concatLines.join('\n'));
    await ffmpeg.exec(['-f', 'concat', '-safe', '0', '-i', 'concat.txt', '-c', 'copy', '-movflags', '+faststart', 'output.mp4']);

    const data = await ffmpeg.readFile('output.mp4');
    const blob = new Blob([data.buffer], { type: 'video/mp4' });
    const url = URL.createObjectURL(blob);

    // Cleanup
    for (let i = 0; i < validScenes.length; i++) {
      try { await ffmpeg.deleteFile(`img_${i}.png`); } catch {}
      try { await ffmpeg.deleteFile(`segment_${i}.mp4`); } catch {}
      try { await ffmpeg.deleteFile(`audio_${i}.mp3`); } catch {}
    }
    try { await ffmpeg.deleteFile('concat.txt'); } catch {}
    try { await ffmpeg.deleteFile('output.mp4'); } catch {}

    return { url, blob, time: Math.round((Date.now() - startTime) / 1000), format: 'mp4' };
  }, [scenes]);

  // ─── MediaRecorder WebM Fallback ──────────────────────────────────────────
  const exportWithMediaRecorder = useCallback(async () => {
    const startTime = Date.now();

    setPhase('downloading');
    setMessage('Preparing scenes...');
    setProgress(10);

    const validScenes = scenes.filter(s => s.image_url);
    if (!validScenes.length) throw new Error('No scene images available');

    // Preload images
    const images = [];
    for (let i = 0; i < validScenes.length; i++) {
      setMessage(`Loading image ${i + 1}/${validScenes.length}...`);
      setProgress(10 + Math.round((i / validScenes.length) * 20));
      const img = new Image();
      img.crossOrigin = 'anonymous';
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = () => resolve(); // Continue even if image fails
        img.src = validScenes[i].image_url;
      });
      images.push(img);
    }

    // Preload audio
    const audioElements = [];
    for (let i = 0; i < validScenes.length; i++) {
      if (validScenes[i].audio_url) {
        const audio = new Audio();
        audio.crossOrigin = 'anonymous';
        audio.preload = 'auto';
        await new Promise((resolve) => {
          audio.oncanplaythrough = resolve;
          audio.onerror = () => resolve();
          audio.src = validScenes[i].audio_url;
        });
        audioElements.push(audio);
      } else {
        audioElements.push(null);
      }
    }

    if (abortRef.current) return;

    setPhase('rendering');
    setMessage('Recording video...');
    setProgress(35);

    // Setup canvas
    const W = 1280, H = 720;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    // Create audio context for mixing
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const dest = audioCtx.createMediaStreamDestination();

    // Combine canvas video stream + audio
    const canvasStream = canvas.captureStream(15);
    const videoTrack = canvasStream.getVideoTracks()[0];
    const combinedStream = new MediaStream([videoTrack, ...dest.stream.getAudioTracks()]);

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
      ? 'video/webm;codecs=vp8,opus'
      : 'video/webm';
    const recorder = new MediaRecorder(combinedStream, { mimeType, videoBitsPerSecond: 2500000 });

    const chunks = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

    const recordingDone = new Promise((resolve) => { recorder.onstop = resolve; });
    recorder.start(100);

    // Play each scene
    for (let i = 0; i < validScenes.length; i++) {
      if (abortRef.current) { recorder.stop(); return; }

      const dur = (validScenes[i].duration || 5) * 1000;
      setMessage(`Recording scene ${i + 1}/${validScenes.length}...`);
      setProgress(35 + Math.round(((i + 1) / validScenes.length) * 55));

      // Draw image on canvas
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, W, H);
      if (images[i]?.complete && images[i].naturalWidth > 0) {
        const scale = Math.min(W / images[i].naturalWidth, H / images[i].naturalHeight);
        const sw = images[i].naturalWidth * scale;
        const sh = images[i].naturalHeight * scale;
        ctx.drawImage(images[i], (W - sw) / 2, (H - sh) / 2, sw, sh);
      }

      // Play audio for this scene
      if (audioElements[i]) {
        try {
          const source = audioCtx.createMediaElementSource(audioElements[i]);
          source.connect(dest);
          audioElements[i].currentTime = 0;
          await audioElements[i].play();
        } catch (e) { console.warn('Audio play failed:', e); }
      }

      // Wait for scene duration
      await new Promise((resolve) => setTimeout(resolve, dur));

      // Stop audio
      if (audioElements[i]) {
        try { audioElements[i].pause(); } catch {}
      }
    }

    recorder.stop();
    await recordingDone;
    audioCtx.close();

    const blob = new Blob(chunks, { type: 'video/webm' });
    const url = URL.createObjectURL(blob);

    return { url, blob, time: Math.round((Date.now() - startTime) / 1000), format: 'webm' };
  }, [scenes]);

  // ─── Main export handler ──────────────────────────────────────────────────
  const startExport = useCallback(async () => {
    abortRef.current = false;
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
      toast.success(`Video exported successfully! (${result.format.toUpperCase()})`);
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
              toast.success('Video exported as WebM!');
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
    a.click();
  };

  const abort = () => {
    abortRef.current = true;
    setPhase('ready');
    setProgress(0);
    setMessage('');
  };

  // No export available at all
  if (exportMode && exportMode.mode === 'none') {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="browser-export-unsupported">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-white font-semibold">Browser Export Not Available</h3>
            <p className="text-slate-400 text-sm mt-1">{exportMode.reason}</p>
            <p className="text-slate-400 text-sm mt-2">
              You can still download the <strong className="text-teal-400">Story Pack</strong> with all your assets,
              or use the <strong className="text-emerald-400">Instant Preview</strong> to watch your story.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const formatLabel = exportMode?.mode === 'ffmpeg' ? 'MP4' : 'WebM';
  const doneSize = videoBlob ? (videoBlob.size / (1024 * 1024)).toFixed(1) : '0';

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="browser-video-export">
      {/* Header */}
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
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400">
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {phase === 'ready' && (
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-4 text-sm text-slate-400">
              <span className="flex items-center gap-1"><Monitor className="w-4 h-4" /> 720p</span>
              <span className="flex items-center gap-1"><Film className="w-4 h-4" /> {formatLabel}</span>
              <span className="flex items-center gap-1"><Smartphone className="w-4 h-4" /> {scenes.length} scenes</span>
            </div>
            {exportMode?.mode === 'mediarecorder' && (
              <p className="text-xs text-amber-400/80 bg-amber-500/10 rounded-lg px-3 py-2">
                Your browser doesn't support MP4 export. We'll create a WebM video instead — it plays in all modern browsers.
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
                <Download className="w-4 h-4 mr-2" /> Download {formatLabel}
              </Button>
              <Button onClick={() => { setPhase('ready'); setVideoUrl(null); setVideoBlob(null); }} variant="outline" className="border-slate-700 text-slate-300">
                Re-export
              </Button>
            </div>
          </div>
        )}

        {phase === 'error' && (
          <div className="text-center space-y-3">
            <p className="text-red-400 text-sm">{message}</p>
            <div className="flex items-center justify-center gap-3">
              <Button onClick={startExport} className="bg-purple-600 hover:bg-purple-700" data-testid="retry-export-btn">
                Retry Export
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              If export keeps failing, download the <strong>Story Pack</strong> or share the <strong>Preview URL</strong> instead.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
