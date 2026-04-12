import React, { useState, useEffect } from 'react';
import { Bell, X } from 'lucide-react';
import { Button } from './ui/button';
import { usePushNotifications } from '../hooks/usePushNotifications';

/**
 * PushPrompt — Non-intrusive prompt to enable push notifications.
 * Only shows if: supported, not yet granted, user has participated in at least 1 battle/war.
 * Dismissable with 7-day cooldown.
 */
export default function PushPrompt() {
  const { permission, requestPermission, isSupported } = usePushNotifications();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!isSupported || permission !== 'default') return;

    // Check cooldown
    const dismissed = localStorage.getItem('push_prompt_dismissed');
    if (dismissed) {
      const dismissedAt = new Date(dismissed);
      if (Date.now() - dismissedAt.getTime() < 7 * 24 * 60 * 60 * 1000) return;
    }

    // Show after 5 seconds
    const timer = setTimeout(() => setVisible(true), 5000);
    return () => clearTimeout(timer);
  }, [isSupported, permission]);

  if (!visible) return null;

  const handleEnable = async () => {
    const success = await requestPermission();
    if (success) {
      setVisible(false);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem('push_prompt_dismissed', new Date().toISOString());
    setVisible(false);
  };

  return (
    <div className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:max-w-sm z-50 animate-in slide-in-from-bottom-4"
      data-testid="push-prompt">
      <div className="rounded-xl border border-violet-500/20 bg-slate-900/95 backdrop-blur-md shadow-2xl p-4">
        <button onClick={handleDismiss} className="absolute top-3 right-3 text-white/30 hover:text-white">
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center flex-shrink-0">
            <Bell className="w-5 h-5 text-violet-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold text-white mb-1">Never miss a rank drop</p>
            <p className="text-xs text-white/40 mb-3">
              Get instant alerts when someone beats your story. Take it back before it's too late.
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleEnable}
                className="bg-violet-600 hover:bg-violet-700 text-white text-xs font-bold"
                data-testid="enable-push-btn"
              >
                Enable Alerts
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDismiss}
                className="text-white/30 text-xs"
                data-testid="dismiss-push-btn"
              >
                Not now
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
