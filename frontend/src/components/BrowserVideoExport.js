import React, { useState, useRef, useCallback, useEffect } from 'react';
import { FFmpeg } from '@ffmpeg/ffmpeg';
import { toBlobURL, fetchFile } from '@ffmpeg/util';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
  Film, Download, Loader2, AlertCircle, CheckCircle,
  Package, Eye, Monitor, Smartphone, X
} from 'lucide-react';
import { toast } from 'sonner';

let ffmpegInstance = null;

async function getFFmpeg() {
  if (ffmpegInstance?.loaded) return ffmpegInstance;
  ffmpegInstance = new FFmpeg();
  return ffmpegInstance;
}

// Check if browser supports ffmpeg.wasm
function checkBrowserSupport() {
  try {
    if (typeof SharedArrayBuffer === 'undefined') return { supported: false, reason: 'SharedArrayBuffer not available. Try Chrome or Firefox.' };
    if (!window.WebAssembly) return { supported: false, reason: 'WebAssembly not supported.' };
    return { supported: true };
  } catch {
    return { supported: false, reason: 'Browser compatibility check failed.' };
  }
}

export default function BrowserVideoExport({ scenes, title, jobId, onClose }) {
  const [phase, setPhase] = useState('ready'); // ready | loading | downloading | rendering | done | error
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoBlob, setVideoBlob] = useState(null);
  const [renderTime, setRenderTime] = useState(0);
  const [browserSupport, setBrowserSupport] = useState(null);
  const ffmpegRef = useRef(null);
  const abortRef = useRef(false);

  useEffect(() => {
    setBrowserSupport(checkBrowserSupport());
  }, []);

  const exportVideo = useCallback(async () => {
    abortRef.current = false;
    const startTime = Date.now();

    try {
      // Phase 1: Load FFmpeg WASM
      setPhase('loading');
      setMessage('Loading video encoder...');
      setProgress(5);

      const ffmpeg = await getFFmpeg();
      ffmpegRef.current = ffmpeg;

      if (!ffmpeg.loaded) {
        ffmpeg.on('progress', ({ progress: p }) => {
          if (phase === 'rendering') {
            setProgress(Math.min(40 + Math.round(p * 55), 95));
          }
        });

        // Load from CDN
        const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm';
        await ffmpeg.load({
          coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
          wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
        });
      }

      if (abortRef.current) return;
      setProgress(15);

      // Phase 2: Download scene assets
      setPhase('downloading');
      setMessage('Downloading scene assets...');

      const validScenes = scenes.filter(s => s.image_url);
      if (validScenes.length === 0) {
        throw new Error('No scene images available');
      }

      // Download images
      for (let i = 0; i < validScenes.length; i++) {
        if (abortRef.current) return;
        const scene = validScenes[i];
        setMessage(`Downloading image ${i + 1}/${validScenes.length}...`);
        setProgress(15 + Math.round((i / validScenes.length) * 15));

        try {
          const imgData = await fetchFile(scene.image_url);
          await ffmpeg.writeFile(`img_${i}.png`, imgData);
        } catch (err) {
          console.warn(`Failed to download image ${i}:`, err);
        }
      }

      // Download audio files
      const audioScenes = validScenes.filter(s => s.audio_url);
      for (let i = 0; i < audioScenes.length; i++) {
        if (abortRef.current) return;
        const scene = audioScenes[i];
        setMessage(`Downloading audio ${i + 1}/${audioScenes.length}...`);
        setProgress(30 + Math.round((i / audioScenes.length) * 10));

        try {
          const audioData = await fetchFile(scene.audio_url);
          await ffmpeg.writeFile(`audio_${i}.mp3`, audioData);
        } catch (err) {
          console.warn(`Failed to download audio ${i}:`, err);
        }
      }

      if (abortRef.current) return;

      // Phase 3: Render video
      setPhase('rendering');
      setMessage('Rendering slideshow video...');
      setProgress(40);

      // Build FFmpeg command for slideshow with audio
      // Strategy: Create each scene as a short clip, then concat
      const W = 1280, H = 720, FPS = 15;
      const concatLines = [];

      for (let i = 0; i < validScenes.length; i++) {
        const scene = validScenes[i];
        const dur = scene.duration || 5;
        const hasAudio = audioScenes.includes(scene);
        const audioIdx = audioScenes.indexOf(scene);

        if (hasAudio && audioIdx >= 0) {
          // Scene with audio: duration matches audio
          await ffmpeg.exec([
            '-loop', '1',
            '-i', `img_${i}.png`,
            '-i', `audio_${audioIdx}.mp3`,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '28',
            '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}`,
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '96k',
            '-shortest',
            '-movflags', '+faststart',
            `segment_${i}.mp4`
          ]);
        } else {
          // Scene without audio: fixed duration
          await ffmpeg.exec([
            '-loop', '1',
            '-t', `${dur}`,
            '-i', `img_${i}.png`,
            '-f', 'lavfi', '-t', `${dur}`,
            '-i', 'anullsrc=r=44100:cl=stereo',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '28',
            '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}`,
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-shortest',
            '-movflags', '+faststart',
            `segment_${i}.mp4`
          ]);
        }

        concatLines.push(`file 'segment_${i}.mp4'`);
        setProgress(40 + Math.round(((i + 1) / validScenes.length) * 45));
        setMessage(`Rendering scene ${i + 1}/${validScenes.length}...`);
      }

      // Write concat list
      const concatText = concatLines.join('\n');
      await ffmpeg.writeFile('concat.txt', concatText);

      // Concatenate all segments
      setMessage('Assembling final video...');
      setProgress(90);

      await ffmpeg.exec([
        '-f', 'concat',
        '-safe', '0',
        '-i', 'concat.txt',
        '-c', 'copy',
        '-movflags', '+faststart',
        'output.mp4'
      ]);

      // Read output
      const data = await ffmpeg.readFile('output.mp4');
      const blob = new Blob([data.buffer], { type: 'video/mp4' });
      const url = URL.createObjectURL(blob);

      setVideoUrl(url);
      setVideoBlob(blob);
      setPhase('done');
      setProgress(100);
      setRenderTime(Math.round((Date.now() - startTime) / 1000));
      setMessage('Video ready!');

      // Cleanup temp files
      for (let i = 0; i < validScenes.length; i++) {
        try { await ffmpeg.deleteFile(`img_${i}.png`); } catch {}
        try { await ffmpeg.deleteFile(`segment_${i}.mp4`); } catch {}
        try { await ffmpeg.deleteFile(`audio_${i}.mp3`); } catch {}
      }
      try { await ffmpeg.deleteFile('concat.txt'); } catch {}
      try { await ffmpeg.deleteFile('output.mp4'); } catch {}

      toast.success('Video exported successfully!');

    } catch (err) {
      console.error('Browser export failed:', err);
      setPhase('error');
      setMessage(err.message || 'Export failed');
      toast.error('Video export failed. Try downloading the Story Pack instead.');
    }
  }, [scenes, phase]);

  const downloadVideo = () => {
    if (!videoUrl) return;
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = `${title || 'story'}_${jobId?.slice(0, 8) || 'video'}.mp4`;
    a.click();
  };

  const abort = () => {
    abortRef.current = true;
    setPhase('ready');
    setProgress(0);
    setMessage('');
  };

  // Unsupported browser
  if (browserSupport && !browserSupport.supported) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="browser-export-unsupported">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-white font-semibold">Browser Export Not Available</h3>
            <p className="text-slate-400 text-sm mt-1">{browserSupport.reason}</p>
            <p className="text-slate-400 text-sm mt-2">
              You can still download the <strong className="text-purple-400">Story Pack ZIP</strong> with all your assets,
              or use the <strong className="text-emerald-400">Web Preview</strong> to view your story.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="browser-video-export">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
            phase === 'done' ? 'bg-emerald-500/20' : 'bg-purple-500/20'
          }`}>
            {phase === 'done' ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : phase === 'error' ? (
              <AlertCircle className="w-5 h-5 text-red-400" />
            ) : (
              <Film className="w-5 h-5 text-purple-400" />
            )}
          </div>
          <div>
            <h3 className="text-white font-semibold text-sm">Browser Video Export</h3>
            <p className="text-xs text-slate-400">
              {phase === 'done' 
                ? `Rendered in ${renderTime}s — ${(videoBlob?.size / (1024*1024)).toFixed(1)}MB` 
                : 'MP4 rendered directly in your browser — no server needed'}
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
        {/* Ready state */}
        {phase === 'ready' && (
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-4 text-sm text-slate-400">
              <span className="flex items-center gap-1"><Monitor className="w-4 h-4" /> 720p</span>
              <span className="flex items-center gap-1"><Film className="w-4 h-4" /> 15fps</span>
              <span className="flex items-center gap-1"><Smartphone className="w-4 h-4" /> {scenes.length} scenes</span>
            </div>
            <Button
              onClick={exportVideo}
              className="bg-purple-600 hover:bg-purple-700 px-8"
              data-testid="start-export-btn"
            >
              <Film className="w-4 h-4 mr-2" /> Export MP4 Video
            </Button>
          </div>
        )}

        {/* Processing states */}
        {['loading', 'downloading', 'rendering'].includes(phase) && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-white font-medium flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                {message}
              </span>
              <span className="text-slate-400">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
            <Button variant="outline" size="sm" onClick={abort} className="text-slate-400 border-slate-700">
              Cancel
            </Button>
          </div>
        )}

        {/* Done */}
        {phase === 'done' && videoUrl && (
          <div className="space-y-4">
            <video
              src={videoUrl}
              controls
              className="w-full rounded-lg bg-black aspect-video"
              data-testid="exported-video-player"
            />
            <div className="flex items-center gap-3">
              <Button onClick={downloadVideo} className="bg-emerald-600 hover:bg-emerald-700 flex-1" data-testid="download-exported-video">
                <Download className="w-4 h-4 mr-2" /> Download MP4
              </Button>
              <Button onClick={() => { setPhase('ready'); setVideoUrl(null); setVideoBlob(null); }} variant="outline" className="border-slate-700 text-slate-300">
                Re-export
              </Button>
            </div>
          </div>
        )}

        {/* Error */}
        {phase === 'error' && (
          <div className="text-center space-y-3">
            <p className="text-red-400 text-sm">{message}</p>
            <div className="flex items-center justify-center gap-3">
              <Button onClick={exportVideo} className="bg-purple-600 hover:bg-purple-700" data-testid="retry-export-btn">
                Retry Export
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              If export keeps failing, download the <strong>Story Pack ZIP</strong> or share the <strong>Preview URL</strong> instead.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
