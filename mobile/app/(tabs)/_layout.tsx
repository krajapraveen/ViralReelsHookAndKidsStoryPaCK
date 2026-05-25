import { Tabs } from 'expo-router';

import { ProtectedRoute } from '@/components/ProtectedRoute';
import { colors } from '@/theme/colors';

export default function TabsLayout() {
  return (
    <ProtectedRoute>
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            backgroundColor: colors.midnight,
            borderTopColor: colors.border,
          },
          tabBarActiveTintColor: colors.aurora,
          tabBarInactiveTintColor: colors.subtle,
        }}
      >
        <Tabs.Screen name="home" options={{ title: 'Home' }} />
        <Tabs.Screen name="create" options={{ title: 'Create' }} />
        <Tabs.Screen name="library" options={{ title: 'Library' }} />
        <Tabs.Screen name="wallet" options={{ title: 'Wallet' }} />
        <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
      </Tabs>
    </ProtectedRoute>
  );
}
