import { ResizeMode, Video, type AVPlaybackStatus } from 'expo-av';
import { useRef, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import { Button } from './Button';

type VideoPreviewProps = {
  jobId?: string;
  uri?: string;
  thumbnailUri?: string;
  onRetry?: () => void;
};

export function VideoPreview({ jobId, uri, thumbnailUri, onRetry }: VideoPreviewProps) {
  const videoRef = useRef<Video>(null);
  const [loading, setLoading] = useState(Boolean(uri));
  const [error, setError] = useState<string | null>(null);
  const [playbackState, setPlaybackState] = useState<'thumbnail_ready' | 'loading_video' | 'ready_to_play' | 'starting' | 'playing' | 'ended'>(
    'loading_video',
  );

  const startPlayback = async () => {
    if (!uri || !videoRef.current) return;
    setError(null);
    setPlaybackState('starting');
    setLoading(true);
    console.info('[video.playback.play_requested]', { uri });
    try {
      const currentStatus = await videoRef.current.getStatusAsync();
      if ('isLoaded' in currentStatus && currentStatus.isLoaded) {
        await videoRef.current.setPositionAsync(0);
      } else {
        await videoRef.current.loadAsync({ uri }, { shouldPlay: false }, false);
      }
      const status = await videoRef.current.playAsync();
      if ('isLoaded' in status && status.isLoaded) {
        // Expo may report isPlaying on the next status tick; keep spinner until then.
        if (!status.isPlaying) {
          console.info('[video.playback.play_pending]', { uri, status });
          return;
        }
        setPlaybackState('playing');
        setLoading(false);
        console.info('[video.playback.play_started]', { uri });
      } else {
        setPlaybackState('ready_to_play');
        setLoading(false);
        setError('Video is not loaded yet. Tap retry to try again.');
        console.warn('[video.playback.play_not_started]', { uri, status });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Video playback failed to start.';
      setPlaybackState('ready_to_play');
      setLoading(false);
      setError(message);
      console.warn('[video.playback.play_failed]', { uri, message });
    }
  };

  const handlePlaybackStatus = (status: AVPlaybackStatus) => {
    if (!status.isLoaded) return;
    if (status.isPlaying) {
      setPlaybackState('playing');
      setLoading(false);
      return;
    }
    if (status.didJustFinish) {
      setPlaybackState('ended');
      return;
    }
    if (playbackState === 'loading_video') {
      setPlaybackState('ready_to_play');
    }
  };

  if (!uri) {
    return (
      <View className="aspect-video items-center justify-center rounded-3xl border border-dashed border-white/15 bg-black/30">
        <ActivityIndicator color="#22d3ee" />
        <Text className="mt-3 text-center text-slate-300">Finalizing video...</Text>
      </View>
    );
  }

  return (
    <Pressable onPress={startPlayback} className="overflow-hidden rounded-3xl border border-white/10 bg-black">
      {loading || error ? (
        <Pressable onPress={startPlayback} className="absolute inset-0 z-20 items-center justify-center bg-black/80 px-5">
          {loading ? <ActivityIndicator color="#22d3ee" /> : null}
          <Text className="mt-3 text-center text-slate-200">
            {error || (playbackState === 'starting' ? 'Starting video...' : 'Loading playable video...')}
          </Text>
          {error && onRetry ? (
            <View className="mt-4 w-full">
              <Button title="Retry playback" variant="secondary" onPress={startPlayback} />
            </View>
          ) : null}
        </Pressable>
      ) : null}
      <Video
        ref={videoRef}
        key={`${jobId || 'video'}:${uri}`}
        source={{ uri }}
        useNativeControls
        shouldPlay={false}
        usePoster={Boolean(thumbnailUri)}
        posterSource={thumbnailUri ? { uri: thumbnailUri } : undefined}
        resizeMode={ResizeMode.CONTAIN}
        onLoadStart={() => {
          setLoading(true);
          setError(null);
          setPlaybackState('loading_video');
          console.info('[video.playback.load_start]', { uri });
        }}
        onLoad={(status) => {
          setLoading(false);
          setPlaybackState('ready_to_play');
          console.info('[video.playback.loaded]', { uri, status });
        }}
        onReadyForDisplay={() => {
          setLoading(false);
          setPlaybackState((current) => (current === 'loading_video' ? 'ready_to_play' : current));
          console.info('[video.playback.ready]', { uri });
        }}
        onPlaybackStatusUpdate={handlePlaybackStatus}
        onError={(event) => {
          setLoading(false);
          setPlaybackState('ready_to_play');
          const message = String((event as any)?.nativeEvent?.error || 'Video playback failed.');
          setError(message);
          console.warn('[video.playback.error]', { uri, message });
        }}
        style={{ width: '100%', aspectRatio: 16 / 9 }}
      />
      {['ready_to_play', 'ended'].includes(playbackState) && !error ? (
        <Pressable onPress={startPlayback} className="absolute inset-0 items-center justify-center">
          <View className="rounded-full bg-black/55 px-5 py-3">
            <Text className="text-center font-bold text-white">
              {playbackState === 'ended' ? '↻ Replay' : '▶ Tap to play'}
            </Text>
          </View>
        </Pressable>
      ) : null}
    </Pressable>
  );
}
