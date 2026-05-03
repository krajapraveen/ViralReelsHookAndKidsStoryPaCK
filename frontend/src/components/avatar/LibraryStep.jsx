import React from 'react';
import { Plus, Video, Sparkles, Clock } from 'lucide-react';
import { DemoBadge, SectionTitle } from './shared';

/**
 * Step 0 — Avatar Library.
 * First screen the user sees. They either pick an existing avatar or
 * click "Create new" to enter the wizard proper.
 */
export default function LibraryStep({ clones = [], onCreateNew, onPickAvatar }) {
  const hasClones = clones.length > 0;
  return (
    <div className="space-y-6" data-testid="avatar-studio-library-step">
      <SectionTitle
        eyebrow="AI Cloning Studio"
        title="Your AI Avatar Library"
        sub="Pick a saved avatar to generate a new video in 30 seconds, or create a fresh one. Every output is disclosure-labeled."
      />
      <div className="flex items-center justify-between">
        <div className="text-xs text-slate-500">{hasClones ? `${clones.length} saved avatar${clones.length === 1 ? '' : 's'}` : 'No saved avatars yet'}</div>
        <DemoBadge />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <button
          onClick={onCreateNew}
          className="group relative p-5 rounded-2xl border-2 border-dashed border-violet-500/40 bg-gradient-to-br from-violet-500/10 to-fuchsia-500/5 hover:from-violet-500/20 hover:to-fuchsia-500/10 transition-colors text-left min-h-[172px] flex flex-col justify-between"
          data-testid="avatar-studio-library-create-new-btn"
        >
          <div className="flex items-center gap-2 text-violet-200">
            <div className="w-9 h-9 rounded-full bg-violet-500/20 border border-violet-500/40 flex items-center justify-center">
              <Plus className="w-5 h-5" />
            </div>
            <span className="text-sm font-bold uppercase tracking-wider">Create new avatar</span>
          </div>
          <div>
            <div className="text-lg font-bold text-white">Start a fresh AI clone</div>
            <div className="text-xs text-slate-400 mt-1">Pick a type → upload → generate in ~30s.</div>
          </div>
        </button>

        {clones.map(c => (
          <button
            key={c.id}
            onClick={() => onPickAvatar(c)}
            className="group p-5 rounded-2xl border border-white/10 bg-white/[0.03] hover:border-violet-500/50 hover:bg-white/[0.05] transition-colors text-left min-h-[172px] flex flex-col justify-between"
            data-testid={`avatar-studio-library-card-${c.id}`}
          >
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white font-bold text-sm">
                {(c.clone_name || '?').slice(0, 1).toUpperCase()}
              </div>
              <StatusPill status={c.status} />
            </div>
            <div>
              <div className="text-base font-bold text-white truncate">{c.clone_name || 'Untitled avatar'}</div>
              <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-2">
                <Video className="w-3 h-3" />
                {c.clone_type || 'self'}
                <span className="text-slate-700">·</span>
                <Clock className="w-3 h-3" />
                {c.created_at ? new Date(c.created_at).toLocaleDateString() : ''}
              </div>
            </div>
          </button>
        ))}
      </div>

      {!hasClones && (
        <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] text-xs text-slate-400 flex items-start gap-2"
             data-testid="avatar-studio-library-empty-hint">
          <Sparkles className="w-4 h-4 text-violet-300 mt-0.5 shrink-0" />
          <div>
            Tip: you can test the full 5-step wizard right now. The first avatar you generate is a <span className="text-amber-300 font-semibold">demo / simulated output</span> — real AI rendering unlocks in Phase 2.
          </div>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }) {
  const map = {
    ready:            { c: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30', l: 'Ready' },
    training:         { c: 'bg-violet-500/15 text-violet-300 border-violet-500/30', l: 'Training' },
    consent_pending:  { c: 'bg-amber-500/15 text-amber-300 border-amber-500/30', l: 'Consent needed' },
    consent_review:   { c: 'bg-amber-500/15 text-amber-300 border-amber-500/30', l: 'Review' },
    consent_approved: { c: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30', l: 'Approved' },
    consent_rejected: { c: 'bg-rose-500/15 text-rose-300 border-rose-500/30', l: 'Rejected' },
    disabled:         { c: 'bg-rose-500/15 text-rose-300 border-rose-500/30', l: 'Disabled' },
  };
  const m = map[status] || { c: 'bg-white/10 text-slate-300 border-white/15', l: status || 'draft' };
  return (
    <span className={`ml-auto text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border ${m.c}`}>
      {m.l}
    </span>
  );
}
