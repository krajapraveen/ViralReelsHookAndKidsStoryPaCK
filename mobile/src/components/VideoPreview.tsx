import { ResizeMode, Video } from 'expo-av';
import { useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';

import { Button } from './Button';

type VideoPreviewProps = {
  uri?: string;
  onRetry?: () => void;
};

export function VideoPreview({ uri, onRetry }: VideoPreviewProps) {
  const [loading, setLoading] = useState(Boolean(uri));
  const [error, setError] = useState<string | null>(null);

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
        key={uri}
        source={{ uri }}
        useNativeControls
        resizeMode={ResizeMode.CONTAIN}
        onLoadStart={() => {
          setLoading(true);
          setError(null);
          console.info('[video.playback.load_start]', { uri });
        }}
        onReadyForDisplay={() => {
          setLoading(false);
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
    </View>
  );
}
