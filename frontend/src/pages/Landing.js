import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Sparkles, Video, BookOpen, Zap, Clock, TrendingUp, Play, Menu, X } from 'lucide-react';
import DemoReelGenerator from '../components/DemoReelGenerator';

export default function Landing() {
  const [showDemo, setShowDemo] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 overflow-y-auto overflow-x-hidden" style={{ WebkitOverflowScrolling: 'touch' }}>
      {/* Demo Modal */}
      <DemoReelGenerator isOpen={showDemo} onClose={() => setShowDemo(false)} />
      {/* Floating Navbar */}
      <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-5xl px-4">
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
            <Link to="/contact">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-contact-btn">
                Contact
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-login-btn">
                Login
              </Button>
            </Link>
            <Link to="/signup">
              <Button className="bg-indigo-500 hover:bg-indigo-600 text-white rounded-full" data-testid="nav-signup-btn">
                Get Started
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
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start" data-testid="mobile-nav-pricing">
                  Pricing
                </Button>
              </Link>
              <Link to="/reviews" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start" data-testid="mobile-nav-reviews">
                  Reviews
                </Button>
              </Link>
              <Link to="/user-manual" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start" data-testid="mobile-nav-help">
                  Help
                </Button>
              </Link>
              <Link to="/contact" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start" data-testid="mobile-nav-contact">
                  Contact
                </Button>
              </Link>
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full text-white hover:bg-white/10 justify-start" data-testid="mobile-nav-login">
                  Login
                </Button>
              </Link>
              <Link to="/signup" onClick={() => setMobileMenuOpen(false)}>
                <Button className="w-full bg-indigo-500 hover:bg-indigo-600 text-white rounded-full mt-2" data-testid="mobile-nav-signup">
                  Get Started
                </Button>
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 rounded-full px-6 py-2 mb-8">
            <Sparkles className="w-4 h-4 text-purple-500" />
            <span className="text-purple-500 text-sm font-medium">AI-Powered Content Creation</span>
          </div>
          
          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-7xl font-black text-white mb-6 tracking-tight leading-tight">
            Generate viral reels +<br />
            kids story videos + much more<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
              in minutes
            </span>
          </h1>
          
          <p className="text-base sm:text-lg md:text-xl text-slate-300 max-w-3xl mx-auto mb-8 sm:mb-12 px-4">
            Hooks, scripts, captions, hashtags — complete kids story video packs with scene prompts and voiceovers, 
            AI image & video generation (GenStudio), content repurposing tools, thumbnail text generators, content calendars, 
            carousel makers, and so much more. Everything you need to create viral content.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-6 sm:mb-8 px-4">
            <Button 
              size="lg" 
              onClick={() => setShowDemo(true)}
              className="w-full sm:w-auto bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white rounded-full px-6 sm:px-8 py-4 sm:py-6 text-base sm:text-lg shadow-lg shadow-purple-500/20 hover:scale-105 transition-all" 
              data-testid="hero-demo-btn"
            >
              <Play className="w-5 h-5 mr-2" />
              Try Free Demo
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-12 sm:mb-16 px-4">
            <Link to="/app/reels" className="w-full sm:w-auto">
              <Button size="lg" className="w-full sm:w-auto bg-indigo-500 hover:bg-indigo-600 text-white rounded-full px-6 sm:px-8 py-4 sm:py-6 text-base sm:text-lg shadow-lg shadow-indigo-500/20 hover:scale-105 transition-all" data-testid="hero-reel-btn">
                <Video className="w-5 h-5 mr-2" />
                Generate a Reel Now
              </Button>
            </Link>
            <Link to="/app/stories" className="w-full sm:w-auto">
              <Button size="lg" variant="outline" className="w-full sm:w-auto border-2 border-white/20 text-white hover:bg-white/10 rounded-full px-6 sm:px-8 py-4 sm:py-6 text-base sm:text-lg" data-testid="hero-story-btn">
                <BookOpen className="w-5 h-5 mr-2" />
                Create Kids Story Pack
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="text-4xl font-bold text-indigo-400 mb-2">5-10s</div>
              <div className="text-slate-400">Reel Generation</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-purple-400 mb-2">30-90s</div>
              <div className="text-slate-400">Story Pack</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-green-400 mb-2">100 Free</div>
              <div className="text-slate-400">Credits on Signup</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Reel Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-8 hover:border-indigo-500/50 transition-colors">
              <div className="w-14 h-14 bg-indigo-500/10 rounded-xl flex items-center justify-center mb-6">
                <Video className="w-7 h-7 text-indigo-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">Viral Reel Scripts</h3>
              <p className="text-slate-300 mb-6">
                Get 5 hooks, full script, captions, hashtags, and b-roll ideas in seconds. Perfect for Instagram, YouTube Shorts, and TikTok.
              </p>
              <ul className="space-y-3 text-slate-400">
                <li className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-purple-500" />
                  <span>Instant generation (5-10 seconds)</span>
                </li>
                <li className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-purple-500" />
                  <span>Multiple niches & tones</span>
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-500" />
                  <span>Optimized for retention</span>
                </li>
              </ul>
            </div>

            {/* Story Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-8 hover:border-purple-500/50 transition-colors">
              <div className="w-14 h-14 bg-purple-500/10 rounded-xl flex items-center justify-center mb-6">
                <BookOpen className="w-7 h-7 text-purple-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">Kids Story Video Packs</h3>
              <p className="text-slate-300 mb-6">
                Complete production packages with scene breakdowns, image prompts, voiceover scripts, and YouTube optimization.
              </p>
              <ul className="space-y-3 text-slate-400">
                <li className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-indigo-500" />
                  <span>8-12 scene options</span>
                </li>
                <li className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-500" />
                  <span>Safe & age-appropriate</span>
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-500" />
                  <span>YouTube title, description & tags</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-white/10 rounded-3xl p-8 sm:p-12">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">Start Creating Today</h2>
          <p className="text-base sm:text-lg md:text-xl text-slate-300 mb-8 px-4">
            Get 100 free credits on signup. No credit card required.
          </p>
          <Link to="/signup">
            <Button size="lg" className="w-full sm:w-auto bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-full px-8 sm:px-12 py-4 sm:py-6 text-base sm:text-lg shadow-lg hover:scale-105 transition-all" data-testid="cta-signup-btn">
              Get Started Free
            </Button>
          </Link>
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
            <div className="flex items-center gap-6 text-slate-400">
              <Link to="/pricing" className="hover:text-white transition-colors">Pricing</Link>
              <Link to="/reviews" className="hover:text-white transition-colors">Reviews</Link>
              <Link to="/contact" className="hover:text-white transition-colors">Contact</Link>
            </div>
            <p className="text-slate-500 text-sm">© 2026 Visionary Suite. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
