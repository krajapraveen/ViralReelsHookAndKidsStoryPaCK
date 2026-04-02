import React, { useRef, useCallback } from 'react';
import { Check, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react';
import { trackEvent } from '../../utils/analytics';

const PREVIEW_STYLES = [
  { id: 'cartoon_fun', name: 'Cartoon', badge: 'Most Popular', desc: 'Bright, friendly, universal appeal', gradient: 'from-yellow-500 to-amber-400', badgeColor: 'bg-amber-500/20 text-amber-300' },
  { id: 'soft_manga', name: 'Manga', badge: 'Trending', desc: 'Sharp lines, action-focused style', gradient: 'from-indigo-500 to-violet-400', badgeColor: 'bg-violet-500/20 text-violet-300' },
  { id: 'cute_chibi', name: 'Chibi', badge: 'Best for Kids', desc: 'Cute, playful, highly shareable', gradient: 'from-emerald-500 to-teal-400', badgeColor: 'bg-emerald-500/20 text-emerald-300' },
  { id: 'kids_storybook', name: 'Storybook', badge: 'Warm & Magical', desc: 'Soft illustrated fairy-tale look', gradient: 'from-sky-500 to-cyan-400', badgeColor: 'bg-sky-500/20 text-sky-300' },
  { id: 'bold_superhero', name: 'Bold Hero', badge: 'Best for Action', desc: 'High-energy superhero aesthetic', gradient: 'from-red-600 to-orange-500', badgeColor: 'bg-red-500/20 text-red-300' },
  { id: 'retro_action', name: 'Retro Pop', badge: 'Classic Vibe', desc: 'Vintage pop-art comic panels', gradient: 'from-pink-500 to-rose-400', badgeColor: 'bg-pink-500/20 text-pink-300' },
  { id: 'noir_comic', name: 'Noir', badge: 'Dramatic', desc: 'Dark shadows, cinematic mood', gradient: 'from-slate-600 to-zinc-500', badgeColor: 'bg-slate-500/20 text-slate-300' },
  { id: 'cyberpunk_comic', name: 'Cyberpunk', badge: 'Futuristic', desc: 'Neon-lit sci-fi world', gradient: 'from-cyan-500 to-blue-600', badgeColor: 'bg-cyan-500/20 text-cyan-300' },
];

export function StylePreviewStrip({ selectedStyle, onStyleSelect, generatorRef }) {
  const scrollRef = useRef(null);

  const handleSelect = useCallback((styleId) => {
    onStyleSelect(styleId);
    trackEvent('comic_preview_style_click', { style: styleId, source: 'preview_strip' });

    // Scroll toward generator if ref exists
    if (generatorRef?.current) {
      setTimeout(() => {
        generatorRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
    }
  }, [onStyleSelect, generatorRef]);

  const scroll = (dir) => {
    if (!scrollRef.current) return;
    const amount = dir === 'left' ? -260 : 260;
    scrollRef.current.scrollBy({ left: amount, behavior: 'smooth' });
  };

  return (
    <div className="relative" data-testid="style-preview-strip">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-white">Pick a style to get started</h3>
          <p className="text-[11px] text-slate-500 mt-0.5">Click any style to select it instantly</p>
        </div>
        <div className="hidden sm:flex gap-1">
          <button
            onClick={() => scroll('left')}
            className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
            aria-label="Scroll left"
            data-testid="strip-scroll-left"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => scroll('right')}
            className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
            aria-label="Scroll right"
            data-testid="strip-scroll-right"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent snap-x snap-mandatory -mx-1 px-1"
        style={{ WebkitOverflowScrolling: 'touch' }}
        data-testid="strip-scroll-container"
      >
        {PREVIEW_STYLES.map((s) => {
          const isSelected = selectedStyle === s.id;
          return (
            <button
              key={s.id}
              onClick={() => handleSelect(s.id)}
              className={`flex-shrink-0 snap-start w-[140px] sm:w-[155px] rounded-xl border-2 transition-all duration-200 text-left group overflow-hidden ${
                isSelected
                  ? 'border-purple-500 ring-2 ring-purple-500/30 scale-[1.03] bg-slate-800/90'
                  : 'border-slate-700/60 hover:border-slate-500 bg-slate-900/60 hover:bg-slate-800/60'
              }`}
              data-testid={`preview-${s.id}`}
            >
              {/* Gradient visual */}
              <div className={`relative h-20 bg-gradient-to-br ${s.gradient} flex items-center justify-center`}>
                {isSelected && (
                  <div className="absolute inset-0 bg-purple-900/30 flex items-center justify-center">
                    <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                  </div>
                )}
                {!isSelected && (
                  <Sparkles className="w-6 h-6 text-white/40 group-hover:text-white/70 transition-colors" />
                )}
              </div>

              {/* Info */}
              <div className="p-2.5">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-xs font-bold text-white truncate">{s.name}</span>
                </div>
                <span className={`inline-block text-[9px] font-semibold px-1.5 py-0.5 rounded-full mb-1 ${s.badgeColor}`}>
                  {s.badge}
                </span>
                <p className="text-[10px] text-slate-500 leading-tight line-clamp-2">{s.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
