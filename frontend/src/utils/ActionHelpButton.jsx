/* eslint-disable react/prop-types */
import React from 'react';
import { HelpCircle } from 'lucide-react';
import { useActionGuide } from './ActionGuide';

/**
 * P0 "What should I do?" helper button.
 *
 * Default mode = "inline" — drop this in any page header / toolbar.
 *   <ActionHelpButton actionId="story_video" />
 *
 * Optional mode = "floating" — fixed bottom-right pill.
 *   <ActionHelpButton actionId="story_video" mode="floating" />
 */
export default function ActionHelpButton({
  actionId = 'story_video',
  label = 'What should I do?',
  mode = 'inline',
}) {
  const { openGuide } = useActionGuide(actionId);

  const baseCls =
    'rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-semibold ' +
    'flex items-center gap-1.5 shadow-[0_6px_18px_-6px_rgba(168,85,247,0.5)] ' +
    'hover:scale-[1.03] active:scale-[0.98] transition-transform';

  if (mode === 'floating') {
    return (
      <button
        onClick={() => openGuide()}
        className={`fixed z-40 right-4 sm:right-6 bottom-20 sm:bottom-24 px-3.5 py-2.5 text-xs ${baseCls}`}
        data-testid="action-help-button"
        aria-label={label}
      >
        <HelpCircle className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">{label}</span>
        <span className="sm:hidden">Help</span>
      </button>
    );
  }

  return (
    <button
      onClick={() => openGuide()}
      className={`px-3 py-1.5 text-xs ${baseCls}`}
      data-testid="action-help-button"
      aria-label={label}
    >
      <HelpCircle className="w-3.5 h-3.5" />
      <span className="hidden sm:inline">{label}</span>
      <span className="sm:hidden">Help</span>
    </button>
  );
}
