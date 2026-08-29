import { router } from 'expo-router';

import { Screen } from '@/components/Screen';
import { ToolCard } from '@/components/ToolCard';
import { CREATOR_TOOLS } from '@/constants/features';

export default function CreateScreen() {
  return (
    <Screen
      title="Create"
      subtitle="Mobile equivalents for Visionary Suite creator tools. APIs are mapped where existing backend routes were found."
    >
      {CREATOR_TOOLS.map((tool) => (
        <ToolCard key={tool.key} tool={tool} onPress={() => router.push(tool.route as never)} />
      ))}
    </Screen>
  );
}
