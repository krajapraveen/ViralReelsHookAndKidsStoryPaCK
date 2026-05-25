import { ResizeMode, Video } from 'expo-av';
import { Text, View } from 'react-native';

type VideoPreviewProps = {
  uri?: string;
};

export function VideoPreview({ uri }: VideoPreviewProps) {
  if (!uri) {
    return (
      <View className="aspect-video items-center justify-center rounded-3xl border border-dashed border-white/15 bg-black/30">
        <Text className="text-center text-slate-300">Video output will appear here when the job completes.</Text>
      </View>
    );
  }

  return (
    <View className="overflow-hidden rounded-3xl border border-white/10 bg-black">
      <Video
        source={{ uri }}
        useNativeControls
        resizeMode={ResizeMode.CONTAIN}
        style={{ width: '100%', aspectRatio: 16 / 9 }}
      />
    </View>
  );
}
