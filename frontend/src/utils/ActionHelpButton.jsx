/* eslint-disable react/prop-types */
import React from 'react';
import { HelpCircle } from 'lucide-react';
import { useActionGuide } from './ActionGuide';

/**
 * P0 Floating Help Button — "What should I do?"
 * Drop this on any Story-to-Video / Studio surface; it pops the relevant
 * action guide on demand. Does NOT auto-open. Returning users still get
 * help when they need it.
 *
 *   <ActionHelpButton actionId="story_video" />
 */
export default function ActionHelpButton({ actionId = 'story_video', label = 'What should I do?' }) {
  const { openGuide } = useActionGuide(actionId);
  return (
    <button
      onClick={() => openGuide()}
      className="fixed z-40 right-4 sm:right-6 bottom-20 sm:bottom-24 px-3.5 py-2.5 rounded-full
                 bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white text-xs font-semibold
                 flex items-center gap-1.5 shadow-[0_8px_24px_-6px_rgba(168,85,247,0.55)]
                 hover:scale-[1.03] active:scale-[0.98] transition-transform"
      data-testid="action-help-button"
      aria-label={label}
    >
      <HelpCircle className="w-3.5 h-3.5" />
      <span className="hidden sm:inline">{label}</span>
      <span className="sm:hidden">Help</span>
    </button>
  );
}
