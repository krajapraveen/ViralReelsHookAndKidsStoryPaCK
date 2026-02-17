import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Sparkles, Image, Video, Palette, Scissors, Clock, 
  ArrowLeft, Coins, History, Zap, Star, TrendingUp,
  ChevronRight, Play, Download
} from 'lucide-react';
import api from '../utils/api';

export default function GenStudioDashboard() {
  const [credits, setCredits] = useState(0);
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await api.get('/api/genstudio/dashboard');
      setDashboardData(response.data);
      setCredits(response.data.credits);
    } catch (error) {
      toast.error('Failed to load GenStudio dashboard');
    } finally {
      setLoading(false);
    }
  };

  const tools = [
    {
      id: 'text-to-image',
      name: 'Text → Image',
      description: 'Generate stunning images from text prompts',
      icon: Image,
      color: 'from-purple-500 to-pink-500',
      cost: 10,
      path: '/app/gen-studio/text-to-image'
    },
    {
      id: 'text-to-video',
      name: 'Text → Video',
      description: 'Create videos from text with Sora 2',
      icon: Video,
      color: 'from-blue-500 to-cyan-500',
      cost: 10,
      path: '/app/gen-studio/text-to-video'
    },
    {
      id: 'image-to-video',
      name: 'Image → Video',
      description: 'Animate your images with AI motion',
      icon: Play,
      color: 'from-green-500 to-emerald-500',
      cost: 10,
      path: '/app/gen-studio/image-to-video'
    },
    {
      id: 'style-profiles',
      name: 'Brand Style Profiles',
      description: 'Create consistent brand aesthetics',
      icon: Palette,
      color: 'from-orange-500 to-amber-500',
      cost: 20,
      path: '/app/gen-studio/style-profiles'
    },
    {
      id: 'video-remix',
      name: 'Video Remix',
      description: 'Remix videos with new styles & prompts',
      icon: Scissors,
      color: 'from-red-500 to-rose-500',
      cost: 12,
      path: '/app/gen-studio/video-remix'
    }
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">GenStudio</h1>
                  <p className="text-xs text-slate-400">AI Generation Suite</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <Link to="/app/gen-studio/history" className="text-slate-400 hover:text-white flex items-center gap-2 text-sm">
                <History className="w-4 h-4" />
                History
              </Link>
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <span className="font-bold text-white">{credits}</span>
                <span className="text-slate-400 text-sm">credits</span>
              </div>
              <Link to="/app/billing">
                <Button size="sm" className="bg-purple-600 hover:bg-purple-700">
                  Buy Credits
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-4">
            Create with <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">AI Power</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Generate stunning images, videos, and more with our AI-powered tools. 
            Files auto-deleted after <span className="text-red-400 font-semibold">3 MINUTES</span> for security.
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{dashboardData?.stats?.totalGenerations || 0}</p>
                <p className="text-xs text-slate-400">Total Generations</p>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-pink-500/20 flex items-center justify-center">
                <Image className="w-5 h-5 text-pink-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{dashboardData?.stats?.totalImages || 0}</p>
                <p className="text-xs text-slate-400">Images Created</p>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <Video className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{dashboardData?.stats?.totalVideos || 0}</p>
                <p className="text-xs text-slate-400">Videos Created</p>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Palette className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{dashboardData?.styleProfiles?.length || 0}</p>
                <p className="text-xs text-slate-400">Style Profiles</p>
              </div>
            </div>
          </div>
        </div>

        {/* AI Tools Grid */}
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Star className="w-5 h-5 text-yellow-500" />
          AI Generation Tools
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {tools.map((tool) => (
            <div 
              key={tool.id}
              className={`relative bg-slate-900/50 border border-slate-800 rounded-2xl p-6 hover:border-slate-700 transition-all duration-300 ${tool.comingSoon ? 'opacity-60' : 'cursor-pointer hover:scale-[1.02]'}`}
              onClick={() => !tool.comingSoon && navigate(tool.path)}
            >
              {tool.comingSoon && (
                <div className="absolute top-4 right-4 bg-yellow-500/20 text-yellow-400 text-xs font-medium px-2 py-1 rounded-full">
                  Coming Soon
                </div>
              )}
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${tool.color} flex items-center justify-center mb-4`}>
                <tool.icon className="w-7 h-7 text-white" />
              </div>
              <h4 className="text-lg font-bold text-white mb-2">{tool.name}</h4>
              <p className="text-sm text-slate-400 mb-4">{tool.description}</p>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-500 flex items-center gap-1">
                  <Coins className="w-4 h-4 text-yellow-500" />
                  {tool.cost} credits
                </span>
                {!tool.comingSoon && (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Quick Templates */}
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-500" />
          Quick Templates
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          {dashboardData?.templates?.slice(0, 8).map((template) => (
            <button
              key={template.id}
              onClick={() => navigate(`/app/gen-studio/text-to-image?template=${template.id}`)}
              className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-left hover:border-purple-500/50 hover:bg-slate-800/50 transition-all"
            >
              <p className="text-sm font-medium text-white mb-1">{template.name}</p>
              <p className="text-xs text-slate-500 capitalize">{template.category}</p>
            </button>
          ))}
        </div>

        {/* Recent Generations */}
        {dashboardData?.recentJobs?.length > 0 && (
          <>
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-500" />
              Recent Generations
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {dashboardData.recentJobs.slice(0, 5).map((job) => (
                <div key={job.id} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                  <div className="aspect-square bg-slate-800 flex items-center justify-center">
                    {job.outputUrls?.[0] ? (
                      <img src={`${process.env.REACT_APP_BACKEND_URL}${job.outputUrls[0]}`} alt="Generated" className="w-full h-full object-cover" />
                    ) : (
                      <Image className="w-8 h-8 text-slate-600" />
                    )}
                  </div>
                  <div className="p-3">
                    <p className="text-xs text-slate-400 truncate">{job.type.replace('_', ' → ')}</p>
                    <p className={`text-xs font-medium ${job.status === 'completed' ? 'text-green-400' : job.status === 'failed' ? 'text-red-400' : 'text-yellow-400'}`}>
                      {job.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Safety Notice */}
        <div className="mt-12 bg-slate-900/30 border border-slate-800 rounded-xl p-6">
          <h4 className="text-sm font-semibold text-white mb-2">⚠️ Content Policy</h4>
          <p className="text-xs text-slate-400">
            GenStudio does not support face swapping, identity cloning, or deepfakes. 
            All generated content must comply with our <Link to="/app/copyright" className="text-purple-400 hover:underline">content policy</Link>. 
            By using GenStudio, you confirm you have rights/consent for all content.
          </p>
        </div>
      </main>
    </div>
  );
}
