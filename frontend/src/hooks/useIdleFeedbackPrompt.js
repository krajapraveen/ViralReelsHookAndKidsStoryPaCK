import { useState, useEffect, useRef, useCallback } from 'react';
import { getFeedbackEligibility, markFeedbackPromptShown } from '../utils/feedbackSession';

/**
 * useIdleFeedbackPrompt — fires callback once after idle threshold
 * Only triggers if user has used a feature this session.
 */
export default function useIdleFeedbackPrompt(onIdle, idleMs = 120000) {
  const timerRef = useRef(null);
  const startedRef = useRef(null);
  const firedRef = useRef(false);

  const schedule = useCallback(() => {
    if (firedRef.current) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    const { eligible, hasUsedFeature } = getFeedbackEligibility();
    if (!hasUsedFeature || !eligible) return;

    startedRef.current = Date.now();
    timerRef.current = setTimeout(() => {
      const latest = getFeedbackEligibility();
      if (!latest.eligible || firedRef.current) return;
      firedRef.current = true;
      markFeedbackPromptShown();
      const idleSec = Math.floor((Date.now() - (startedRef.current || Date.now())) / 1000);
      onIdle(idleSec);
    }, idleMs);
  }, [onIdle, idleMs]);

  useEffect(() => {
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    const reset = () => schedule();
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    schedule();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [schedule]);

  return { cancel: () => { firedRef.current = true; if (timerRef.current) clearTimeout(timerRef.current); } };
}
