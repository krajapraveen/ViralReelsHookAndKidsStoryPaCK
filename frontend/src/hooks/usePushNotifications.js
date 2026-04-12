import { useEffect, useState, useCallback } from 'react';
import api from '../utils/api';

const VAPID_KEY = process.env.REACT_APP_VAPID_PUBLIC_KEY;

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

/**
 * usePushNotifications — Manages service worker registration and push subscription.
 * Auto-subscribes if permission granted. Prompts on first use.
 */
export function usePushNotifications() {
  const [permission, setPermission] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  );
  const [subscribed, setSubscribed] = useState(false);

  const subscribe = useCallback(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !VAPID_KEY) {
      return false;
    }

    try {
      const reg = await navigator.serviceWorker.register('/sw-push.js');
      await navigator.serviceWorker.ready;

      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(VAPID_KEY),
        });
      }

      // Send to backend
      const subJson = sub.toJSON();
      await api.post('/api/push/subscribe', {
        endpoint: subJson.endpoint,
        keys: subJson.keys,
      });

      setSubscribed(true);
      return true;
    } catch (err) {
      console.warn('[Push] Subscription failed:', err);
      return false;
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if (typeof Notification === 'undefined') return false;

    const result = await Notification.requestPermission();
    setPermission(result);
    if (result === 'granted') {
      return await subscribe();
    }
    return false;
  }, [subscribe]);

  // Auto-subscribe if already granted
  useEffect(() => {
    if (permission === 'granted' && !subscribed) {
      subscribe();
    }
  }, [permission, subscribed, subscribe]);

  return {
    permission,
    subscribed,
    requestPermission,
    subscribe,
    isSupported: typeof Notification !== 'undefined' && 'serviceWorker' in navigator,
  };
}
