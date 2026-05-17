import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import './index.css';
import App from './App';
import { Toaster } from './components/ui/sonner';

// P0 2026-05-19 CASE B — defensive Service Worker unregister.
//
// The app itself never registers a Service Worker, but legacy
// deployments and some third-party SDKs can leave one behind, and on
// Cloudflare / the platform CDN, a stale SW will serve old bundles
// from disk even on incognito if the browser shared the SW with the
// container before. This unregister runs at every boot so a stale SW
// can never persist across a single hard refresh.
if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((reg) => {
      // eslint-disable-next-line no-console
      console.info('[boot] unregistering legacy ServiceWorker', reg.scope);
      reg.unregister().catch(() => {});
    });
  }).catch(() => {});
  // Also clear any Cache Storage entries — these are what an old SW
  // would have written. Without this the next page load still serves
  // stale JS bundles from the Cache Storage even after unregister.
  if (typeof caches !== 'undefined') {
    caches.keys().then((names) => {
      names.forEach((name) => caches.delete(name).catch(() => {}));
    }).catch(() => {});
  }
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <App />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
);