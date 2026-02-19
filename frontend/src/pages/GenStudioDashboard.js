import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Sparkles, Image, Video, Palette, Scissors, Clock, 
  ArrowLeft, Coins, History, Zap, Star, TrendingUp,
  ChevronRight, Play, Download, Wallet, AlertCircle,
  CheckCircle, XCircle, Loader2, RefreshCw
} from 'lucide-react';
import api, { walletAPI } from '../utils/api';

export default function GenStudioDashboard() {
  const [wallet, setWallet] = useState({ balanceCredits: 0, reservedCredits: 0, availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  const [dashboardData, setDashboardData] = useState(null);
  const [activeJobs, setActiveJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
    // Poll for active jobs
    const interval = setInterval(fetchActiveJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [walletRes, pricingRes, dashboardRes] = await Promise.all([
        walletAPI.getWallet(),
        walletAPI.getPricing(),
        api.get('/api/genstudio/dashboard')
      ]);
      setWallet(walletRes.data);
      setPricing(pricingRes.data.pricing);
      setDashboardData(dashboardRes.data);
      await fetchActiveJobs();
    } catch (error) {
      toast.error('Failed to load GenStudio dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveJobs = async () => {
    try {
      const response = await walletAPI.listJobs({ limit: 10 });
      const active = response.data.jobs.filter(j => 
        ['QUEUED', 'RUNNING'].includes(j.status)
      );
      setActiveJobs(active);
    } catch (error) {
      console.error('Failed to fetch active jobs');
    }
  };

  const tools = [
    {
      id: 'text-to-image',
      name: 'Text → Image',
      description: 'Generate stunning images from text prompts',
      icon: Image,
      color: 'from-purple-500 to-pink-500',
      costKey: 'TEXT_TO_IMAGE',
      path: '/app/gen-studio/text-to-image'
    },
    {
      id: 'text-to-video',
      name: 'Text → Video',
      description: 'Create videos from text with Sora 2',
      icon: Video,
      color: 'from-blue-500 to-cyan-500',
      costKey: 'TEXT_TO_VIDEO',
      path: '/app/gen-studio/text-to-video'
    },
    {
      id: 'image-to-video',
      name: 'Image → Video',
      description: 'Animate your images with AI motion',
      icon: Play,
      color: 'from-green-500 to-emerald-500',
      costKey: 'IMAGE_TO_VIDEO',
      path: '/app/gen-studio/image-to-video'
    },
    {
      id: 'style-profiles',
      name: 'Brand Style Profiles',
      description: 'Create consistent brand aesthetics',
      icon: Palette,
      color: 'from-orange-500 to-amber-500',
      costKey: 'STYLE_PROFILE_CREATE',
      path: '/app/gen-studio/style-profiles'
    },
    {
      id: 'video-remix',
      name: 'Video Remix',
      description: 'Remix videos with new styles & prompts',
      icon: Scissors,
      color: 'from-red-500 to-rose-500',
      costKey: 'VIDEO_REMIX',
      path: '/app/gen-studio/video-remix'
    }
  ];

  const getJobStatusIcon = (status) => {
    switch (status) {
      case 'QUEUED': return <Clock className="w-4 h-4 text-yellow-400" />;
      case 'RUNNING': return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      case 'SUCCEEDED': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'FAILED': return <XCircle className="w-4 h-4 text-red-400" />;
      default: return <AlertCircle className="w-4 h-4 text-slate-400" />;
    }
  };

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
              {/* Wallet Display */}
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2" data-testid="wallet-balance">
                <Wallet className="w-4 h-4 text-purple-400" />
                <div className="flex flex-col">
                  <span className="font-bold text-white text-sm">{wallet.availableCredits}</span>
                  <span className="text-xs text-slate-500">available</span>
                </div>
                {wallet.reservedCredits > 0 && (
                  <div className="border-l border-slate-600 pl-2 ml-2">
                    <span className="text-xs text-yellow-400">{wallet.reservedCredits} reserved</span>
                  </div>
                )}
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
        {/* Active Jobs Alert */}
        {activeJobs.length > 0 && (
          <div className="mb-6 bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-blue-300 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Active Jobs ({activeJobs.length})
              </h3>
              <Button variant="ghost" size="sm" onClick={fetchActiveJobs} className="text-blue-300">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
            <div className="grid gap-2">
              {activeJobs.map(job => (
                <div key={job.id} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-3">
                    {getJobStatusIcon(job.status)}
                    <div>
                      <p className="text-sm text-white">{job.jobType.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-slate-400">{job.status} - {job.progress || 0}%</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{job.costCredits} credits</span>
                    <Link to={`/app/gen-studio/history`}>
                      <Button variant="ghost" size="sm" className="text-slate-400">View</Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

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
                <Wallet className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{wallet.balanceCredits}</p>
                <p className="text-xs text-slate-400">Total Credits</p>
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
          {tools.map((tool) => {
            const cost = pricing[tool.costKey]?.baseCredits || 10;
            const canAfford = wallet.availableCredits >= cost;
            
            return (
              <div 
                key={tool.id}
                className={`relative bg-slate-900/50 border rounded-2xl p-6 transition-all duration-300 ${
                  canAfford 
                    ? 'border-slate-800 hover:border-slate-700 cursor-pointer hover:scale-[1.02]' 
                    : 'border-red-500/30 opacity-70'
                }`}
                onClick={() => canAfford && navigate(tool.path)}
                data-testid={`tool-${tool.id}`}
              >
                {!canAfford && (
                  <div className="absolute top-4 right-4 bg-red-500/20 text-red-400 text-xs font-medium px-2 py-1 rounded-full flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    Low Credits
                  </div>
                )}
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${tool.color} flex items-center justify-center mb-4`}>
                  <tool.icon className="w-7 h-7 text-white" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">{tool.name}</h4>
                <p className="text-sm text-slate-400 mb-4">{tool.description}</p>
                <div className="flex items-center justify-between">
                  <span className={`text-sm flex items-center gap-1 ${canAfford ? 'text-slate-500' : 'text-red-400'}`}>
                    <Coins className="w-4 h-4 text-yellow-500" />
                    {cost} credits
                  </span>
                  {canAfford && (
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  )}
                </div>
              </div>
            );
          })}
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
                    <p className="text-xs text-slate-400 truncate">{job.type?.replace('_', ' → ') || job.jobType?.replace('_', ' → ')}</p>
                    <p className={`text-xs font-medium ${job.status === 'completed' || job.status === 'SUCCEEDED' ? 'text-green-400' : job.status === 'failed' || job.status === 'FAILED' ? 'text-red-400' : 'text-yellow-400'}`}>
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
