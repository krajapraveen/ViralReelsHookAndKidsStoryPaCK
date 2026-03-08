import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  BookOpen, Search, ArrowLeft, ChevronRight, ChevronDown,
  Sparkles, Video, BookMarked, Film, Calendar, Wand2,
  Palette, CreditCard, HelpCircle, Settings, Shield,
  Download, Play, Image, FileText, Users, Zap
} from 'lucide-react';
import api from '../utils/api';

const FEATURE_ICONS = {
  story_generator: BookMarked,
  reel_generator: Video,
  story_series: Film,
  challenge_generator: Calendar,
  tone_switcher: Wand2,
  coloring_book: Palette,
  creator_tools: Settings
};

export default function UserManual() {
  const [manual, setManual] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [expandedSections, setExpandedSections] = useState({});
  const [activeFeature, setActiveFeature] = useState(null);

  useEffect(() => {
    fetchManual();
  }, []);

  const fetchManual = async () => {
    try {
      const response = await api.get('/api/help/manual');
      setManual(response.data);
    } catch (error) {
      console.error('Failed to load manual:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    
    try {
      const response = await api.get(`/api/help/search?q=${encodeURIComponent(query)}`);
      setSearchResults(response.data.results || []);
    } catch (error) {
      console.error('Search error:', error);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <BookOpen className="w-8 h-8 text-purple-400" />
                <div>
                  <h1 className="text-xl font-bold text-white">User Manual</h1>
                  <p className="text-xs text-slate-400">Complete guide to Visionary Suite</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Search */}
        <div className="mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search the manual..."
              className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-12 pr-4 py-3 text-white focus:border-purple-500 focus:outline-none"
            />
          </div>
          
          {searchResults.length > 0 && (
            <div className="mt-2 bg-slate-800 border border-slate-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3">Search Results</h4>
              {searchResults.map((result, idx) => (
                <div key={idx} className="py-2 border-b border-slate-700 last:border-0">
                  <p className="text-sm text-white">{result.content}</p>
                  <p className="text-xs text-slate-500">{result.path}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Start */}
        <div className="mb-8 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Quick Start
          </h2>
          <div className="grid md:grid-cols-4 gap-4">
            {manual?.overview?.quickStart?.map((step, idx) => (
              <div key={idx} className="bg-slate-800/50 rounded-lg p-4">
                <p className="text-sm text-slate-300">{step}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white mb-4">Feature Guides</h2>
          
          {manual?.features && Object.entries(manual.features).map(([key, feature]) => {
            const Icon = FEATURE_ICONS[key] || HelpCircle;
            const isExpanded = expandedSections[key];
            
            return (
              <div key={key} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleSection(key)}
                  className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                      <Icon className="w-5 h-5 text-purple-400" />
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-white">{feature.title}</h3>
                      <p className="text-xs text-slate-400">{feature.description}</p>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  )}
                </button>
                
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-4">
                    {/* Credit Cost */}
                    {feature.creditCost && (
                      <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                        <p className="text-sm text-green-400">
                          <CreditCard className="w-4 h-4 inline mr-2" />
                          Cost: {typeof feature.creditCost === 'object' 
                            ? Object.entries(feature.creditCost).map(([k, v]) => `${k}: ${v}`).join(', ')
                            : feature.creditCost
                          }
                        </p>
                      </div>
                    )}
                    
                    {/* How to Use */}
                    {feature.howToUse && (
                      <div>
                        <h4 className="font-medium text-white mb-2">How to Use</h4>
                        <ol className="space-y-2">
                          {feature.howToUse.map((step, idx) => (
                            <li key={idx} className="text-sm text-slate-300 flex gap-2">
                              <span className="text-purple-400 font-medium">{idx + 1}.</span>
                              {step.replace(/^\d+\.\s*/, '')}
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                    
                    {/* Tips */}
                    {feature.tips && (
                      <div>
                        <h4 className="font-medium text-white mb-2">Tips</h4>
                        <ul className="space-y-1">
                          {feature.tips.map((tip, idx) => (
                            <li key={idx} className="text-sm text-slate-400 flex gap-2">
                              <span className="text-yellow-400">💡</span>
                              {tip}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* Sub-features */}
                    {feature.subFeatures && (
                      <div>
                        <h4 className="font-medium text-white mb-2">Sub-features</h4>
                        <div className="grid md:grid-cols-2 gap-3">
                          {Object.entries(feature.subFeatures).map(([subKey, subFeature]) => (
                            <div key={subKey} className="bg-slate-800/50 rounded-lg p-3">
                              <h5 className="font-medium text-white text-sm">{subFeature.title}</h5>
                              <p className="text-xs text-slate-400 mt-1">{subFeature.description}</p>
                              <p className="text-xs text-green-400 mt-2">{subFeature.creditCost}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Includes/Features list */}
                    {feature.includes && (
                      <div>
                        <h4 className="font-medium text-white mb-2">What's Included</h4>
                        <ul className="grid grid-cols-2 gap-2">
                          {feature.includes.map((item, idx) => (
                            <li key={idx} className="text-sm text-slate-400 flex gap-2">
                              <span className="text-green-400">✓</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Account Section */}
        <div className="mt-8 space-y-4">
          <h2 className="text-xl font-bold text-white mb-4">Account & Billing</h2>
          
          {/* Credits */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-purple-400" />
              Understanding Credits
            </h3>
            <div className="space-y-2">
              {manual?.account?.credits?.howItWorks?.map((item, idx) => (
                <p key={idx} className="text-sm text-slate-400">• {item}</p>
              ))}
            </div>
          </div>
          
          {/* Subscription */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <Shield className="w-5 h-5 text-green-400" />
              Subscription Plans
            </h3>
            <div className="grid md:grid-cols-3 gap-4">
              {manual?.account?.subscription?.plans?.map((plan, idx) => (
                <div key={idx} className="bg-slate-800/50 rounded-lg p-4">
                  <h4 className="font-medium text-white">{plan.name}</h4>
                  <p className="text-purple-400 font-bold">{plan.price}</p>
                  <p className="text-sm text-slate-400">{plan.credits} credits</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Troubleshooting */}
        <div className="mt-8">
          <h2 className="text-xl font-bold text-white mb-4">Troubleshooting</h2>
          <div className="space-y-3">
            {manual?.troubleshooting?.common_issues?.map((item, idx) => (
              <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <h4 className="font-medium text-red-400 mb-2">{item.issue}</h4>
                <p className="text-sm text-slate-300">{item.solution}</p>
              </div>
            ))}
          </div>
          
          <div className="mt-4 bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
            <p className="text-sm text-slate-300">
              Need more help? Contact us at{' '}
              <a href={`mailto:${manual?.troubleshooting?.contact?.email}`} className="text-purple-400 hover:underline">
                {manual?.troubleshooting?.contact?.email}
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
