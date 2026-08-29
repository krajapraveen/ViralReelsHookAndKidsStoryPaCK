import * as Linking from 'expo-linking';
import * as Notifications from 'expo-notifications';

export const linkingPrefixes = [
  Linking.createURL('/'),
  'visionarysuite://',
  'https://visionary-suite.com',
  'https://www.visionary-suite.com',
];

export async function preparePushNotifications() {
  const permissions = await Notifications.getPermissionsAsync();
  if (!permissions.granted) {
    return {
      ready: false,
      reason: 'Push permission has not been granted.',
      todo: 'Add Expo/FCM/APNS token registration endpoints before enabling production push.',
    };
  }

  return {
    ready: true,
    todo: 'Backend currently exposes Web Push. Add native push token registration before sending notifications.',
  };
}
