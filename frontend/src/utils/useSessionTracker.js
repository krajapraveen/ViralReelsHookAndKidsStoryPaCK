/**
 * useSessionTracker — Tracks session_started and session_ended with duration.
 * Fires session_started on mount, session_ended on tab close / visibility change.
 * Deduplicates: only ONE session_started per page load.
 */
import { useEffect, useRef } from 'react';
import { trackFunnel, getSessionId } from './funnelTracker';

export default function useSessionTracker() {
  const started = useRef(false);
  const startTime = useRef(Date.now());

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    startTime.current = Date.now();

    trackFunnel('session_started', {
      meta: { entry_url: window.location.pathname },
    });

    const endSession = () => {
      const duration = Math.round((Date.now() - startTime.current) / 1000);
      const payload = JSON.stringify({
        step: 'session_ended',
        session_id: getSessionId(),
        user_id: null,
        context: {
          source_page: window.location.pathname,
          device_type: window.innerWidth < 768 ? 'mobile' : window.innerWidth < 1024 ? 'tablet' : 'desktop',
          meta: { duration_seconds: duration, exit_url: window.location.pathname },
        },
      });
      // Use sendBeacon for reliable delivery on tab close
      const url = `${process.env.REACT_APP_BACKEND_URL}/api/funnel/track`;
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
      }
    };

    // Fire on tab close
    window.addEventListener('beforeunload', endSession);
    // Fire on visibility change (tab switch on mobile)
    const onVisChange = () => {
      if (document.visibilityState === 'hidden') endSession();
    };
    document.addEventListener('visibilitychange', onVisChange);

    return () => {
      window.removeEventListener('beforeunload', endSession);
      document.removeEventListener('visibilitychange', onVisChange);
    };
  }, []);
}
