import React, { useState } from 'react';
import { Eye, X, Sparkles, Lock } from 'lucide-react';
import { Button } from './ui/button';

// Style previews with CSS-based colored backgrounds — no external URLs, no placehold.co
const STYLE_PREVIEWS = {
  // Action Styles
  bold_superhero: { bg: 'from-purple-800 to-indigo-900', text: 'Bold Hero', description: 'Dynamic heroic poses with bold colors and strong lines' },
  dark_vigilante: { bg: 'from-slate-800 to-gray-900', text: 'Dark Vigilante', description: 'Moody shadows and noir atmosphere' },
  retro_action: { bg: 'from-red-600 to-orange-700', text: 'Retro Action', description: 'Classic 80s halftone comic aesthetic' },
  dynamic_battle: { bg: 'from-orange-500 to-red-600', text: 'Battle Scene', description: 'High-energy motion lines and impact effects' },
  // Fun Styles
  cartoon_fun: { bg: 'from-green-500 to-emerald-600', text: 'Cartoon Fun', description: 'Bright cheerful cartoon with playful features' },
  meme_expression: { bg: 'from-yellow-500 to-amber-600', text: 'Meme Face', description: 'Exaggerated funny expressions, meme-worthy' },
  comic_caricature: { bg: 'from-pink-500 to-rose-600', text: 'Caricature', description: 'Playful exaggerated features' },
  exaggerated_reaction: { bg: 'from-pink-400 to-fuchsia-600', text: 'Reaction', description: 'Over-the-top emotional reactions' },
  // Soft Styles
  romance_comic: { bg: 'from-rose-300 to-pink-400', text: 'Romance', description: 'Soft romantic with dreamy atmosphere' },
  dreamy_pastel: { bg: 'from-pink-200 to-purple-300', text: 'Pastel', description: 'Gentle pastel color palette' },
  soft_manga: { bg: 'from-violet-400 to-purple-500', text: 'Soft Manga', description: 'Gentle manga-inspired with expressive eyes' },
  cute_chibi: { bg: 'from-rose-400 to-pink-500', text: 'Chibi', description: 'Adorable mini character with big head' },
  // Fantasy Styles
  magical_fantasy: { bg: 'from-violet-600 to-purple-700', text: 'Magical', description: 'Enchanted atmosphere with mystical elements' },
  medieval_adventure: { bg: 'from-amber-900 to-yellow-900', text: 'Medieval', description: 'Knights, castles, and fantasy adventures' },
  scifi_neon: { bg: 'from-cyan-500 to-blue-600', text: 'Sci-Fi Neon', description: 'Futuristic neon cyberpunk aesthetic' },
  cyberpunk_comic: { bg: 'from-violet-600 to-indigo-700', text: 'Cyberpunk', description: 'High-tech dystopia with neon lights' },
  // Kids Styles
  kids_storybook: { bg: 'from-amber-400 to-yellow-500', text: 'Storybook', description: "Friendly children's book illustration" },
  friendly_animal: { bg: 'from-lime-500 to-green-600', text: 'Animals', description: 'Cute animal characters, child-safe' },
  classroom_comic: { bg: 'from-sky-400 to-blue-500', text: 'Classroom', description: 'School-themed fun illustrations' },
  adventure_kids: { bg: 'from-emerald-400 to-teal-500', text: 'Adventure', description: 'Kid-friendly exciting adventures' },
  // Minimal Styles
  black_white_ink: { bg: 'from-gray-800 to-slate-900', text: 'B&W Ink', description: 'Classic black and white ink illustration' },
  sketch_outline: { bg: 'from-slate-400 to-gray-500', text: 'Sketch', description: 'Hand-drawn pencil sketch look' },
  noir_comic: { bg: 'from-gray-900 to-black', text: 'Noir', description: 'Film noir with dramatic shadows' },
  vintage_print: { bg: 'from-stone-500 to-stone-600', text: 'Vintage', description: 'Retro newspaper print aesthetic' },
};

const defaultPreview = { bg: 'from-purple-800 to-indigo-900', text: 'Preview', description: 'Original comic style' };

/** CSS-based style preview swatch — no external image URLs */
function StyleSwatch({ preview, alt, className, aspectRatio = 'aspect-square' }) {
  const p = preview || defaultPreview;
  return (
    <div className={`bg-gradient-to-br ${p.bg} flex items-center justify-center ${aspectRatio} ${className || ''}`}>
      <span className="text-white/80 font-bold text-sm text-center drop-shadow-md px-2">{p.text || alt}</span>
    </div>
  );
}

/** StylePreviewModal - Shows a preview of what the style looks like */
export function StylePreviewModal({ isOpen, onClose, style, styleName }) {
  if (!isOpen) return null;
  const preview = STYLE_PREVIEWS[style] || defaultPreview;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white">Style Preview</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="w-6 h-6" /></button>
        </div>
        <div className="rounded-xl overflow-hidden mb-4 border border-slate-600">
          <StyleSwatch preview={preview} alt={styleName} aspectRatio="aspect-square" />
        </div>
        <h4 className="font-semibold text-white mb-2">{styleName}</h4>
        <p className="text-slate-400 text-sm mb-4">{preview.description}</p>
        <Button onClick={onClose} className="w-full bg-purple-600 hover:bg-purple-700">
          <Sparkles className="w-4 h-4 mr-2" /> Select This Style
        </Button>
      </div>
    </div>
  );
}

/** StyleCard with Preview Button */
export function StyleCardWithPreview({ style, selected, onSelect, isPremium = false, hasAccess = true, onPreview }) {
  const locked = isPremium && !hasAccess;
  const preview = STYLE_PREVIEWS[style.id];

  return (
    <div
      className={`relative p-3 rounded-xl border-2 text-left transition-all duration-300 cursor-pointer group ${
        selected ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
          : locked ? 'border-slate-700 bg-slate-800/30 opacity-80'
          : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
      }`}
      onClick={() => !locked && onSelect(style.id)}
    >
      {preview && (
        <div className="relative mb-2 rounded-lg overflow-hidden">
          <StyleSwatch preview={preview} alt={style.name} aspectRatio="aspect-video" className={locked ? 'grayscale' : ''} />
          <button
            onClick={(e) => { e.stopPropagation(); onPreview(style); }}
            className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity"
          >
            <Eye className="w-6 h-6 text-white" />
          </button>
        </div>
      )}
      <p className={`font-medium text-sm truncate ${selected ? 'text-white' : 'text-slate-300'}`}>{style.name}</p>
      {locked && (
        <>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] rounded-xl flex flex-col items-center justify-center z-10">
            <Lock className="w-6 h-6 text-yellow-400 mb-1" />
            <span className="text-xs font-bold text-yellow-400">PRO</span>
          </div>
          <div className="absolute top-1 right-1 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full z-20">PRO</div>
        </>
      )}
    </div>
  );
}

/** StyleGrid with Preview support */
export default function StylePreviewGrid({ styles, selectedStyle, onSelect, userPlan = 'free', premiumStyles = [] }) {
  const [previewStyle, setPreviewStyle] = useState(null);
  const hasProAccess = ['creator', 'pro', 'studio'].includes(userPlan);

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {styles.map((style) => (
          <StyleCardWithPreview
            key={style.id}
            style={style}
            selected={selectedStyle === style.id}
            onSelect={onSelect}
            isPremium={premiumStyles.includes(style.id)}
            hasAccess={hasProAccess}
            onPreview={() => setPreviewStyle(style)}
          />
        ))}
      </div>
      <StylePreviewModal isOpen={!!previewStyle} onClose={() => setPreviewStyle(null)} style={previewStyle?.id} styleName={previewStyle?.name} />
    </>
  );
}

export { STYLE_PREVIEWS };
