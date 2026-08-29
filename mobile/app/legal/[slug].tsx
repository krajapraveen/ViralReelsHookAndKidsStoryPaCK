import { useLocalSearchParams } from 'expo-router';
import { Text, View } from 'react-native';

import { Screen } from '@/components/Screen';

const legalCopy: Record<string, { title: string; body: string; route: string }> = {
  privacy: {
    title: 'Privacy policy',
    route: '/privacy-policy',
    body:
      'Mobile privacy content should mirror the web Privacy Policy. Existing backend privacy APIs cover consent, export, and delete requests.',
  },
  terms: {
    title: 'Terms of service',
    route: '/terms',
    body:
      'Mobile terms should mirror the web Terms of Service and include subscription/payment language once native payments are finalized.',
  },
  cookies: {
    title: 'Cookie policy',
    route: '/cookie-policy',
    body:
      'Native apps do not use browser cookies the same way as web, but this page preserves the legal surface and links back to the web policy.',
  },
  security: {
    title: 'Security',
    route: '/security',
    body:
      'Security and vulnerability disclosure surfaces exist on web and backend. Mobile should expose report/contact entry points without porting admin triage.',
  },
};

export default function LegalScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const page = legalCopy[slug || 'privacy'] || legalCopy.privacy;

  return (
    <Screen title={page.title} subtitle="Legal content is intentionally aligned with existing web routes.">
      <View className="rounded-3xl border border-white/10 bg-white/5 p-5">
        <Text className="leading-7 text-slate-200">{page.body}</Text>
        <Text className="mt-5 text-sm font-semibold uppercase tracking-wide text-slate-400">Source web route</Text>
        <Text className="mt-1 text-aurora">{page.route}</Text>
      </View>
    </Screen>
  );
}
