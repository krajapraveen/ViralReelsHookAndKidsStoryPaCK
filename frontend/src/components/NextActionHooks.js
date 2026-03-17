import React from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Play, RefreshCw, Film, BookOpen, Sparkles, Palette,
  MessageCircle, Zap, ArrowRight, Mic, Image, PenTool
} from 'lucide-react';

// ─── TOOL-SPECIFIC HOOK CONFIGS ────────────────────────────────────────────
const HOOK_CONFIGS = {
  'gif-maker': {
    title: "Don't stop here",
    subtitle: 'Your GIF is just the beginning.',
    hooks: [
      { id: 'remix-emotion', label: 'Try Different Reaction', desc: 'Same photo, new emotion', icon: RefreshCw, color: 'from-pink-500 to-rose-500', target: 'gif-maker', modifier: 'Create with a completely different emotion and expression' },
      { id: 'to-comic', label: 'Turn Into Comic', desc: 'Transform into comic art', icon: PenTool, color: 'from-violet-500 to-purple-500', target: 'photo-to-comic', modifier: 'Convert this reaction into a comic panel' },
      { id: 'to-video', label: 'Create Story Video', desc: 'Animate your character', icon: Film, color: 'from-blue-500 to-cyan-500', target: 'story-video-studio', modifier: 'Create an animated story video featuring this character' },
      { id: 'to-reel', label: 'Make a Reel Script', desc: 'Go viral with this', icon: Sparkles, color: 'from-amber-500 to-orange-500', target: 'reels', modifier: 'Write a viral reel script using this reaction' },
    ],
  },
  'reels': {
    title: "Your script is ready. Now amplify it.",
    subtitle: 'Turn words into visuals, stories, and more.',
    hooks: [
      { id: 'to-video', label: 'Generate Video', desc: 'Turn this script into a video', icon: Film, color: 'from-blue-500 to-indigo-500', target: 'story-video-studio', modifier: 'Create an animated story video from this reel script' },
      { id: 'remix-tone', label: 'Rewrite Different Tone', desc: 'Funny, dramatic, bold...', icon: RefreshCw, color: 'from-pink-500 to-rose-500', target: 'reels', modifier: 'Rewrite this in a completely different tone' },
      { id: 'expand-story', label: 'Expand Into Story', desc: 'Full narrative from your hook', icon: BookOpen, color: 'from-emerald-500 to-teal-500', target: 'story-video-studio', modifier: 'Expand this reel hook into a full animated story' },
      { id: 'to-comic', label: 'Turn Into Comic', desc: 'Visualize as comic panels', icon: PenTool, color: 'from-violet-500 to-purple-500', target: 'comic-storybook', modifier: 'Convert this script into a comic storybook' },
    ],
  },
  'comic-storybook': {
    title: "Your comic is alive. Keep going.",
    subtitle: 'Add chapters, change styles, or go multi-format.',
    hooks: [
      { id: 'next-chapter', label: 'Add Next Chapter', desc: 'Continue the adventure', icon: Play, color: 'from-blue-500 to-indigo-500', target: 'comic-storybook', modifier: 'Continue this comic story with a new exciting chapter' },
      { id: 'remix-style', label: 'Change Art Style', desc: 'Same story, new look', icon: Palette, color: 'from-pink-500 to-rose-500', target: 'comic-storybook', modifier: 'Recreate this comic in a completely different art style' },
      { id: 'to-video', label: 'Convert to Video', desc: 'Animate your comic', icon: Film, color: 'from-emerald-500 to-teal-500', target: 'story-video-studio', modifier: 'Turn this comic storybook into an animated story video' },
      { id: 'to-bedtime', label: 'Make Bedtime Story', desc: 'Narrated version', icon: Mic, color: 'from-amber-500 to-orange-500', target: 'bedtime-story-builder', modifier: 'Convert this comic into a narrated bedtime story' },
    ],
  },
  'bedtime-story-builder': {
    title: "Story told. What's next?",
    subtitle: 'Visualize it, continue it, or share it.',
    hooks: [
      { id: 'to-video', label: 'Convert to Video', desc: 'Animated story video', icon: Film, color: 'from-blue-500 to-indigo-500', target: 'story-video-studio', modifier: 'Turn this bedtime story into an animated video with illustrations' },
      { id: 'next-episode', label: 'Next Episode', desc: 'Continue the adventure', icon: Play, color: 'from-emerald-500 to-teal-500', target: 'bedtime-story-builder', modifier: 'Continue this bedtime story with a new exciting episode' },
      { id: 'remix-tone', label: 'Change Narration', desc: 'Different voice & tone', icon: RefreshCw, color: 'from-pink-500 to-rose-500', target: 'bedtime-story-builder', modifier: 'Retell this story with a completely different narration style' },
      { id: 'to-comic', label: 'Create Illustrations', desc: 'Comic storybook version', icon: Image, color: 'from-violet-500 to-purple-500', target: 'comic-storybook', modifier: 'Create illustrated comic panels from this bedtime story' },
    ],
  },
  'caption-rewriter': {
    title: "Captions ready. Now make them work.",
    subtitle: 'Generate content from your best caption.',
    hooks: [
      { id: 'to-reel', label: 'Generate Reel Script', desc: 'Turn caption into video script', icon: Film, color: 'from-blue-500 to-indigo-500', target: 'reels', modifier: 'Create a viral reel script based on this caption' },
      { id: 'remix-tone', label: 'Rewrite Again', desc: 'Try a different tone', icon: RefreshCw, color: 'from-pink-500 to-rose-500', target: 'caption-rewriter', modifier: 'Rewrite in a completely different tone' },
      { id: 'expand-script', label: 'Expand to Full Script', desc: 'Long-form content', icon: BookOpen, color: 'from-emerald-500 to-teal-500', target: 'reels', modifier: 'Expand this caption into a full reel script with scenes' },
      { id: 'to-video', label: 'Create Story Video', desc: 'Animate this message', icon: Sparkles, color: 'from-violet-500 to-purple-500', target: 'story-video-studio', modifier: 'Create an animated story video from this caption concept' },
    ],
  },
  'brand-story-builder': {
    title: "Brand story done. Now distribute.",
    subtitle: 'Turn your story into multi-format content.',
    hooks: [
      { id: 'to-reel', label: 'Create Reel Script', desc: 'Social video from brand story', icon: Film, color: 'from-blue-500 to-indigo-500', target: 'reels', modifier: 'Convert this brand story into a viral social media reel script' },
      { id: 'to-video', label: 'Generate Video Ad', desc: 'Animated brand video', icon: Sparkles, color: 'from-emerald-500 to-teal-500', target: 'story-video-studio', modifier: 'Create an animated brand story video from this content' },
      { id: 'expand-copy', label: 'Expand Website Copy', desc: 'Full landing page content', icon: BookOpen, color: 'from-pink-500 to-rose-500', target: 'brand-story-builder', modifier: 'Expand this into comprehensive website copy and landing page content' },
      { id: 'social-series', label: 'Create Social Series', desc: 'Multi-post campaign', icon: MessageCircle, color: 'from-violet-500 to-purple-500', target: 'reels', modifier: 'Create a series of social media posts from this brand story' },
    ],
  },
  'daily-viral-ideas': {
    title: "Got the idea. Now execute.",
    subtitle: 'Turn trending ideas into real content.',
    hooks: [
      { id: 'to-reel', label: 'Generate Reel Script', desc: 'Script from this idea', icon: Film, color: 'from-blue-500 to-indigo-500', target: 'reels', modifier: 'Write a viral reel script based on this trending idea' },
      { id: 'to-video', label: 'Create Story Video', desc: 'Animated content', icon: Sparkles, color: 'from-emerald-500 to-teal-500', target: 'story-video-studio', modifier: 'Create an animated story video from this viral idea' },
      { id: 'to-caption', label: 'Generate Captions', desc: 'Ready-to-post captions', icon: PenTool, color: 'from-pink-500 to-rose-500', target: 'caption-rewriter', modifier: 'Generate multiple caption variations from this viral idea' },
      { id: 'to-comic', label: 'Make a Comic', desc: 'Visual storytelling', icon: Image, color: 'from-violet-500 to-purple-500', target: 'comic-storybook', modifier: 'Create a comic storybook based on this trending idea' },
    ],
  },
};

const TOOL_ROUTES = {
  'story-video-studio': '/app/story-video-studio',
  'reels': '/app/reels',
  'photo-to-comic': '/app/photo-to-comic',
  'gif-maker': '/app/gif-maker',
  'stories': '/app/stories',
  'bedtime-story-builder': '/app/bedtime-story-builder',
  'comic-storybook': '/app/comic-storybook',
  'coloring-book': '/app/coloring-book',
  'caption-rewriter': '/app/caption-rewriter',
  'brand-story-builder': '/app/brand-story-builder',
  'daily-viral-ideas': '/app/daily-viral-ideas',
};

export default function NextActionHooks({ toolType, prompt = '', settings = {}, generationId = null, title = '' }) {
  const navigate = useNavigate();
  const config = HOOK_CONFIGS[toolType];
  if (!config) return null;

  const handleHook = (hook) => {
    const route = TOOL_ROUTES[hook.target] || `/app/${hook.target}`;
    const finalPrompt = hook.modifier ? `${prompt}. ${hook.modifier}` : prompt;

    // Store remix context for the target tool
    const stateData = {
      prompt: finalPrompt,
      timestamp: Date.now(),
      source_tool: toolType,
      remixFrom: {
        tool: toolType,
        prompt,
        settings,
        title,
        parentId: generationId,
      },
    };
    localStorage.setItem('remix_data', JSON.stringify(stateData));

    navigate(route, { state: stateData });
    toast.success(`Creating: ${hook.label}...`);
  };

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-slate-900/90 to-slate-950/90 overflow-hidden" data-testid="next-action-hooks">
      {/* Header */}
      <div className="px-5 pt-5 pb-3">
        <div className="flex items-center gap-2 mb-1">
          <Zap className="w-4 h-4 text-amber-400" />
          <h3 className="text-base font-bold text-white" data-testid="hooks-title">{config.title}</h3>
        </div>
        <p className="text-sm text-slate-400">{config.subtitle}</p>
      </div>

      {/* Action Grid — PRIMARY CTA ZONE */}
      <div className="px-5 pb-5 grid grid-cols-2 gap-3" data-testid="hooks-grid">
        {config.hooks.map((hook) => (
          <button
            key={hook.id}
            onClick={() => handleHook(hook)}
            className="group relative rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] p-4 text-left transition-all duration-200 hover:scale-[1.02] hover:border-white/[0.12]"
            data-testid={`hook-${hook.id}`}
          >
            {/* Gradient accent bar */}
            <div className={`absolute top-0 left-0 right-0 h-[2px] rounded-t-xl bg-gradient-to-r ${hook.color} opacity-40 group-hover:opacity-100 transition-opacity`} />

            <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${hook.color} flex items-center justify-center mb-3 shadow-lg`}>
              <hook.icon className="w-4 h-4 text-white" />
            </div>
            <p className="text-sm font-semibold text-white group-hover:text-white/90 mb-0.5">{hook.label}</p>
            <p className="text-[11px] text-slate-500 group-hover:text-slate-400">{hook.desc}</p>
            <ArrowRight className="absolute top-4 right-4 w-4 h-4 text-white/0 group-hover:text-white/40 transition-all" />
          </button>
        ))}
      </div>
    </div>
  );
}
