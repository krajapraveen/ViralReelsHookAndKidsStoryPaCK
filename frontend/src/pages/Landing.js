import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Sparkles, Video, BookOpen, Zap, Clock, TrendingUp } from 'lucide-react';

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Floating Navbar */}
      <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-5xl px-4">
        <div className="bg-black/50 backdrop-blur-md border border-white/10 rounded-full px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-indigo-500" />
            <span className="text-xl font-bold text-white">CreatorStudio AI</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/pricing">
              <Button variant="ghost" className="text-white hover:bg-white/10" data-testid="nav-pricing-btn">
                Pricing
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
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 rounded-full px-6 py-2 mb-8">
            <Sparkles className="w-4 h-4 text-orange-500" />
            <span className="text-orange-500 text-sm font-medium">AI-Powered Content Creation</span>
          </div>
          
          <h1 className="text-6xl lg:text-7xl font-black text-white mb-6 tracking-tight leading-tight">
            Generate viral reels +<br />
            kids story videos<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-orange-400">
              in minutes
            </span>
          </h1>
          
          <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-12">
            Hooks, scripts, captions, hashtags — and complete kids story video packs with scene prompts and voiceovers. 
            Everything you need to create viral content.
          </p>

          <div className="flex items-center justify-center gap-4 mb-16">
            <Link to="/app/reels">
              <Button size="lg" className="bg-indigo-500 hover:bg-indigo-600 text-white rounded-full px-8 py-6 text-lg shadow-lg shadow-indigo-500/20 hover:scale-105 transition-all" data-testid="hero-reel-btn">
                <Video className="w-5 h-5 mr-2" />
                Generate a Reel Now
              </Button>
            </Link>
            <Link to="/app/stories">
              <Button size="lg" variant="outline" className="border-2 border-white/20 text-white hover:bg-white/10 rounded-full px-8 py-6 text-lg" data-testid="hero-story-btn">
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
              <div className="text-4xl font-bold text-orange-400 mb-2">30-90s</div>
              <div className="text-slate-400">Story Pack</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-green-400 mb-2">5 Free</div>
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
                  <Zap className="w-4 h-4 text-orange-500" />
                  <span>Instant generation (5-10 seconds)</span>
                </li>
                <li className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-orange-500" />
                  <span>Multiple niches & tones</span>
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-orange-500" />
                  <span>Optimized for retention</span>
                </li>
              </ul>
            </div>

            {/* Story Feature */}
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-8 hover:border-orange-500/50 transition-colors">
              <div className="w-14 h-14 bg-orange-500/10 rounded-xl flex items-center justify-center mb-6">
                <BookOpen className="w-7 h-7 text-orange-400" />
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
        <div className="max-w-4xl mx-auto text-center bg-gradient-to-r from-indigo-500/10 to-orange-500/10 border border-white/10 rounded-3xl p-12">
          <h2 className="text-4xl font-bold text-white mb-4">Start Creating Today</h2>
          <p className="text-xl text-slate-300 mb-8">
            Get 5 free credits on signup. No credit card required.
          </p>
          <Link to="/signup">
            <Button size="lg" className="bg-gradient-to-r from-indigo-500 to-orange-500 hover:from-indigo-600 hover:to-orange-600 text-white rounded-full px-12 py-6 text-lg shadow-lg hover:scale-105 transition-all" data-testid="cta-signup-btn">
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 px-4">
        <div className="max-w-7xl mx-auto text-center text-slate-400">
          <p>&copy; 2026 CreatorStudio AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
