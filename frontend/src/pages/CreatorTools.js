import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  Sparkles, Calendar, LayoutGrid, Hash, Type, RefreshCw, 
  BookOpen, FileText, TrendingUp, Loader2, ArrowLeft, 
  Coins, Download, Copy, Check, LogOut, Wand2, Video, MessageSquare
} from 'lucide-react';
import api from '../utils/api';
import HelpGuide from '../components/HelpGuide';

export default function CreatorTools() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('calendar');
  const [copied, setCopied] = useState(null);
  const navigate = useNavigate();

  // Calendar state
  const [calendarNiche, setCalendarNiche] = useState('business');
  const [calendarDays, setCalendarDays] = useState(30);
  const [includeScripts, setIncludeScripts] = useState(false);
  const [calendarResult, setCalendarResult] = useState(null);

  // Carousel state
  const [carouselTopic, setCarouselTopic] = useState('');
  const [carouselNiche, setCarouselNiche] = useState('general');
  const [carouselSlides, setCarouselSlides] = useState(7);
  const [carouselResult, setCarouselResult] = useState(null);

  // Hashtag state
  const [hashtagNiche, setHashtagNiche] = useState('business');
  const [hashtagResult, setHashtagResult] = useState(null);

  // Thumbnail state
  const [thumbnailTopic, setThumbnailTopic] = useState('');
  const [thumbnailResult, setThumbnailResult] = useState(null);

  // Trending state
  const [trendingTopics, setTrendingTopics] = useState([]);
  const [trendingNiche, setTrendingNiche] = useState('general');
  const [trendingLoading, setTrendingLoading] = useState(false);

  // Convert state
  const [userReels, setUserReels] = useState([]);
  const [userStories, setUserStories] = useState([]);
  const [convertLoading, setConvertLoading] = useState(false);
  const [convertResult, setConvertResult] = useState(null);
  const [selectedReelId, setSelectedReelId] = useState('');
  const [selectedStoryId, setSelectedStoryId] = useState('');

  const niches = ['luxury', 'relationship', 'health', 'motivation', 'parenting', 'business', 'travel', 'food'];
  const trendingNiches = ['general', 'fitness', 'business', 'travel', 'food', 'tech'];

  useEffect(() => {
    fetchCredits();
    fetchTrending(trendingNiche);
    fetchUserContent();
  }, []);

  const fetchUserContent = async () => {
    try {
      const [reelsRes, storiesRes] = await Promise.all([
        api.get('/api/convert/user-reels?limit=10'),
        api.get('/api/convert/user-stories?limit=10')
      ]);
      setUserReels(reelsRes.data.reels || []);
      setUserStories(storiesRes.data.stories || []);
    } catch (error) {
      console.error('Failed to fetch user content');
    }
  };

  const fetchCredits = async () => {
    try {
      const response = await api.get('/api/wallet/me');
      setCredits(response.data.balanceCredits || response.data.balance || 0);
    } catch (error) {
      console.error('Failed to fetch credits');
    }
  };

  const fetchTrending = async (niche = 'general') => {
    setTrendingLoading(true);
    try {
      const response = await api.get(`/api/creator-tools/trending?niche=${niche}&limit=8`);
      if (response.data.success && response.data.topics) {
        // Map backend response to frontend expected format
        const mappedTopics = response.data.topics.map((t, index) => ({
          id: index + 1,
          title: t.topic,
          description: `Explore trending content about ${t.topic.toLowerCase()}`,
          hook_preview: t.hook,
          niche: response.data.niche,
          suggested_angle: `Engagement level: ${t.engagement}`,
          engagement: t.engagement
        }));
        setTrendingTopics(mappedTopics);
      }
    } catch (error) {
      console.error('Failed to fetch trending topics:', error);
      toast.error('Failed to load trending topics');
    } finally {
      setTrendingLoading(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success('Copied to clipboard!');
    setTimeout(() => setCopied(null), 2000);
  };

  // Generate 30-Day Calendar
  const generateCalendar = async () => {
    const cost = includeScripts ? 25 : 10;
    if (credits < cost) {
      toast.error(`Need ${cost} credits for this feature`);
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post(`/api/creator-tools/content-calendar?niche=${calendarNiche}&days=${calendarDays}&include_full_scripts=${includeScripts}`);
      setCalendarResult(response.data);
      fetchCredits(); // Refresh credits
      toast.success('Calendar generated!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate calendar');
    } finally {
      setLoading(false);
    }
  };

  // Generate Carousel
  const generateCarousel = async () => {
    if (!carouselTopic.trim()) {
      toast.error('Please enter a topic');
      return;
    }
    if (credits < 3) {
      toast.error('Need 3 credits for carousel');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post(`/api/creator-tools/carousel?topic=${encodeURIComponent(carouselTopic)}&niche=${carouselNiche}&slides=${carouselSlides}`);
      setCarouselResult(response.data);
      fetchCredits(); // Refresh credits
      toast.success('Carousel generated!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate carousel');
    } finally {
      setLoading(false);
    }
  };

  // Get Hashtags
  const getHashtags = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/creator-tools/hashtags/${hashtagNiche}`);
      setHashtagResult(response.data);
      toast.success('Hashtags loaded!');
    } catch (error) {
      toast.error('Failed to load hashtags');
    } finally {
      setLoading(false);
    }
  };

  // Generate Thumbnails
  const generateThumbnails = async () => {
    if (!thumbnailTopic.trim()) {
      toast.error('Please enter a topic');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post(`/api/creator-tools/thumbnail-text?topic=${encodeURIComponent(thumbnailTopic)}`);
      setThumbnailResult(response.data);
      toast.success('Thumbnail text generated!');
    } catch (error) {
      toast.error('Failed to generate thumbnails');
    } finally {
      setLoading(false);
    }
  };

  // Convert Functions
  const convertReelToCarousel = async () => {
    if (credits < 10) {
      toast.error('Need 10 credits for this conversion');
      return;
    }
    
    setConvertLoading(true);
    try {
      const url = selectedReelId 
        ? `/api/convert/reel-to-carousel?generation_id=${selectedReelId}`
        : '/api/convert/reel-to-carousel?use_recent=true';
      const response = await api.post(url);
      setConvertResult({ type: 'carousel', data: response.data });
      fetchCredits();
      toast.success(response.data.message || 'Converted to carousel!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Conversion failed');
    } finally {
      setConvertLoading(false);
    }
  };

  const convertReelToYoutube = async () => {
    if (credits < 10) {
      toast.error('Need 10 credits for this conversion');
      return;
    }
    
    setConvertLoading(true);
    try {
      const url = selectedReelId 
        ? `/api/convert/reel-to-youtube?generation_id=${selectedReelId}`
        : '/api/convert/reel-to-youtube?use_recent=true';
      const response = await api.post(url);
      setConvertResult({ type: 'youtube', data: response.data });
      fetchCredits();
      toast.success(response.data.message || 'Expanded to YouTube script!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Conversion failed');
    } finally {
      setConvertLoading(false);
    }
  };

  const convertStoryToReel = async () => {
    if (credits < 10) {
      toast.error('Need 10 credits for this conversion');
      return;
    }
    
    setConvertLoading(true);
    try {
      const url = selectedStoryId 
        ? `/api/convert/story-to-reel?generation_id=${selectedStoryId}`
        : '/api/convert/story-to-reel?use_recent=true';
      const response = await api.post(url);
      setConvertResult({ type: 'reel', data: response.data });
      fetchCredits();
      toast.success(response.data.message || 'Converted to reel!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Conversion failed');
    } finally {
      setConvertLoading(false);
    }
  };

  const convertStoryToQuote = async () => {
    setConvertLoading(true);
    try {
      const url = selectedStoryId 
        ? `/api/convert/story-to-quote?generation_id=${selectedStoryId}`
        : '/api/convert/story-to-quote?use_recent=true';
      const response = await api.post(url);
      setConvertResult({ type: 'quotes', data: response.data });
      toast.success(response.data.message || 'Quotes extracted!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Extraction failed');
    } finally {
      setConvertLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Wand2 className="w-6 h-6 text-purple-400" />
              <span className="text-xl font-bold text-white">Creator Tools</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-purple-500/20 border border-purple-500/30 rounded-full px-4 py-2">
              <Coins className="w-4 h-4 text-purple-400" />
              <span className="font-semibold text-purple-300">{credits} Credits</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="text-slate-400 hover:text-white" data-testid="creator-tools-logout">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid grid-cols-6 lg:grid-cols-6 mb-8 bg-slate-800/50 border border-slate-700" data-testid="creator-tools-tabs" data-tour="creator-tools-tabs">
            <TabsTrigger value="calendar" className="flex items-center gap-2 text-slate-400 data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/20" data-testid="tab-calendar">
              <Calendar className="w-4 h-4" />
              <span className="hidden sm:inline">Calendar</span>
            </TabsTrigger>
            <TabsTrigger value="carousel" className="flex items-center gap-2 text-slate-400 data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/20" data-testid="tab-carousel">
              <LayoutGrid className="w-4 h-4" />
              <span className="hidden sm:inline">Carousel</span>
            </TabsTrigger>
            <TabsTrigger value="hashtags" className="flex items-center gap-2 text-slate-400 data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/20" data-testid="tab-hashtags">
              <Hash className="w-4 h-4" />
              <span className="hidden sm:inline">Hashtags</span>
            </TabsTrigger>
            <TabsTrigger value="thumbnails" className="flex items-center gap-2 text-slate-400 data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/20" data-testid="tab-thumbnails">
              <Type className="w-4 h-4" />
              <span className="hidden sm:inline">Thumbnails</span>
            </TabsTrigger>
            <TabsTrigger value="trending" className="flex items-center gap-2 text-slate-400 data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/20" data-testid="tab-trending">
              <TrendingUp className="w-4 h-4" />
              <span className="hidden sm:inline">Trending</span>
            </TabsTrigger>
            <TabsTrigger value="convert" className="flex items-center gap-2 text-slate-400 data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/20" data-testid="tab-convert">
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">Convert</span>
            </TabsTrigger>
          </TabsList>

          {/* 30-Day Calendar Tab */}
          <TabsContent value="calendar">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                  <Calendar className="w-6 h-6 text-purple-400" />
                  30-Day Content Calendar
                </h2>
                <p className="text-slate-400 mb-6">Generate a full month of content ideas</p>
                
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Select Niche</Label>
                    <Select value={calendarNiche} onValueChange={setCalendarNiche}>
                      <SelectTrigger className="bg-slate-800 border-slate-700 text-white" data-testid="calendar-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        {niches.map(n => (
                          <SelectItem key={n} value={n} className="text-white hover:bg-slate-700">{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label className="text-slate-300">Number of Days</Label>
                    <Select value={calendarDays.toString()} onValueChange={(v) => setCalendarDays(parseInt(v))}>
                      <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="7" className="text-white hover:bg-slate-700">7 days</SelectItem>
                        <SelectItem value="14" className="text-white hover:bg-slate-700">14 days</SelectItem>
                        <SelectItem value="30" className="text-white hover:bg-slate-700">30 days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      id="includeScripts" 
                      checked={includeScripts}
                      onChange={(e) => setIncludeScripts(e.target.checked)}
                      className="rounded"
                    />
                    <Label htmlFor="includeScripts">Include full scripts (+15 credits)</Label>
                  </div>
                  
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-purple-700">
                      <Coins className="w-4 h-4" />
                      <span className="font-medium">Cost: {includeScripts ? 25 : 10} credits</span>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={generateCalendar} 
                    disabled={loading}
                    className="w-full bg-purple-500 hover:bg-purple-600"
                    data-testid="generate-calendar-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Calendar className="w-4 h-4 mr-2" />}
                    Generate Calendar
                  </Button>
                </div>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 max-h-[600px] overflow-y-auto backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Your Content Calendar</h3>
                {!calendarResult ? (
                  <div className="text-center py-12 text-slate-400">
                    <Calendar className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Your calendar will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-3" data-testid="calendar-result">
                    {calendarResult.calendar.map((day, index) => (
                      <div key={index} className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-purple-400">{day.date} ({day.dayOfWeek})</span>
                          <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded border border-purple-500/30">{day.contentType}</span>
                        </div>
                        <p className="text-sm font-medium text-white mb-2">{day.suggestedTopic}</p>
                        {day.inspirationalTip && (
                          <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg p-3 mb-2 border border-purple-500/20">
                            <p className="text-sm text-purple-200 italic">💡 {day.inspirationalTip}</p>
                          </div>
                        )}
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span>📱 {day.niche}</span>
                          <span>⏰ {day.bestPostingTime}</span>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(`${day.suggestedTopic}\n\n${day.inspirationalTip || ''}`, `day-${index}`)} className="text-slate-400 hover:text-white">
                            {copied === `day-${index}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Carousel Tab */}
          <TabsContent value="carousel">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                  <LayoutGrid className="w-6 h-6 text-blue-400" />
                  Carousel Generator
                </h2>
                <p className="text-slate-400 mb-6">Create engaging carousel posts</p>
                
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Topic</Label>
                    <Input 
                      placeholder="e.g., 5 Morning Habits for Success"
                      value={carouselTopic}
                      onChange={(e) => setCarouselTopic(e.target.value)}
                      className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
                      data-testid="carousel-topic-input"
                    />
                  </div>
                  
                  <div>
                    <Label className="text-slate-300">Niche</Label>
                    <Select value={carouselNiche} onValueChange={setCarouselNiche}>
                      <SelectTrigger className="bg-slate-800 border-slate-700 text-white" data-testid="carousel-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">General</SelectItem>
                        {niches.map(n => (
                          <SelectItem key={n} value={n}>{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>Number of Slides</Label>
                    <Select value={carouselSlides.toString()} onValueChange={(v) => setCarouselSlides(parseInt(v))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[5, 6, 7, 8, 9, 10].map(n => (
                          <SelectItem key={n} value={n.toString()}>{n} slides</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-blue-700">
                      <Coins className="w-4 h-4" />
                      <span className="font-medium">Cost: 3 credits</span>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={generateCarousel} 
                    disabled={loading}
                    className="w-full bg-blue-500 hover:bg-blue-600"
                    data-testid="generate-carousel-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <LayoutGrid className="w-4 h-4 mr-2" />}
                    Generate Carousel
                  </Button>
                </div>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 max-h-[600px] overflow-y-auto backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Your Carousel Preview</h3>
                {!carouselResult ? (
                  <div className="space-y-3">
                    {/* Preview placeholder slides */}
                    {Array.from({ length: carouselSlides }).map((_, index) => (
                      <div key={index} className={`rounded-lg p-4 border ${
                        index === 0 ? 'bg-blue-500/10 border-blue-500/30' : 
                        index === carouselSlides - 1 ? 'bg-green-500/10 border-green-500/30' : 
                        'bg-slate-700/30 border-slate-600'
                      }`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-slate-300">Slide {index + 1}</span>
                          <span className={`text-xs uppercase px-2 py-1 rounded ${
                            index === 0 ? 'bg-blue-500/20 text-blue-300' : 
                            index === carouselSlides - 1 ? 'bg-green-500/20 text-green-300' : 
                            'bg-slate-600 text-slate-300'
                          }`}>
                            {index === 0 ? 'COVER' : index === carouselSlides - 1 ? 'CTA' : 'CONTENT'}
                          </span>
                        </div>
                        <p className="text-slate-500 italic text-sm">
                          {index === 0 
                            ? 'Hook headline will appear here...' 
                            : index === carouselSlides - 1 
                              ? 'Call-to-action will appear here...' 
                              : 'Content slide text will appear here...'}
                        </p>
                      </div>
                    ))}
                    <div className="text-center py-4 text-slate-400">
                      <LayoutGrid className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                      <p className="text-sm">Enter a topic and click "Generate Carousel"</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4" data-testid="carousel-result">
                    {carouselResult.carousel.slides.map((slide) => (
                      <div key={slide.slideNumber} className={`rounded-lg p-4 border ${
                        slide.type === 'cover' ? 'bg-blue-500/10 border-blue-500/30' : 
                        slide.type === 'cta' ? 'bg-green-500/10 border-green-500/30' : 
                        'bg-slate-700/30 border-slate-600'
                      }`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-white">Slide {slide.slideNumber}</span>
                          <span className={`text-xs uppercase px-2 py-1 rounded ${
                            slide.type === 'cover' ? 'bg-blue-500/20 text-blue-300' : 
                            slide.type === 'cta' ? 'bg-green-500/20 text-green-300' : 
                            'bg-slate-600 text-slate-300'
                          }`}>{slide.type}</span>
                        </div>
                        <p className="font-medium text-white">{slide.headline}</p>
                        {slide.subheadline && <p className="text-sm text-slate-400 mt-1">{slide.subheadline}</p>}
                        {slide.body && <p className="text-sm text-slate-300 mt-1">{slide.body}</p>}
                        {slide.cta && <p className="text-sm text-green-400 mt-1 font-medium">{slide.cta}</p>}
                        {slide.designTip && <p className="text-xs text-slate-500 mt-2 bg-slate-800/50 p-2 rounded">💡 {slide.designTip}</p>}
                        <Button variant="ghost" size="sm" onClick={() => copyToClipboard(slide.headline + (slide.body ? '\n' + slide.body : ''), `slide-${slide.slideNumber}`)} className="mt-2 text-slate-400 hover:text-white">
                          {copied === `slide-${slide.slideNumber}` ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                          Copy
                        </Button>
                      </div>
                    ))}
                    
                    {/* Tips Section */}
                    {carouselResult.tips && carouselResult.tips.length > 0 && (
                      <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 mt-4">
                        <h4 className="font-bold text-white mb-2">Pro Tips</h4>
                        <ul className="text-sm text-slate-300 space-y-1">
                          {carouselResult.tips.map((tip, i) => (
                            <li key={i}>• {tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Hashtags Tab */}
          <TabsContent value="hashtags">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                  <Hash className="w-6 h-6 text-green-400" />
                  Hashtag Bank
                </h2>
                <p className="text-slate-400 mb-6">Curated hashtags by niche - FREE</p>
                
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Select Niche</Label>
                    <Select value={hashtagNiche} onValueChange={setHashtagNiche}>
                      <SelectTrigger className="bg-slate-800 border-slate-700 text-white" data-testid="hashtag-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        {niches.map(n => (
                          <SelectItem key={n} value={n} className="text-white hover:bg-slate-700">{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-400">
                      <Sparkles className="w-4 h-4" />
                      <span className="font-medium">FREE - No credits required</span>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={getHashtags} 
                    disabled={loading}
                    className="w-full bg-green-500 hover:bg-green-600"
                    data-testid="get-hashtags-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Hash className="w-4 h-4 mr-2" />}
                    Get Hashtags
                  </Button>
                </div>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Hashtag Results</h3>
                {!hashtagResult ? (
                  <div className="text-center py-12 text-slate-400">
                    <Hash className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Select a niche and click Get Hashtags</p>
                  </div>
                ) : (
                  <div className="space-y-4" data-testid="hashtag-result">
                    <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-bold text-white capitalize">{hashtagResult.niche} Hashtags</h4>
                        <span className="text-sm text-green-400 bg-green-500/20 px-2 py-1 rounded border border-green-500/30">{hashtagResult.count} tags</span>
                      </div>
                      <div className="flex flex-wrap gap-2 mb-3">
                        {hashtagResult.hashtags.map((tag, i) => (
                          <span key={i} className="text-sm bg-slate-800 text-slate-300 border border-slate-600 px-2 py-1 rounded hover:bg-slate-700 cursor-pointer transition-colors" onClick={() => copyToClipboard(tag, `tag-${i}`)}>{tag}</span>
                        ))}
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard(hashtagResult.hashtags.join(' '), 'all-hashtags')} className="text-slate-400 hover:text-white">
                        {copied === 'all-hashtags' ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                        Copy All Hashtags
                      </Button>
                    </div>
                    <p className="text-sm text-slate-400 text-center mt-4 bg-slate-700/30 rounded-lg p-3 border border-slate-600">💡 {hashtagResult.tip}</p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Thumbnails Tab */}
          <TabsContent value="thumbnails">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                  <Type className="w-6 h-6 text-orange-400" />
                  Thumbnail Text Generator
                </h2>
                <p className="text-slate-400 mb-6">Generate attention-grabbing thumbnail text - FREE</p>
                
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Topic/Subject</Label>
                    <Input 
                      placeholder="e.g., productivity, weight loss, money"
                      value={thumbnailTopic}
                      onChange={(e) => setThumbnailTopic(e.target.value)}
                      className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
                      data-testid="thumbnail-topic-input"
                    />
                  </div>
                  
                  <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-orange-400">
                      <Sparkles className="w-4 h-4" />
                      <span className="font-medium">FREE - No credits required</span>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={generateThumbnails} 
                    disabled={loading}
                    className="w-full bg-orange-500 hover:bg-orange-600"
                    data-testid="generate-thumbnails-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Type className="w-4 h-4 mr-2" />}
                    Generate Thumbnail Text
                  </Button>
                </div>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Thumbnail Options</h3>
                {!thumbnailResult ? (
                  <div className="text-center py-12 text-slate-400">
                    <Type className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Enter a topic and generate thumbnail text</p>
                  </div>
                ) : (
                  <div className="space-y-4" data-testid="thumbnail-result">
                    {Object.entries(thumbnailResult.thumbnails).map(([style, texts]) => (
                      <div key={style} className={`rounded-lg p-4 border ${
                        style === 'emotional' ? 'bg-red-500/10 border-red-500/30' :
                        style === 'curiosity' ? 'bg-yellow-500/10 border-yellow-500/30' :
                        style === 'action' ? 'bg-blue-500/10 border-blue-500/30' :
                        'bg-purple-500/10 border-purple-500/30'
                      }`}>
                        <h4 className="font-bold text-white capitalize mb-2">{style}</h4>
                        <div className="space-y-2">
                          {texts.map((text, i) => (
                            <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded px-3 py-2">
                              <span className="font-medium text-white">{text}</span>
                              <Button variant="ghost" size="sm" onClick={() => copyToClipboard(text, `${style}-${i}`)} className="text-slate-400 hover:text-white">
                                {copied === `${style}-${i}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Trending Tab */}
          <TabsContent value="trending">
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-pink-400" />
                    Weekly Trending Topics
                  </h2>
                  <p className="text-slate-400">Stay updated with what's trending this week</p>
                </div>
                <div className="flex items-center gap-3">
                  <Select value={trendingNiche} onValueChange={(v) => { setTrendingNiche(v); fetchTrending(v); }}>
                    <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white" data-testid="trending-niche-select">
                      <SelectValue placeholder="Select niche" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      {trendingNiches.map(n => (
                        <SelectItem key={n} value={n} className="text-white hover:bg-slate-700">{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => fetchTrending(trendingNiche)}
                    disabled={trendingLoading}
                    className="border-pink-500/30 text-pink-400 hover:bg-pink-500/20"
                    data-testid="refresh-trending-btn"
                  >
                    {trendingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-4 py-2 mb-6 inline-flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400 font-medium">FREE - No credits required</span>
              </div>
              
              {trendingLoading ? (
                <div className="text-center py-12">
                  <Loader2 className="w-12 h-12 mx-auto mb-4 text-pink-400 animate-spin" />
                  <p className="text-slate-400">Loading trending topics...</p>
                </div>
              ) : trendingTopics.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <TrendingUp className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <p>No trending topics available</p>
                  <p className="text-sm mt-2">Try selecting a different niche!</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="trending-result">
                  {trendingTopics.map((topic) => (
                    <div key={topic.id} className="bg-gradient-to-br from-pink-500/10 to-purple-500/10 rounded-lg p-4 border border-pink-500/20 hover:border-pink-500/40 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs bg-pink-500/20 text-pink-300 px-2 py-1 rounded capitalize border border-pink-500/30">{topic.niche}</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          topic.engagement === 'Very High' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                          topic.engagement === 'High' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' :
                          'bg-slate-500/20 text-slate-300 border border-slate-500/30'
                        }`}>{topic.engagement}</span>
                      </div>
                      <h3 className="font-bold text-white mb-2">{topic.title}</h3>
                      <div className="bg-slate-800/50 rounded p-2 text-sm border border-slate-700">
                        <span className="font-medium text-purple-400">Hook: </span>
                        <span className="text-slate-300">{topic.hook_preview}</span>
                      </div>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => copyToClipboard(`${topic.title}\n\n${topic.hook_preview}`, `trending-${topic.id}`)}
                        className="w-full mt-3 text-slate-400 hover:text-white hover:bg-slate-700/50"
                      >
                        {copied === `trending-${topic.id}` ? <Check className="w-3 h-3 mr-2" /> : <Copy className="w-3 h-3 mr-2" />}
                        Copy Topic & Hook
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="mt-6 bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                <h4 className="text-sm font-medium text-slate-300 mb-2">💡 Pro Tips</h4>
                <ul className="text-sm text-slate-400 space-y-1">
                  <li>• Jump on trending topics within 24-48 hours for maximum reach</li>
                  <li>• Add your unique perspective to stand out from the crowd</li>
                  <li>• Use the hook as your opening line in videos</li>
                  <li>• High engagement topics = more algorithm boost</li>
                </ul>
              </div>
            </div>
          </TabsContent>

          {/* Convert Tab */}
          <TabsContent value="convert">
            <div className="grid lg:grid-cols-2 gap-8">
              {/* Left: Conversion Options */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 backdrop-blur-sm">
                <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                  <RefreshCw className="w-6 h-6 text-indigo-400" />
                  Convert Content
                </h2>
                <p className="text-slate-400 mb-6">Repurpose your existing content into new formats</p>
                
                <div className="space-y-6">
                  {/* Reel to Carousel */}
                  <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-xl p-5 border border-indigo-500/30 hover:border-indigo-500/50 transition-all">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-indigo-500/20 rounded-lg">
                        <LayoutGrid className="w-5 h-5 text-indigo-400" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white">Reel → Carousel</h3>
                        <span className="text-xs text-indigo-400 font-medium bg-indigo-500/20 px-2 py-0.5 rounded-full">10 credits</span>
                      </div>
                    </div>
                    <p className="text-sm text-slate-400 mb-4">Convert your viral reel script into a 5-10 slide Instagram carousel with captions</p>
                    <div className="flex items-center gap-2">
                      <Select value={selectedReelId} onValueChange={setSelectedReelId}>
                        <SelectTrigger className="flex-1 bg-slate-800 border-slate-700 text-white" data-testid="convert-reel-carousel-select">
                          <SelectValue placeholder={userReels.length > 0 ? "Select a reel" : "Use most recent reel"} />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="recent" className="text-white hover:bg-slate-700">Use most recent reel</SelectItem>
                          {userReels.map(reel => (
                            <SelectItem key={reel.id} value={reel.id} className="text-white hover:bg-slate-700">
                              {reel.topic || 'Untitled Reel'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button 
                        className="bg-indigo-600 hover:bg-indigo-700" 
                        size="sm" 
                        onClick={convertReelToCarousel}
                        disabled={convertLoading}
                        data-testid="convert-reel-carousel-btn"
                      >
                        {convertLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Convert'}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Reel to YouTube */}
                  <div className="bg-gradient-to-br from-red-500/10 to-orange-500/10 rounded-xl p-5 border border-red-500/30 hover:border-red-500/50 transition-all">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-red-500/20 rounded-lg">
                        <Video className="w-5 h-5 text-red-400" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white">Reel → YouTube</h3>
                        <span className="text-xs text-red-400 font-medium bg-red-500/20 px-2 py-0.5 rounded-full">10 credits</span>
                      </div>
                    </div>
                    <p className="text-sm text-slate-400 mb-4">Expand your 60-second reel into a full 8-10 minute YouTube video script</p>
                    <div className="flex items-center gap-2">
                      <Select value={selectedReelId} onValueChange={setSelectedReelId}>
                        <SelectTrigger className="flex-1 bg-slate-800 border-slate-700 text-white" data-testid="convert-reel-youtube-select">
                          <SelectValue placeholder={userReels.length > 0 ? "Select a reel" : "Use most recent reel"} />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="recent" className="text-white hover:bg-slate-700">Use most recent reel</SelectItem>
                          {userReels.map(reel => (
                            <SelectItem key={reel.id} value={reel.id} className="text-white hover:bg-slate-700">
                              {reel.topic || 'Untitled Reel'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button 
                        className="bg-red-600 hover:bg-red-700" 
                        size="sm" 
                        onClick={convertReelToYoutube}
                        disabled={convertLoading}
                        data-testid="convert-reel-youtube-btn"
                      >
                        {convertLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Expand'}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Story to Reel */}
                  <div className="bg-gradient-to-br from-pink-500/10 to-rose-500/10 rounded-xl p-5 border border-pink-500/30 hover:border-pink-500/50 transition-all">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-pink-500/20 rounded-lg">
                        <BookOpen className="w-5 h-5 text-pink-400" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white">Story → Reel</h3>
                        <span className="text-xs text-pink-400 font-medium bg-pink-500/20 px-2 py-0.5 rounded-full">10 credits</span>
                      </div>
                    </div>
                    <p className="text-sm text-slate-400 mb-4">Convert your kids story into a short parenting reel about the moral/lesson</p>
                    <div className="flex items-center gap-2">
                      <Select value={selectedStoryId} onValueChange={setSelectedStoryId}>
                        <SelectTrigger className="flex-1 bg-slate-800 border-slate-700 text-white" data-testid="convert-story-reel-select">
                          <SelectValue placeholder={userStories.length > 0 ? "Select a story" : "Use most recent story"} />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="recent" className="text-white hover:bg-slate-700">Use most recent story</SelectItem>
                          {userStories.map(story => (
                            <SelectItem key={story.id} value={story.id} className="text-white hover:bg-slate-700">
                              {story.title || 'Untitled Story'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button 
                        className="bg-pink-600 hover:bg-pink-700" 
                        size="sm" 
                        onClick={convertStoryToReel}
                        disabled={convertLoading}
                        data-testid="convert-story-reel-btn"
                      >
                        {convertLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Convert'}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Story to Quote */}
                  <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 rounded-xl p-5 border border-emerald-500/30 hover:border-emerald-500/50 transition-all">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-emerald-500/20 rounded-lg">
                        <MessageSquare className="w-5 h-5 text-emerald-400" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white">Story → Quote</h3>
                        <span className="text-xs text-emerald-400 font-medium bg-emerald-500/20 px-2 py-0.5 rounded-full">FREE</span>
                      </div>
                    </div>
                    <p className="text-sm text-slate-400 mb-4">Generate shareable moral quotes and wisdom from your kids story</p>
                    <div className="flex items-center gap-2">
                      <Select value={selectedStoryId} onValueChange={setSelectedStoryId}>
                        <SelectTrigger className="flex-1 bg-slate-800 border-slate-700 text-white" data-testid="convert-story-quote-select">
                          <SelectValue placeholder={userStories.length > 0 ? "Select a story" : "Use most recent story"} />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="recent" className="text-white hover:bg-slate-700">Use most recent story</SelectItem>
                          {userStories.map(story => (
                            <SelectItem key={story.id} value={story.id} className="text-white hover:bg-slate-700">
                              {story.title || 'Untitled Story'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button 
                        className="bg-emerald-600 hover:bg-emerald-700" 
                        size="sm" 
                        onClick={convertStoryToQuote}
                        disabled={convertLoading}
                        data-testid="convert-story-quote-btn"
                      >
                        {convertLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate'}
                      </Button>
                    </div>
                  </div>
                </div>
                
                {/* Coming Soon */}
                <div className="mt-6 bg-slate-700/30 rounded-lg p-4 border border-dashed border-slate-600">
                  <p className="text-sm text-slate-400 text-center">
                    🚀 Coming Soon: Carousel → Thread, YouTube → Shorts, Story → Audiobook
                  </p>
                </div>
              </div>
              
              {/* Right: Conversion Results */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 max-h-[800px] overflow-y-auto backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Conversion Result</h3>
                {!convertResult ? (
                  <div className="text-center py-12 text-slate-400">
                    <RefreshCw className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Select content and click a conversion button</p>
                    <p className="text-sm mt-2">Results will appear here</p>
                  </div>
                ) : convertResult.type === 'carousel' ? (
                  <div className="space-y-4" data-testid="convert-carousel-result">
                    <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-3">
                      <p className="text-indigo-300 font-medium">{convertResult.data.message}</p>
                    </div>
                    {convertResult.data.carousel?.slides?.map((slide) => (
                      <div key={slide.slideNumber} className={`rounded-lg p-4 border ${
                        slide.type === 'cover' ? 'bg-blue-500/10 border-blue-500/30' : 
                        slide.type === 'cta' ? 'bg-green-500/10 border-green-500/30' : 
                        'bg-slate-700/30 border-slate-600'
                      }`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-white">Slide {slide.slideNumber}</span>
                          <span className={`text-xs uppercase px-2 py-1 rounded ${
                            slide.type === 'cover' ? 'bg-blue-500/20 text-blue-300' : 
                            slide.type === 'cta' ? 'bg-green-500/20 text-green-300' : 
                            'bg-slate-600 text-slate-300'
                          }`}>{slide.type}</span>
                        </div>
                        <p className="font-medium text-white">{slide.headline}</p>
                        {slide.body && <p className="text-sm text-slate-300 mt-1">{slide.body}</p>}
                        {slide.cta && <p className="text-sm text-green-400 mt-1 font-medium">{slide.cta}</p>}
                        <Button variant="ghost" size="sm" onClick={() => copyToClipboard(slide.headline + (slide.body ? '\n' + slide.body : ''), `convert-slide-${slide.slideNumber}`)} className="mt-2 text-slate-400 hover:text-white">
                          {copied === `convert-slide-${slide.slideNumber}` ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                          Copy
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : convertResult.type === 'youtube' ? (
                  <div className="space-y-4" data-testid="convert-youtube-result">
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                      <p className="text-red-300 font-medium">{convertResult.data.message}</p>
                    </div>
                    <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
                      <h4 className="font-bold text-white mb-2">{convertResult.data.youtubeScript?.title}</h4>
                      <p className="text-sm text-slate-400 mb-3">{convertResult.data.youtubeScript?.description}</p>
                      <span className="text-xs bg-red-500/20 text-red-300 px-2 py-1 rounded">{convertResult.data.youtubeScript?.estimatedLength}</span>
                    </div>
                    {convertResult.data.youtubeScript?.sections?.map((section, i) => (
                      <div key={i} className="bg-slate-700/30 rounded-lg p-3 border border-slate-600">
                        <h5 className="font-medium text-white mb-1">{section.section}</h5>
                        <p className="text-sm text-slate-300">{section.content}</p>
                        {section.tips && <p className="text-xs text-slate-500 mt-2">💡 {section.tips}</p>}
                      </div>
                    ))}
                    {convertResult.data.youtubeScript?.mainContent?.map((section, i) => (
                      <div key={`main-${i}`} className="bg-slate-700/30 rounded-lg p-3 border border-slate-600">
                        <h5 className="font-medium text-white mb-1">{section.section}</h5>
                        <p className="text-sm text-slate-300">{section.expandedContent}</p>
                      </div>
                    ))}
                  </div>
                ) : convertResult.type === 'reel' ? (
                  <div className="space-y-4" data-testid="convert-reel-result">
                    <div className="bg-pink-500/10 border border-pink-500/30 rounded-lg p-3">
                      <p className="text-pink-300 font-medium">{convertResult.data.message}</p>
                    </div>
                    <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
                      <h4 className="font-bold text-white mb-2">{convertResult.data.reel?.title}</h4>
                      <p className="text-sm text-pink-400 font-medium mb-2">Best Hook:</p>
                      <p className="text-white bg-pink-500/10 rounded p-2 border border-pink-500/30">{convertResult.data.reel?.best_hook}</p>
                    </div>
                    <div className="bg-slate-700/30 rounded-lg p-3 border border-slate-600">
                      <h5 className="font-medium text-white mb-2">All Hooks</h5>
                      {convertResult.data.reel?.hooks?.map((hook, i) => (
                        <div key={i} className="flex items-center justify-between py-1">
                          <span className="text-sm text-slate-300">{hook}</span>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(hook, `hook-${i}`)}>
                            {copied === `hook-${i}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          </Button>
                        </div>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {convertResult.data.reel?.hashtags?.map((tag, i) => (
                        <span key={i} className="text-sm bg-slate-800 text-slate-300 px-2 py-1 rounded cursor-pointer hover:bg-slate-700" onClick={() => copyToClipboard(tag, `reel-tag-${i}`)}>{tag}</span>
                      ))}
                    </div>
                  </div>
                ) : convertResult.type === 'quotes' ? (
                  <div className="space-y-4" data-testid="convert-quotes-result">
                    <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3">
                      <p className="text-emerald-300 font-medium">{convertResult.data.message}</p>
                    </div>
                    {convertResult.data.result?.quotes?.map((quote, i) => (
                      <div key={i} className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 rounded-lg p-4 border border-emerald-500/30">
                        <p className="text-lg text-white font-medium mb-2">{quote.quote}</p>
                        <p className="text-sm text-emerald-400">{quote.source}</p>
                        <div className="flex items-center justify-between mt-3">
                          <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-1 rounded capitalize">{quote.type}</span>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(`${quote.quote}\n${quote.source}`, `quote-${i}`)} className="text-slate-400 hover:text-white">
                            {copied === `quote-${i}` ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                            Copy
                          </Button>
                        </div>
                        {quote.designSuggestion && <p className="text-xs text-slate-500 mt-2">💡 {quote.designSuggestion}</p>}
                      </div>
                    ))}
                    <div className="flex flex-wrap gap-2 mt-4">
                      {convertResult.data.result?.hashtags?.map((tag, i) => (
                        <span key={i} className="text-sm bg-slate-800 text-slate-300 px-2 py-1 rounded cursor-pointer hover:bg-slate-700" onClick={() => copyToClipboard(tag, `quote-tag-${i}`)}>{tag}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="creator-tools" activeTab={activeTab} />
    </div>
  );
}
