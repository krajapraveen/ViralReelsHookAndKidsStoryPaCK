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

  const niches = ['luxury', 'relationship', 'health', 'motivation', 'parenting', 'business', 'travel', 'food'];

  useEffect(() => {
    fetchCredits();
    fetchTrending();
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await api.get('/api/credits/balance');
      setCredits(response.data.balance);
    } catch (error) {
      console.error('Failed to fetch credits');
    }
  };

  const fetchTrending = async () => {
    try {
      const response = await api.get('/api/content/trending');
      setTrendingTopics(response.data.topics || []);
    } catch (error) {
      console.error('Failed to fetch trending');
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
      const response = await api.post(`/api/creator-tools/calendar/generate?niche=${calendarNiche}&days=${calendarDays}&include_full_scripts=${includeScripts}`);
      setCalendarResult(response.data);
      setCredits(response.data.remainingCredits);
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
    if (credits < 2) {
      toast.error('Need 2 credits for carousel');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post(`/api/creator-tools/carousel/generate?topic=${encodeURIComponent(carouselTopic)}&niche=${carouselNiche}&slides=${carouselSlides}`);
      setCarouselResult(response.data);
      setCredits(response.data.remainingCredits);
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

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-900">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Wand2 className="w-6 h-6 text-purple-600" />
              <span className="text-xl font-bold text-slate-900">Creator Tools</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-purple-50 border border-purple-100 rounded-full px-4 py-2">
              <Coins className="w-4 h-4 text-purple-600" />
              <span className="font-semibold text-purple-700">{credits} Credits</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="text-slate-600 hover:text-slate-900" data-testid="creator-tools-logout">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid grid-cols-6 lg:grid-cols-6 mb-8 bg-white border border-slate-200 shadow-sm" data-testid="creator-tools-tabs">
            <TabsTrigger value="calendar" className="flex items-center gap-2 data-[state=active]:text-purple-700" data-testid="tab-calendar">
              <Calendar className="w-4 h-4" />
              <span className="hidden sm:inline">Calendar</span>
            </TabsTrigger>
            <TabsTrigger value="carousel" className="flex items-center gap-2 data-[state=active]:text-purple-700" data-testid="tab-carousel">
              <LayoutGrid className="w-4 h-4" />
              <span className="hidden sm:inline">Carousel</span>
            </TabsTrigger>
            <TabsTrigger value="hashtags" className="flex items-center gap-2 data-[state=active]:text-purple-700" data-testid="tab-hashtags">
              <Hash className="w-4 h-4" />
              <span className="hidden sm:inline">Hashtags</span>
            </TabsTrigger>
            <TabsTrigger value="thumbnails" className="flex items-center gap-2 data-[state=active]:text-purple-700" data-testid="tab-thumbnails">
              <Type className="w-4 h-4" />
              <span className="hidden sm:inline">Thumbnails</span>
            </TabsTrigger>
            <TabsTrigger value="trending" className="flex items-center gap-2 data-[state=active]:text-purple-700" data-testid="tab-trending">
              <TrendingUp className="w-4 h-4" />
              <span className="hidden sm:inline">Trending</span>
            </TabsTrigger>
            <TabsTrigger value="convert" className="flex items-center gap-2 data-[state=active]:text-purple-700" data-testid="tab-convert">
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">Convert</span>
            </TabsTrigger>
          </TabsList>

          {/* 30-Day Calendar Tab */}
          <TabsContent value="calendar">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <h2 className="text-2xl font-bold text-slate-900 mb-2 flex items-center gap-2">
                  <Calendar className="w-6 h-6 text-purple-600" />
                  30-Day Content Calendar
                </h2>
                <p className="text-slate-500 mb-6">Generate a full month of content ideas</p>
                
                <div className="space-y-4">
                  <div>
                    <Label>Select Niche</Label>
                    <Select value={calendarNiche} onValueChange={setCalendarNiche}>
                      <SelectTrigger data-testid="calendar-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {niches.map(n => (
                          <SelectItem key={n} value={n}>{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>Number of Days</Label>
                    <Select value={calendarDays.toString()} onValueChange={(v) => setCalendarDays(parseInt(v))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="7">7 days</SelectItem>
                        <SelectItem value="14">14 days</SelectItem>
                        <SelectItem value="30">30 days</SelectItem>
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
              
              <div className="bg-white rounded-xl border border-slate-200 p-6 max-h-[600px] overflow-y-auto">
                <h3 className="text-lg font-bold mb-4">Your Content Calendar</h3>
                {!calendarResult ? (
                  <div className="text-center py-12 text-slate-500">
                    <Calendar className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p>Your calendar will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-3" data-testid="calendar-result">
                    {calendarResult.calendar.map((day) => (
                      <div key={day.day} className="bg-slate-50 rounded-lg p-4 border border-slate-100">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-purple-600">Day {day.day}</span>
                          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">{day.content_type}</span>
                        </div>
                        <p className="text-sm font-medium mb-2">{day.hook}</p>
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>📱 {day.format}</span>
                          <span>⏰ {day.best_time}</span>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(day.hook, `day-${day.day}`)}>
                            {copied === `day-${day.day}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
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
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <LayoutGrid className="w-6 h-6 text-blue-500" />
                  Carousel Generator
                </h2>
                <p className="text-slate-500 mb-6">Create engaging carousel posts</p>
                
                <div className="space-y-4">
                  <div>
                    <Label>Topic</Label>
                    <Input 
                      placeholder="e.g., 5 Morning Habits for Success"
                      value={carouselTopic}
                      onChange={(e) => setCarouselTopic(e.target.value)}
                      data-testid="carousel-topic-input"
                    />
                  </div>
                  
                  <div>
                    <Label>Niche</Label>
                    <Select value={carouselNiche} onValueChange={setCarouselNiche}>
                      <SelectTrigger data-testid="carousel-niche-select">
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
                      <span className="font-medium">Cost: 2 credits</span>
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
              
              <div className="bg-white rounded-xl border border-slate-200 p-6 max-h-[600px] overflow-y-auto">
                <h3 className="text-lg font-bold mb-4">Your Carousel</h3>
                {!carouselResult ? (
                  <div className="text-center py-12 text-slate-500">
                    <LayoutGrid className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p>Your carousel will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-4" data-testid="carousel-result">
                    {carouselResult.carousel.slides.map((slide) => (
                      <div key={slide.slide_number} className={`rounded-lg p-4 border ${
                        slide.type === 'hook' ? 'bg-blue-50 border-blue-200' : 
                        slide.type === 'cta' ? 'bg-green-50 border-green-200' : 
                        'bg-slate-50 border-slate-200'
                      }`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold">Slide {slide.slide_number}</span>
                          <span className="text-xs uppercase px-2 py-1 rounded bg-white">{slide.type}</span>
                        </div>
                        <p className="font-medium">{slide.text}</p>
                        {slide.subtext && <p className="text-sm text-slate-600 mt-1">{slide.subtext}</p>}
                        {slide.design_tip && <p className="text-xs text-slate-500 mt-2">💡 {slide.design_tip}</p>}
                      </div>
                    ))}
                    
                    {carouselResult.carousel.caption && (
                      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mt-4">
                        <h4 className="font-bold mb-2">Caption</h4>
                        <p className="text-sm whitespace-pre-wrap">{carouselResult.carousel.caption.long}</p>
                        <Button variant="ghost" size="sm" className="mt-2" onClick={() => copyToClipboard(carouselResult.carousel.caption.long, 'caption')}>
                          {copied === 'caption' ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                          Copy Caption
                        </Button>
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
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <Hash className="w-6 h-6 text-green-500" />
                  Hashtag Bank
                </h2>
                <p className="text-slate-500 mb-6">Curated hashtags by niche - FREE</p>
                
                <div className="space-y-4">
                  <div>
                    <Label>Select Niche</Label>
                    <Select value={hashtagNiche} onValueChange={setHashtagNiche}>
                      <SelectTrigger data-testid="hashtag-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {niches.map(n => (
                          <SelectItem key={n} value={n}>{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-700">
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
              
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-lg font-bold mb-4">Hashtag Results</h3>
                {!hashtagResult ? (
                  <div className="text-center py-12 text-slate-500">
                    <Hash className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p>Select a niche and click Get Hashtags</p>
                  </div>
                ) : (
                  <div className="space-y-4" data-testid="hashtag-result">
                    {Object.entries(hashtagResult.hashtags).map(([category, tags]) => (
                      <div key={category} className="bg-slate-50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-bold capitalize">{category.replace('_', ' ')}</h4>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(tags.join(' '), category)}>
                            {copied === category ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          </Button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {tags.map((tag, i) => (
                            <span key={i} className="text-sm bg-white border px-2 py-1 rounded">{tag}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                    <p className="text-sm text-slate-500 text-center mt-4">💡 {hashtagResult.tip}</p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Thumbnails Tab */}
          <TabsContent value="thumbnails">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <Type className="w-6 h-6 text-orange-500" />
                  Thumbnail Text Generator
                </h2>
                <p className="text-slate-500 mb-6">Generate attention-grabbing thumbnail text - FREE</p>
                
                <div className="space-y-4">
                  <div>
                    <Label>Topic/Subject</Label>
                    <Input 
                      placeholder="e.g., productivity, weight loss, money"
                      value={thumbnailTopic}
                      onChange={(e) => setThumbnailTopic(e.target.value)}
                      data-testid="thumbnail-topic-input"
                    />
                  </div>
                  
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-orange-700">
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
              
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-lg font-bold mb-4">Thumbnail Options</h3>
                {!thumbnailResult ? (
                  <div className="text-center py-12 text-slate-500">
                    <Type className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p>Enter a topic and generate thumbnail text</p>
                  </div>
                ) : (
                  <div className="space-y-4" data-testid="thumbnail-result">
                    {Object.entries(thumbnailResult.thumbnails).map(([style, texts]) => (
                      <div key={style} className={`rounded-lg p-4 ${
                        style === 'emotional' ? 'bg-red-50 border border-red-200' :
                        style === 'curiosity' ? 'bg-yellow-50 border border-yellow-200' :
                        style === 'action' ? 'bg-blue-50 border border-blue-200' :
                        'bg-purple-50 border border-purple-200'
                      }`}>
                        <h4 className="font-bold capitalize mb-2">{style}</h4>
                        <div className="space-y-2">
                          {texts.map((text, i) => (
                            <div key={i} className="flex items-center justify-between bg-white rounded px-3 py-2">
                              <span className="font-medium">{text}</span>
                              <Button variant="ghost" size="sm" onClick={() => copyToClipboard(text, `${style}-${i}`)}>
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
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-pink-500" />
                Weekly Trending Topics
              </h2>
              <p className="text-slate-500 mb-6">Stay updated with what's trending this week</p>
              
              {trendingTopics.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <TrendingUp className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                  <p>No trending topics available yet</p>
                  <p className="text-sm mt-2">Check back soon for weekly updates!</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="trending-result">
                  {trendingTopics.map((topic) => (
                    <div key={topic.id} className="bg-gradient-to-br from-pink-50 to-purple-50 rounded-lg p-4 border border-pink-200">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs bg-pink-100 text-pink-700 px-2 py-1 rounded capitalize">{topic.niche}</span>
                      </div>
                      <h3 className="font-bold mb-2">{topic.title}</h3>
                      <p className="text-sm text-slate-600 mb-3">{topic.description}</p>
                      <div className="bg-white rounded p-2 text-sm">
                        <span className="font-medium text-purple-600">Hook: </span>
                        {topic.hook_preview}
                      </div>
                      <p className="text-xs text-slate-500 mt-2">💡 {topic.suggested_angle}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* Convert Tab */}
          <TabsContent value="convert">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-2xl font-bold text-slate-900 mb-2 flex items-center gap-2">
                <RefreshCw className="w-6 h-6 text-indigo-600" />
                Convert Content
              </h2>
              <p className="text-slate-500 mb-6">Repurpose your existing content into new formats</p>
              
              <div className="grid md:grid-cols-2 gap-6">
                {/* Reel to Carousel */}
                <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-5 border border-indigo-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-indigo-100 rounded-lg">
                      <LayoutGrid className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900">Reel → Carousel</h3>
                      <span className="text-xs text-indigo-600 font-medium bg-indigo-100 px-2 py-0.5 rounded-full">5 credits</span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 mb-4">Convert your viral reel script into a 5-10 slide Instagram carousel with captions</p>
                  <div className="flex items-center gap-2">
                    <Select defaultValue="">
                      <SelectTrigger className="flex-1 bg-white" data-testid="convert-reel-carousel-select">
                        <SelectValue placeholder="Select a reel to convert" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="recent">Use most recent reel</SelectItem>
                        <SelectItem value="history">Browse from history...</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button className="bg-indigo-600 hover:bg-indigo-700" size="sm" data-testid="convert-reel-carousel-btn">
                      Convert
                    </Button>
                  </div>
                </div>
                
                {/* Reel to YouTube */}
                <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-5 border border-red-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-red-100 rounded-lg">
                      <Video className="w-5 h-5 text-red-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900">Reel → YouTube</h3>
                      <span className="text-xs text-red-600 font-medium bg-red-100 px-2 py-0.5 rounded-full">2 credits</span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 mb-4">Expand your 60-second reel into a full 8-10 minute YouTube video script</p>
                  <div className="flex items-center gap-2">
                    <Select defaultValue="">
                      <SelectTrigger className="flex-1 bg-white" data-testid="convert-reel-youtube-select">
                        <SelectValue placeholder="Select a reel to expand" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="recent">Use most recent reel</SelectItem>
                        <SelectItem value="history">Browse from history...</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button className="bg-red-600 hover:bg-red-700" size="sm" data-testid="convert-reel-youtube-btn">
                      Expand
                    </Button>
                  </div>
                </div>
                
                {/* Story to Reel */}
                <div className="bg-gradient-to-br from-pink-50 to-rose-50 rounded-xl p-5 border border-pink-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-pink-100 rounded-lg">
                      <BookOpen className="w-5 h-5 text-pink-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900">Story → Reel</h3>
                      <span className="text-xs text-pink-600 font-medium bg-pink-100 px-2 py-0.5 rounded-full">5 credits</span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 mb-4">Convert your kids story into a short parenting reel about the moral/lesson</p>
                  <div className="flex items-center gap-2">
                    <Select defaultValue="">
                      <SelectTrigger className="flex-1 bg-white" data-testid="convert-story-reel-select">
                        <SelectValue placeholder="Select a story to convert" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="recent">Use most recent story</SelectItem>
                        <SelectItem value="history">Browse from history...</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button className="bg-pink-600 hover:bg-pink-700" size="sm" data-testid="convert-story-reel-btn">
                      Convert
                    </Button>
                  </div>
                </div>
                
                {/* Story to Quote */}
                <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-5 border border-emerald-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-emerald-100 rounded-lg">
                      <MessageSquare className="w-5 h-5 text-emerald-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900">Story → Quote</h3>
                      <span className="text-xs text-emerald-600 font-medium bg-emerald-100 px-2 py-0.5 rounded-full">FREE</span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 mb-4">Generate shareable moral quotes and wisdom from your kids story</p>
                  <div className="flex items-center gap-2">
                    <Select defaultValue="">
                      <SelectTrigger className="flex-1 bg-white" data-testid="convert-story-quote-select">
                        <SelectValue placeholder="Select a story" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="recent">Use most recent story</SelectItem>
                        <SelectItem value="history">Browse from history...</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button className="bg-emerald-600 hover:bg-emerald-700" size="sm" data-testid="convert-story-quote-btn">
                      Generate
                    </Button>
                  </div>
                </div>
              </div>
              
              {/* Coming Soon */}
              <div className="mt-6 bg-slate-50 rounded-lg p-4 border border-dashed border-slate-300">
                <p className="text-sm text-slate-500 text-center">
                  🚀 Coming Soon: Carousel → Thread, YouTube → Shorts, Story → Audiobook
                </p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
