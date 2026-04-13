import React from 'react';
import { ArrowRight } from 'lucide-react';

/**
 * FounderAuthorityBlock — Trust + authority section.
 * Placed below hero to increase conversion through founder credibility.
 */
export default function FounderAuthorityBlock({ onExplore }) {
  return (
    <section className="w-full flex justify-center px-4 py-12" data-testid="founder-authority-block">
      <div className="max-w-5xl w-full bg-gradient-to-br from-[#0d0d1a] to-[#111125] border border-white/[0.06] rounded-2xl p-8 shadow-xl">
        <div className="grid md:grid-cols-2 gap-8 items-center">

          {/* LEFT — Photo + Tags */}
          <div className="flex flex-col items-center text-center">
            <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-violet-500/60 shadow-[0_0_30px_-5px_rgba(139,92,246,0.3)]">
              <img
                src="/founder-avatar.png"
                alt="Raja Praveen Katta"
                className="w-full h-full object-cover"
                data-testid="founder-avatar"
              />
            </div>

            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <span className="px-3 py-1 text-xs font-medium bg-violet-600/80 text-white rounded-full">AI Builder</span>
              <span className="px-3 py-1 text-xs font-medium bg-blue-600/80 text-white rounded-full">3D Creator</span>
              <span className="px-3 py-1 text-xs font-medium bg-emerald-600/80 text-white rounded-full">Novel Writer</span>
              <span className="px-3 py-1 text-xs font-medium bg-slate-600/80 text-white rounded-full">Cloud Architect</span>
            </div>
          </div>

          {/* RIGHT — Bio + CTA */}
          <div>
            <p className="text-[11px] font-bold text-violet-400/60 uppercase tracking-widest mb-2" data-testid="founder-label">
              Built by the creator of Visionary Suite
            </p>

            <h2 className="text-2xl font-black text-white" data-testid="founder-name">
              Raja Praveen Katta
            </h2>

            <p className="text-sm text-slate-300 mt-1">
              Software Engineer & Cloud Architect &middot; AI Innovator &middot; 3D Cartoon Movie Creator &middot; Novel Writer
            </p>

            <h3 className="text-base font-semibold text-violet-300 mt-4 leading-relaxed">
              Turning ideas into stories, stories into visuals, and visuals into viral content — powered by AI.
            </h3>

            <p className="text-sm text-slate-400 mt-4 leading-relaxed">
              Visionary Suite is built by Raja Praveen Katta, combining deep engineering expertise with cinematic storytelling. By integrating AI systems, cloud architecture, 3D creation, and writing, this platform goes far beyond ordinary content tools.
            </p>

            <p className="text-sm text-slate-400 mt-2 leading-relaxed">
              From animated kids' stories to viral reels, Visionary Suite enables anyone to create professional-quality content quickly and effortlessly.
            </p>

            <div className="flex flex-wrap gap-2 mt-4">
              <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-slate-400">Built for creators</span>
              <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-slate-400">Story + technology</span>
              <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-slate-400">Designed for viral content</span>
              <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-slate-400">No advanced skills needed</span>
            </div>

            <button
              onClick={onExplore}
              className="mt-6 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 rounded-lg text-white font-semibold text-sm flex items-center gap-2 transition-colors"
              data-testid="founder-explore-btn"
            >
              Explore Visionary Suite <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </div>
      </div>
    </section>
  );
}
