import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { 
  Sparkles, Video, BookOpen, Zap, Clock, TrendingUp, Play, Menu, X, Shield, CheckCircle,
  Star, Users, Award, Gift, ArrowRight, Flame, Crown, Heart, MessageCircle, Share2,
  Instagram, Youtube, Twitter, ChevronDown
} from 'lucide-react';
import DemoReelGenerator from '../components/DemoReelGenerator';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Landing() {
  const [showDemo, setShowDemo] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [liveUsers, setLiveUsers] = useState(47);
  const [contentCreated, setContentCreated] = useState(12784);

  // Fetch real stats from API every 15 minutes
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API_URL}/api/live-stats/public`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.stats) {
            setLiveUsers(data.stats.creators_online);
            setContentCreated(data.stats.content_created_today);
          }
        }
      } catch (error) {
        console.error('Failed to fetch live stats:', error);
      }
    };

    // Fetch immediately
    fetchStats();
    
    // Then fetch every 15 minutes (900000ms)
    const interval = setInterval(fetchStats, 900000);
    
    return () => clearInterval(interval);
  }, []);

  const testimonials = [
    { name: "Sarah K.", role: "Content Creator", text: "Made 3 viral reels in my first week! The hooks are insanely good.", rating: 5, avatar: "S" },
    { name: "Mike R.", role: "YouTube Dad", text: "My kids story channel grew from 0 to 10K subscribers using this tool.", rating: 5, avatar: "M" },
    { name: "Priya S.", role: "Social Media Manager", text: "Saves me 5+ hours every week. The content calendar feature is a game changer.", rating: 5, avatar: "P" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 overflow-y-auto overflow-x-hidden" style={{ WebkitOverflowScrolling: 'touch' }}>
      {/* Demo Modal */}
      <DemoReelGenerator isOpen={showDemo} onClose={() => setShowDemo(false)} />
      
      {/* Live Activity Banner */}
      <div className="fixed top-0 left-0 right-0 z-[60] bg-gradient-to-r from-green-600 to-emerald-600 text-white text-center py-2 text-sm font-medium">
        <div className="flex items-center justify-center gap-3 animate-pulse">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-white rounded-full animate-ping"></span>
            <Users className="w-4 h-4" />
            {liveUsers} creators online now
          </span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:flex items-center gap-1">
            <Flame className="w-4 h-4" />
            {contentCreated.toLocaleString()} pieces of content created today
          </span>
        </div>
      </div>

      {/* Floating Navbar */}
      <nav className="fixed top-10 left-1/2 -translate-x-1/2 z-50 w-full max-w-5xl px-4">
        <div className="bg-black/50 backdrop-blur-md border border-white/10 rounded-full px-4 sm:px-8 py-3 sm:py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-500" />
            <span className="text-base sm:text-xl font-bold text-white">CreatorStudio AI</span>
          </div>
          
          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-4">
            <Link to="/pricing">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-pricing-btn">
                Pricing
              </Button>
            </Link>
            <Link to="/reviews">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-reviews-btn">
                Reviews
              </Button>
            </Link>
            <Link to="/user-manual">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-help-btn">
                Help
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-login-btn">
                Login
              </Button>
            </Link>
            <Link to="/signup">
              <Button className="bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white rounded-full animate-pulse" data-testid="nav-signup-btn">
                <Gift className="w-4 h-4 mr-1" />
                Get 100 Free Credits
              </Button>
            </Link>
          </div>
          
          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-white p-2 hover:bg-white/10 rounded-full transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-btn"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        
        {/* Mobile Menu Dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden mt-2 bg-black/90 backdrop-blur-md border border-white/10 rounded-2xl p-4 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex flex-col gap-2">
              <Link to="/pricing" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start">
                  Pricing
                </Button>
              </Link>
              <Link to="/reviews" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start">
                  Reviews
                </Button>
              </Link>
              <Link to="/user-manual" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start">
                  Help
                </Button>
              </Link>
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start">
                  Login
                </Button>
              </Link>
              <Link to="/signup" onClick={() => setMobileMenuOpen(false)}>
                <Button className="w-full bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white rounded-full mt-2">
                  <Gift className="w-4 h-4 mr-2" />
                  Get 100 Free Credits
                </Button>
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="pt-40 pb-16 px-4">
        <div className="max-w-7xl mx-auto text-center">
          {/* Trust Badges */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            <div className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/20 rounded-full px-4 py-2">
              <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
              <span className="text-yellow-500 text-sm font-medium">4.9/5 Rating</span>
            </div>
            <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-full px-4 py-2">
              <Users className="w-4 h-4 text-green-500" />
              <span className="text-green-500 text-sm font-medium">5,000+ Creators</span>
            </div>
            <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 rounded-full px-4 py-2">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <span className="text-purple-500 text-sm font-medium">AI-Powered</span>
            </div>
          </div>
          
          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-7xl font-black text-white mb-6 tracking-tight leading-tight">
            Go Viral on Social Media<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 via-pink-400 to-purple-400">
              Without Being Creative
            </span>
          </h1>
          
          <p className="text-base sm:text-lg md:text-xl text-slate-300 max-w-3xl mx-auto mb-6 px-4">
            AI writes your hooks, scripts, captions & hashtags. Generate complete kids story video packs. 
            Create 30-day content calendars. <span className="text-white font-semibold">All in under 60 seconds.</span>
          </p>

          {/* Urgency Banner */}
          <div className="inline-flex items-center gap-2 bg-red-500/20 border border-red-500/40 rounded-full px-6 py-3 mb-8 animate-bounce">
            <Flame className="w-5 h-5 text-red-400" />
            <span className="text-red-400 font-bold">LIMITED: Get 100 FREE credits today (worth ₹500)</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-6 px-4">
            <Link to="/signup" className="w-full sm:w-auto">
              <Button 
                size="lg" 
                className="w-full sm:w-auto bg-gradient-to-r from-orange-500 via-pink-500 to-purple-500 hover:from-orange-600 hover:via-pink-600 hover:to-purple-600 text-white rounded-full px-8 py-6 text-lg shadow-2xl shadow-pink-500/30 hover:scale-105 transition-all font-bold" 
                data-testid="hero-signup-btn"
              >
                <Gift className="w-5 h-5 mr-2" />
                Start Free - Get 100 Credits
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-8 px-4">
            <Button 
              size="lg" 
              variant="outline"
              onClick={() => setShowDemo(true)}
              className="w-full sm:w-auto border-2 border-white/20 text-white hover:bg-white/10 rounded-full px-6 py-4 text-base" 
              data-testid="hero-demo-btn"
            >
              <Play className="w-5 h-5 mr-2" />
              Watch Demo (No Signup Required)
            </Button>
          </div>

          <p className="text-slate-500 text-sm mb-12">No credit card required • Cancel anytime • Instant access</p>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto mb-16">
            <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/10">
              <div className="text-3xl font-bold text-indigo-400 mb-1">5-10s</div>
              <div className="text-slate-400 text-sm">Reel Generation</div>
            </div>
            <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/10">
              <div className="text-3xl font-bold text-purple-400 mb-1">30-90s</div>
              <div className="text-slate-400 text-sm">Story Pack</div>
            </div>
            <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/10">
              <div className="text-3xl font-bold text-green-400 mb-1">100</div>
              <div className="text-slate-400 text-sm">Free Credits</div>
            </div>
            <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/10">
              <div className="text-3xl font-bold text-orange-400 mb-1">50K+</div>
              <div className="text-slate-400 text-sm">Content Created</div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof Testimonials */}
      <section className="py-16 px-4 bg-black/30">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-4">
            Loved by Creators Worldwide
          </h2>
          <p className="text-slate-400 text-center mb-12">See what our community is saying</p>
          
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-indigo-500/50 transition-all hover:scale-105">
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                  ))}
                </div>
                <p className="text-slate-300 mb-6 italic">"{testimonial.text}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="text-white font-semibold">{testimonial.name}</div>
                    <div className="text-slate-400 text-sm">{testimonial.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-4">
            Everything You Need to Go Viral
          </h2>
          <p className="text-slate-400 text-center mb-12">Professional content creation tools at your fingertips</p>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Reel Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-indigo-500/50 transition-colors group">
              <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Video className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Viral Reel Scripts</h3>
              <p className="text-slate-400 mb-4 text-sm">5 hooks, script, captions, hashtags in 10 seconds</p>
              <div className="flex items-center gap-2 text-indigo-400 text-sm font-medium">
                <span>10 credits</span>
                <span className="text-slate-500">per reel</span>
              </div>
            </div>

            {/* Story Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-purple-500/50 transition-colors group">
              <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <BookOpen className="w-6 h-6 text-purple-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Kids Story Packs</h3>
              <p className="text-slate-400 mb-4 text-sm">Complete video production package with voiceover</p>
              <div className="flex items-center gap-2 text-purple-400 text-sm font-medium">
                <span>6 credits</span>
                <span className="text-slate-500">per story</span>
              </div>
            </div>

            {/* Comic Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-pink-500/50 transition-colors group relative">
              <div className="absolute -top-2 -right-2 bg-gradient-to-r from-orange-500 to-pink-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                TRENDING
              </div>
              <div className="w-12 h-12 bg-pink-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Award className="w-6 h-6 text-pink-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Photo to Comic</h3>
              <p className="text-slate-400 mb-4 text-sm">Transform photos into comic avatars & strips</p>
              <div className="flex items-center gap-2 text-pink-400 text-sm font-medium">
                <span>15 credits</span>
                <span className="text-slate-500">per comic</span>
              </div>
            </div>

            {/* Calendar Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-green-500/50 transition-colors group">
              <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Clock className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">30-Day Calendar</h3>
              <p className="text-slate-400 mb-4 text-sm">Never run out of content ideas again</p>
              <div className="flex items-center gap-2 text-green-400 text-sm font-medium">
                <span>10 credits</span>
                <span className="text-slate-500">per calendar</span>
              </div>
            </div>

            {/* Hashtag Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-blue-500/50 transition-colors group">
              <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <TrendingUp className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Trending Hashtags</h3>
              <p className="text-slate-400 mb-4 text-sm">AI-optimized hashtags for maximum reach</p>
              <div className="flex items-center gap-2 text-blue-400 text-sm font-medium">
                <span>5 credits</span>
                <span className="text-slate-500">per set</span>
              </div>
            </div>

            {/* Carousel Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:border-yellow-500/50 transition-colors group">
              <div className="w-12 h-12 bg-yellow-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Share2 className="w-6 h-6 text-yellow-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Carousel Maker</h3>
              <p className="text-slate-400 mb-4 text-sm">Engaging multi-slide posts that convert</p>
              <div className="flex items-center gap-2 text-yellow-400 text-sm font-medium">
                <span>8 credits</span>
                <span className="text-slate-500">per carousel</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Platform Support */}
      <section className="py-16 px-4 bg-black/30">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl font-bold text-white mb-8">Works for All Platforms</h2>
          <div className="flex flex-wrap items-center justify-center gap-8">
            <div className="flex items-center gap-2 text-slate-400">
              <Instagram className="w-8 h-8" />
              <span>Instagram</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <Youtube className="w-8 h-8" />
              <span>YouTube</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <Twitter className="w-8 h-8" />
              <span>Twitter/X</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
              </svg>
              <span>TikTok</span>
            </div>
          </div>
        </div>
      </section>

      {/* Daily Rewards Teaser */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-r from-orange-500/20 via-pink-500/20 to-purple-500/20 border border-orange-500/30 rounded-3xl p-8 text-center">
            <div className="inline-flex items-center gap-2 bg-orange-500/20 rounded-full px-4 py-2 mb-4">
              <Gift className="w-5 h-5 text-orange-400" />
              <span className="text-orange-400 font-bold">DAILY REWARDS</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
              Earn Free Credits Every Day!
            </h2>
            <p className="text-slate-300 mb-6">
              Login daily to claim bonus credits. Build a streak and earn up to <span className="text-orange-400 font-bold">50 bonus credits per week!</span>
            </p>
            <div className="flex flex-wrap justify-center gap-4 mb-6">
              {['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'].map((day, i) => (
                <div key={i} className={`w-16 h-16 rounded-xl flex flex-col items-center justify-center ${i === 6 ? 'bg-gradient-to-r from-orange-500 to-pink-500' : 'bg-white/10'} border border-white/20`}>
                  <span className="text-xs text-slate-400">{day}</span>
                  <span className="text-white font-bold">{i === 6 ? '10' : (i + 2)}</span>
                </div>
              ))}
            </div>
            <Link to="/signup">
              <Button className="bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white rounded-full px-8 py-4 text-lg font-bold">
                Start Earning Now
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-white/10 rounded-3xl p-8 sm:p-12">
          <div className="inline-flex items-center gap-2 bg-green-500/20 rounded-full px-4 py-2 mb-6">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-green-400 font-medium">Join 5,000+ creators already using CreatorStudio</span>
          </div>
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to Create Viral Content?
          </h2>
          <p className="text-base sm:text-lg md:text-xl text-slate-300 mb-8 px-4">
            Get 100 free credits on signup. No credit card required. Start creating in 30 seconds.
          </p>
          <Link to="/signup">
            <Button size="lg" className="w-full sm:w-auto bg-gradient-to-r from-orange-500 via-pink-500 to-purple-500 hover:from-orange-600 hover:via-pink-600 hover:to-purple-600 text-white rounded-full px-12 py-6 text-lg shadow-2xl shadow-pink-500/30 hover:scale-105 transition-all font-bold" data-testid="cta-signup-btn">
              <Gift className="w-5 h-5 mr-2" />
              Claim Your 100 Free Credits
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
          <p className="text-slate-500 text-sm mt-4">No spam. Unsubscribe anytime.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-500" />
              <span className="text-white font-semibold">CreatorStudio AI</span>
            </div>
            
            {/* Security Badge */}
            <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-full px-4 py-2">
              <Shield className="w-4 h-4 text-green-400" />
              <span className="text-green-400 text-sm font-medium">Protected by OWASP Standards</span>
              <CheckCircle className="w-3 h-3 text-green-400" />
            </div>
            
            <div className="flex items-center gap-6 text-slate-400">
              <Link to="/pricing" className="hover:text-white transition-colors">Pricing</Link>
              <Link to="/reviews" className="hover:text-white transition-colors">Reviews</Link>
              <Link to="/contact" className="hover:text-white transition-colors">Contact</Link>
              <Link to="/privacy-policy" className="hover:text-white transition-colors">Privacy</Link>
              <Link to="/terms-of-service" className="hover:text-white transition-colors">Terms</Link>
            </div>
          </div>
          <p className="text-slate-500 text-sm text-center mt-6">© 2026 Visionary Suite. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
