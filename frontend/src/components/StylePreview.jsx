import React, { useState, useEffect } from 'react';
import { Eye, X, Loader2, Sparkles, Lock } from 'lucide-react';
import { Button } from './ui/button';

// Style preview images - AI-generated examples for each style
const STYLE_PREVIEWS = {
  // Action Styles
  bold_superhero: {
    preview: 'https://placehold.co/400x400/6b21a8/ffffff?text=Bold+Hero',
    description: 'Dynamic heroic poses with bold colors and strong lines'
  },
  dark_vigilante: {
    preview: 'https://placehold.co/400x400/1e293b/ffffff?text=Dark+Vigilante',
    description: 'Moody shadows and noir atmosphere'
  },
  retro_action: {
    preview: 'https://placehold.co/400x400/dc2626/ffffff?text=Retro+Action',
    description: 'Classic 80s halftone comic aesthetic'
  },
  dynamic_battle: {
    preview: 'https://placehold.co/400x400/f97316/ffffff?text=Battle+Scene',
    description: 'High-energy motion lines and impact effects'
  },
  // Fun Styles
  cartoon_fun: {
    preview: 'https://placehold.co/400x400/22c55e/ffffff?text=Cartoon+Fun',
    description: 'Bright cheerful cartoon with playful features'
  },
  meme_expression: {
    preview: 'https://placehold.co/400x400/eab308/000000?text=Meme+Face',
    description: 'Exaggerated funny expressions, meme-worthy'
  },
  comic_caricature: {
    preview: 'https://placehold.co/400x400/ec4899/ffffff?text=Caricature',
    description: 'Playful exaggerated features'
  },
  exaggerated_reaction: {
    preview: 'https://placehold.co/400x400/f472b6/ffffff?text=Reaction',
    description: 'Over-the-top emotional reactions'
  },
  // Soft Styles
  romance_comic: {
    preview: 'https://placehold.co/400x400/fda4af/000000?text=Romance',
    description: 'Soft romantic with dreamy atmosphere'
  },
  dreamy_pastel: {
    preview: 'https://placehold.co/400x400/fbcfe8/000000?text=Pastel',
    description: 'Gentle pastel color palette'
  },
  soft_manga: {
    preview: 'https://placehold.co/400x400/c084fc/ffffff?text=Soft+Manga',
    description: 'Gentle manga-inspired with expressive eyes'
  },
  cute_chibi: {
    preview: 'https://placehold.co/400x400/fb7185/ffffff?text=Chibi',
    description: 'Adorable mini character with big head'
  },
  // Fantasy Styles
  magical_fantasy: {
    preview: 'https://placehold.co/400x400/8b5cf6/ffffff?text=Magical',
    description: 'Enchanted atmosphere with mystical elements'
  },
  medieval_adventure: {
    preview: 'https://placehold.co/400x400/78350f/ffffff?text=Medieval',
    description: 'Knights, castles, and fantasy adventures'
  },
  scifi_neon: {
    preview: 'https://placehold.co/400x400/06b6d4/000000?text=Sci-Fi+Neon',
    description: 'Futuristic neon cyberpunk aesthetic'
  },
  cyberpunk_comic: {
    preview: 'https://placehold.co/400x400/7c3aed/ffffff?text=Cyberpunk',
    description: 'High-tech dystopia with neon lights'
  },
  // Kids Styles
  kids_storybook: {
    preview: 'https://placehold.co/400x400/fbbf24/000000?text=Storybook',
    description: 'Friendly children\'s book illustration'
  },
  friendly_animal: {
    preview: 'https://placehold.co/400x400/84cc16/000000?text=Animals',
    description: 'Cute animal characters, child-safe'
  },
  classroom_comic: {
    preview: 'https://placehold.co/400x400/38bdf8/000000?text=Classroom',
    description: 'School-themed fun illustrations'
  },
  adventure_kids: {
    preview: 'https://placehold.co/400x400/34d399/000000?text=Adventure',
    description: 'Kid-friendly exciting adventures'
  },
  // Minimal Styles
  black_white_ink: {
    preview: 'https://placehold.co/400x400/1f2937/ffffff?text=B%26W+Ink',
    description: 'Classic black and white ink illustration'
  },
  sketch_outline: {
    preview: 'https://placehold.co/400x400/94a3b8/000000?text=Sketch',
    description: 'Hand-drawn pencil sketch look'
  },
  noir_comic: {
    preview: 'https://placehold.co/400x400/0f172a/ffffff?text=Noir',
    description: 'Film noir with dramatic shadows'
  },
  vintage_print: {
    preview: 'https://placehold.co/400x400/78716c/ffffff?text=Vintage',
    description: 'Retro newspaper print aesthetic'
  }
};

/**
 * StylePreviewModal - Shows a preview of what the style looks like
 */
export function StylePreviewModal({ isOpen, onClose, style, styleName }) {
  if (!isOpen) return null;
  
  const preview = STYLE_PREVIEWS[style] || {
    preview: 'https://placehold.co/400x400/6b21a8/ffffff?text=Preview',
    description: 'Original comic style'
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="bg-slate-800 border border-slate-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white">Style Preview</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <div className="rounded-xl overflow-hidden mb-4 border border-slate-600">
          <img 
            src={preview.preview} 
            alt={styleName} 
            className="w-full aspect-square object-cover"
          />
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

/**
 * StyleCard with Preview Button
 */
export function StyleCardWithPreview({ 
  style, 
  selected, 
  onSelect, 
  isPremium = false, 
  hasAccess = true,
  onPreview
}) {
  const locked = isPremium && !hasAccess;
  const preview = STYLE_PREVIEWS[style.id];

  return (
    <div
      className={`relative p-3 rounded-xl border-2 text-left transition-all duration-300 cursor-pointer group ${
        selected
          ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
          : locked
          ? 'border-slate-700 bg-slate-800/30 opacity-80'
          : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
      }`}
      onClick={() => !locked && onSelect(style.id)}
    >
      {/* Preview Image Thumbnail */}
      {preview && (
        <div className="relative mb-2 rounded-lg overflow-hidden">
          <img 
            src={preview.preview} 
            alt={style.name}
            className={`w-full aspect-video object-cover ${locked ? 'grayscale' : ''}`}
          />
          
          {/* Preview Button Overlay */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPreview(style);
            }}
            className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity"
          >
            <Eye className="w-6 h-6 text-white" />
          </button>
        </div>
      )}
      
      {/* Style Name */}
      <p className={`font-medium text-sm truncate ${selected ? 'text-white' : 'text-slate-300'}`}>
        {style.name}
      </p>
      
      {/* Premium Lock Overlay */}
      {locked && (
        <>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] rounded-xl flex flex-col items-center justify-center z-10">
            <Lock className="w-6 h-6 text-yellow-400 mb-1" />
            <span className="text-xs font-bold text-yellow-400">PRO</span>
          </div>
          <div className="absolute top-1 right-1 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full z-20">
            PRO
          </div>
        </>
      )}
    </div>
  );
}

/**
 * StyleGrid with Preview support
 */
export default function StylePreviewGrid({ 
  styles, 
  selectedStyle, 
  onSelect, 
  userPlan = 'free',
  premiumStyles = [] 
}) {
  const [previewStyle, setPreviewStyle] = useState(null);
  
  const hasProAccess = ['creator', 'pro', 'studio'].includes(userPlan);

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {styles.map((style) => {
          const isPremium = premiumStyles.includes(style.id);
          
          return (
            <StyleCardWithPreview
              key={style.id}
              style={style}
              selected={selectedStyle === style.id}
              onSelect={onSelect}
              isPremium={isPremium}
              hasAccess={hasProAccess}
              onPreview={() => setPreviewStyle(style)}
            />
          );
        })}
      </div>
      
      <StylePreviewModal
        isOpen={!!previewStyle}
        onClose={() => setPreviewStyle(null)}
        style={previewStyle?.id}
        styleName={previewStyle?.name}
      />
    </>
  );
}

// Export preview data for use elsewhere
export { STYLE_PREVIEWS };
