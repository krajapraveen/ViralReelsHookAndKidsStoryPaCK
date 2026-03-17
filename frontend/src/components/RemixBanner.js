import React from 'react';
import { Sparkles, X, Pencil } from 'lucide-react';
import { getToolLabel } from '../hooks/useRemixData';

export default function RemixBanner({ sourceTool, sourceTitle, onDismiss, onEdit }) {
  if (!sourceTool) return null;

  const label = getToolLabel(sourceTool);

  return (
    <div
      className="relative rounded-xl border border-amber-500/20 bg-gradient-to-r from-amber-500/[0.06] to-orange-500/[0.04] px-4 py-3 flex items-center gap-3 animate-in slide-in-from-top-2 duration-300"
      data-testid="remix-banner"
    >
      <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center shrink-0">
        <Sparkles className="w-4 h-4 text-amber-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">
          Prefilled from {label}
          {sourceTitle && <span className="text-amber-400/80 ml-1">— {sourceTitle}</span>}
        </p>
        <p className="text-[11px] text-slate-400">Ready to create. Edit or generate now.</p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        {onEdit && (
          <button
            onClick={onEdit}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            data-testid="remix-banner-edit"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
        )}
        <button
          onClick={onDismiss}
          className="p-1.5 rounded-md text-slate-500 hover:text-white hover:bg-white/5 transition-colors"
          data-testid="remix-banner-dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
