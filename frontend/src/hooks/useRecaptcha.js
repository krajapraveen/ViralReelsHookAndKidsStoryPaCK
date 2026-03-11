import { useCallback, useEffect, useRef } from 'react';

const SITE_KEY = process.env.REACT_APP_RECAPTCHA_SITE_KEY;

let scriptLoaded = false;
let scriptLoading = false;
const loadCallbacks = [];

function loadRecaptchaScript() {
  if (scriptLoaded || !SITE_KEY) return Promise.resolve();
  if (scriptLoading) {
    return new Promise((resolve) => loadCallbacks.push(resolve));
  }

  scriptLoading = true;
  return new Promise((resolve) => {
    loadCallbacks.push(resolve);
    const script = document.createElement('script');
    script.src = `https://www.google.com/recaptcha/api.js?render=${SITE_KEY}`;
    script.async = true;
    script.onload = () => {
      scriptLoaded = true;
      loadCallbacks.forEach((cb) => cb());
      loadCallbacks.length = 0;
    };
    script.onerror = () => {
      scriptLoading = false;
      loadCallbacks.forEach((cb) => cb());
      loadCallbacks.length = 0;
    };
    document.head.appendChild(script);
  });
}

export function useRecaptcha() {
  const ready = useRef(false);

  useEffect(() => {
    loadRecaptchaScript().then(() => {
      ready.current = true;
    });
  }, []);

  const executeRecaptcha = useCallback(async (action) => {
    if (!SITE_KEY) return '';
    if (!ready.current) await loadRecaptchaScript();
    try {
      const token = await window.grecaptcha.execute(SITE_KEY, { action });
      return token;
    } catch (e) {
      console.warn('reCAPTCHA execute failed:', e);
      return '';
    }
  }, []);

  return { executeRecaptcha, siteKey: SITE_KEY };
}
