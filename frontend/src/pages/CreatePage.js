import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Film, Image, BookOpen, Sparkles, ArrowRight, Zap } from 'lucide-react';
import { Button } from '../components/ui/button';

const TOOLS = [
  {
    id: 'story-to-video',
    title: 'Story to Video',
    description: 'Turn stories into cinematic animated videos with AI narration',
    icon: Film,
    route: '/app/story-video-studio',
    color: 'purple',
    badge: 'Flagship',
  },
  {
    id: 'photo-to-comic',
    title: 'Photo to Comic',
    description: 'Convert photos into stylized comic panels',
    icon: Image,
    route: '/app/comic-storybook',
    color: 'teal',
    badge: null,
  },
  {
    id: 'ai-reels',
    title: 'AI Reels',
    description: 'Create viral short-form videos with AI',
    icon: Zap,
    route: '/app/reel-generator',
    color: 'pink',
    badge: null,
  },
  {
    id: 'kids-story',
    title: 'Kids Story Generator',
    description: 'Generate illustrated bedtime stories for children',
    icon: BookOpen,
    route: '/app/bedtime-story-builder',
    color: 'amber',
    badge: null,
  },
];

const COLOR_MAP = {
  purple: {
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20 hover:border-purple-500/40',
    icon: 'text-purple-400',
    badge: 'bg-purple-500/20 text-purple-300',
    btn: 'bg-purple-600 hover:bg-purple-700',
  },
  teal: {
    bg: 'bg-teal-500/10',
    border: 'border-teal-500/20 hover:border-teal-500/40',
    icon: 'text-teal-400',
    badge: 'bg-teal-500/20 text-teal-300',
    btn: 'bg-teal-600 hover:bg-teal-700',
  },
  pink: {
    bg: 'bg-pink-500/10',
    border: 'border-pink-500/20 hover:border-pink-500/40',
    icon: 'text-pink-400',
    badge: 'bg-pink-500/20 text-pink-300',
    btn: 'bg-pink-600 hover:bg-pink-700',
  },
  amber: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20 hover:border-amber-500/40',
    icon: 'text-amber-400',
    badge: 'bg-amber-500/20 text-amber-300',
    btn: 'bg-amber-600 hover:bg-amber-700',
  },
};

export default function CreatePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="create-page">
      <div className="max-w-4xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 rounded-full px-4 py-1.5 mb-4">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-purple-300 text-sm font-medium">AI Creation Suite</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">Create Something Amazing</h1>
          <p className="text-slate-400 text-base max-w-lg mx-auto">Choose a tool to start your next creation. Each tool uses AI to bring your ideas to life.</p>
        </div>

        {/* Tool Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="tool-grid">
          {TOOLS.map(tool => {
            const colors = COLOR_MAP[tool.color];
            const Icon = tool.icon;
            return (
              <div
                key={tool.id}
                className={`relative ${colors.bg} border ${colors.border} rounded-2xl p-6 transition-all cursor-pointer group`}
                onClick={() => navigate(tool.route)}
                data-testid={`tool-card-${tool.id}`}
              >
                {tool.badge && (
                  <span className={`absolute top-4 right-4 ${colors.badge} text-[10px] font-semibold px-2 py-0.5 rounded-full`}>
                    {tool.badge}
                  </span>
                )}
                <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center mb-4`}>
                  <Icon className={`w-6 h-6 ${colors.icon}`} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{tool.title}</h3>
                <p className="text-slate-400 text-sm mb-5">{tool.description}</p>
                <Button className={`${colors.btn} text-sm group-hover:gap-3 transition-all`} data-testid={`start-${tool.id}`}>
                  Start Creating <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
