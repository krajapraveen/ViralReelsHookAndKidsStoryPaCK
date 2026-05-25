import { useEffect, useState } from 'react';
import * as Network from 'expo-network';

export function useNetworkStatus() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function check() {
      const state = await Network.getNetworkStateAsync();
      if (mounted) {
        setIsOffline(state.isConnected === false || state.isInternetReachable === false);
      }
    }

    check();
    const timer = setInterval(check, 15000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return { isOffline };
}
