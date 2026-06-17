/**
 * useAppleSignIn — Sign in with Apple JS SDK hook (popup mode).
 *
 * Apple App Store Guideline 4.8.0 / web parity: the website must
 * offer Sign in with Apple alongside Google. This hook mirrors the
 * shape of `useGoogleLogin` so Login.js + Signup.js drop-in alongside
 * the existing Google integration with minimal code change.
 *
 * Flow:
 *   1. Lazily inject Apple's official JS SDK once per page load.
 *   2. Initialise AppleID.auth with the Services ID + Return URI.
 *   3. On user click → AppleID.auth.signIn() opens the Apple popup.
 *   4. On success Apple resolves with `authorization.id_token` (a
 *      signed JWT). We POST it to `/api/auth/apple-signin` — the
 *      same endpoint the iOS app uses — and the backend verifies
 *      the JWT against Apple's JWKS, accepts the web Services ID
 *      as a valid audience, and returns `{ token, user }`.
 *
 * Config (frontend env):
 *   REACT_APP_APPLE_SERVICES_ID   — e.g. `com.visionarysuite.web`
 *   REACT_APP_APPLE_REDIRECT_URI  — e.g. `https://visionary-suite.com/auth/apple/callback`
 *
 * If the Services ID is not configured the hook returns
 * `{ ready: false, signIn: noop }` so callers can hide the button
 * without crashing.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

const APPLE_SDK_SRC =
  'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js';

function loadAppleSDK() {
  if (typeof window === 'undefined') return Promise.reject(new Error('SSR'));
  if (window.AppleID && window.AppleID.auth) return Promise.resolve(window.AppleID);

  // De-dupe parallel callers
  if (window.__appleSdkPromise) return window.__appleSdkPromise;

  window.__appleSdkPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${APPLE_SDK_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(window.AppleID));
      existing.addEventListener('error', () => reject(new Error('apple_sdk_load_failed')));
      return;
    }
    const script = document.createElement('script');
    script.src = APPLE_SDK_SRC;
    script.async = true;
    script.defer = true;
    script.crossOrigin = 'anonymous';
    script.onload = () => {
      if (window.AppleID && window.AppleID.auth) resolve(window.AppleID);
      else reject(new Error('apple_sdk_missing_after_load'));
    };
    script.onerror = () => reject(new Error('apple_sdk_load_failed'));
    document.head.appendChild(script);
  });

  return window.__appleSdkPromise;
}

export function useAppleSignIn({ onSuccess, onError, onCancel } = {}) {
  const clientId = process.env.REACT_APP_APPLE_SERVICES_ID || '';
  const redirectURI =
    process.env.REACT_APP_APPLE_REDIRECT_URI ||
    (typeof window !== 'undefined'
      ? `${window.location.origin}/auth/apple/callback`
      : '');

  const [ready, setReady] = useState(false);
  // Refs so the latest callbacks fire even after the SDK init promise resolves.
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  const onCancelRef = useRef(onCancel);
  useEffect(() => { onSuccessRef.current = onSuccess; }, [onSuccess]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);
  useEffect(() => { onCancelRef.current = onCancel; }, [onCancel]);

  useEffect(() => {
    if (!clientId) return; // Hook disabled until Services ID is configured.
    let cancelled = false;
    loadAppleSDK()
      .then((AppleID) => {
        if (cancelled) return;
        try {
          AppleID.auth.init({
            clientId,
            scope: 'name email',
            redirectURI,
            // `state` is echoed back by Apple. We use it for CSRF protection
            // when the response comes via redirect; popup mode returns the
            // response synchronously so the state check is opportunistic.
            state: cryptoRandomState(),
            usePopup: true,
          });
          setReady(true);
        } catch (e) {
          if (onErrorRef.current) {
            onErrorRef.current({ type: 'apple_init_failed', error: String(e) });
          }
        }
      })
      .catch((e) => {
        if (onErrorRef.current) {
          onErrorRef.current({ type: 'apple_sdk_load_failed', error: String(e) });
        }
      });
    return () => { cancelled = true; };
  }, [clientId, redirectURI]);

  const signIn = useCallback(async () => {
    if (!ready || !window.AppleID || !window.AppleID.auth) {
      if (onErrorRef.current) {
        onErrorRef.current({ type: 'apple_not_ready' });
      }
      return;
    }
    try {
      const response = await window.AppleID.auth.signIn();
      // Apple JS SDK response shape:
      //   {
      //     authorization: { code, id_token, state },
      //     user?: { email, name: { firstName, lastName } }   // first sign-in only
      //   }
      const idToken = response?.authorization?.id_token;
      if (!idToken) {
        if (onErrorRef.current) {
          onErrorRef.current({ type: 'apple_no_id_token', response });
        }
        return;
      }
      const fullName = response?.user?.name
        ? [response.user.name.firstName, response.user.name.lastName]
            .filter(Boolean).join(' ')
        : '';
      const email = response?.user?.email || '';
      if (onSuccessRef.current) {
        onSuccessRef.current({
          identityToken: idToken,
          authorizationCode: response?.authorization?.code,
          fullName,
          email,
          state: response?.authorization?.state,
        });
      }
    } catch (err) {
      // Apple SDK rejects with `{ error: 'popup_closed_by_user' }` etc.
      const errorCode = err?.error || err?.message || 'apple_signin_failed';
      if (errorCode === 'popup_closed_by_user' || errorCode === 'user_cancelled_authorize') {
        if (onCancelRef.current) onCancelRef.current({ type: errorCode });
        return;
      }
      if (onErrorRef.current) {
        onErrorRef.current({ type: errorCode, error: err });
      }
    }
  }, [ready]);

  return { ready: ready && Boolean(clientId), signIn, configured: Boolean(clientId) };
}

function cryptoRandomState() {
  try {
    const buf = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(buf);
    return Array.from(buf).map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch {
    return String(Math.random()).slice(2) + Date.now().toString(16);
  }
}
