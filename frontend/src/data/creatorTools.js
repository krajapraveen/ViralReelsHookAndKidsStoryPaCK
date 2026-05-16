/**
 * Single source of truth for the platform's Creator Tools list.
 * Consumed by:
 *   • pages/Dashboard.js   — authenticated FeaturesGrid
 *   • pages/Landing.js     — public Creator Tools section (hero-adjacent)
 *
 * Adding/removing a tool here updates BOTH surfaces. Don't duplicate.
 *
 * Field shape:
 *   name        : display label
 *   desc        : 1-line benefit copy
 *   icon        : key in ICON_MAP (lucide-react)
 *   path        : authenticated route (used directly when logged in)
 *   key         : stable identifier (used for data-testid + react keys)
 *   gradient    : tailwind gradient classes for icon tile
 *   score       : sort weight on Dashboard (higher = first)
 *   badge       : optional pill text ("FREE · TESTING", "NEW", etc.)
 */
export const DEFAULT_FEATURES = [
  { name: 'Story Video', desc: 'Turn ideas into cinematic stories', icon: 'Film', path: '/app/story-video-studio', key: 'story-video-studio', gradient: 'from-indigo-500 to-blue-700', score: 100 },
  { name: 'Story Series', desc: 'Multi-episode sagas with memory', icon: 'BookOpen', path: '/app/story-series', key: 'story-series', gradient: 'from-purple-500 to-fuchsia-700', score: 90 },
  { name: 'My Movie Trailer', desc: 'Upload photos → 20-60s personalized AI trailer', icon: 'Camera', path: '/app/photo-trailer', key: 'photo-trailer', gradient: 'from-violet-500 to-fuchsia-700', score: 80, badge: 'NEW' },
  { name: 'Character Memory', desc: 'Persistent characters across stories', icon: 'User', path: '/app/characters', key: 'characters', gradient: 'from-cyan-500 to-blue-700', score: 0 },
  { name: 'Reel Generator', desc: 'Viral short-form video reels', icon: 'Play', path: '/app/reels', key: 'reels', gradient: 'from-rose-500 to-pink-700', score: 0 },
  { name: 'Photo to Comic', desc: 'Transform photos into comic panels', icon: 'Camera', path: '/app/photo-to-comic', key: 'photo-to-comic', gradient: 'from-amber-500 to-orange-700', score: 0 },
  { name: 'Comic Storybook', desc: 'Panel-by-panel illustrated stories', icon: 'Palette', path: '/app/comic-storybook', key: 'comic-storybook', gradient: 'from-emerald-500 to-green-700', score: 0 },
  { name: 'Bedtime Stories', desc: 'Narrated sleep tales with visuals', icon: 'Star', path: '/app/bedtime-stories', key: 'bedtime-stories', gradient: 'from-indigo-500 to-purple-700', score: 0 },
  { name: 'Reaction GIF', desc: 'Photo-to-reaction GIF in seconds', icon: 'ImageIcon', path: '/app/gif-maker', key: 'gif-maker', gradient: 'from-pink-500 to-rose-700', score: 0 },
  { name: 'Brand Story', desc: 'Cinematic brand narratives', icon: 'Megaphone', path: '/app/brand-story-builder', key: 'brand-story-builder', gradient: 'from-teal-500 to-cyan-700', score: 0 },
  { name: 'Daily Viral Ideas', desc: 'AI-generated trending prompts', icon: 'Lightbulb', path: '/app/daily-viral-ideas', key: 'daily-viral-ideas', gradient: 'from-amber-500 to-red-700', score: 0 },
];
