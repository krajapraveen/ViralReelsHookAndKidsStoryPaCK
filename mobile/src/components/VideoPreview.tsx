import { ResizeMode, Video } from 'expo-av';
import { useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';

import { Button } from './Button';

type VideoPreviewProps = {
  jobId?: string;
  uri?: string;
  thumbnailUri?: string;
  onRetry?: () => void;
};

export function VideoPreview({ jobId, uri, thumbnailUri, onRetry }: VideoPreviewProps) {
  const [loading, setLoading] = useState(Boolean(uri));
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  if (!uri) {
    return (
      <View className="aspect-video items-center justify-center rounded-3xl border border-dashed border-white/15 bg-black/30">
        <ActivityIndicator color="#22d3ee" />
        <Text className="mt-3 text-center text-slate-300">Finalizing video...</Text>
      </View>
    );
  }

  return (
    <View className="overflow-hidden rounded-3xl border border-white/10 bg-black">
      {loading || error ? (
        <View className="absolute inset-0 z-10 items-center justify-center bg-black/80 px-5">
          {loading ? <ActivityIndicator color="#22d3ee" /> : null}
          <Text className="mt-3 text-center text-slate-200">
            {error || 'Loading playable video...'}
          </Text>
          {error && onRetry ? (
            <View className="mt-4 w-full">
              <Button title="Retry playback" variant="secondary" onPress={onRetry} />
            </View>
          ) : null}
        </View>
      ) : null}
      <Video
        key={`${jobId || 'video'}:${uri}`}
        source={{ uri }}
        useNativeControls
        usePoster={Boolean(thumbnailUri)}
        posterSource={thumbnailUri ? { uri: thumbnailUri } : undefined}
        resizeMode={ResizeMode.CONTAIN}
        onLoadStart={() => {
          setLoading(true);
          setError(null);
          setReady(false);
          console.info('[video.playback.load_start]', { uri });
        }}
        onReadyForDisplay={() => {
          setLoading(false);
          setReady(true);
          console.info('[video.playback.ready]', { uri });
        }}
        onError={(event) => {
          setLoading(false);
          const message = String((event as any)?.nativeEvent?.error || 'Video playback failed.');
          setError(message);
          console.warn('[video.playback.error]', { uri, message });
        }}
        style={{ width: '100%', aspectRatio: 16 / 9 }}
      />
      {ready && !error ? (
        <View pointerEvents="none" className="absolute inset-0 items-center justify-center">
          <View className="rounded-full bg-black/55 px-5 py-3">
            <Text className="text-center font-bold text-white">▶ Tap to play</Text>
          </View>
        </View>
      ) : null}
    </View>
  );
}
