import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, AlertTriangle, BookOpen, Type, Zap, Download } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const YouTubeThumbnailGenerator = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [copied, setCopied] = useState(null);
  
  // Form state
  const [topic, setTopic] = useState('');
  const [niche, setNiche] = useState('general');
  const [emotion, setEmotion] = useState('curiosity');
  
  // Results
  const [thumbnails, setThumbnails] = useState([]);
  const [generationTime, setGenerationTime] = useState(0);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/youtube-thumbnail-generator/config`);
      if (res.ok) {
        setConfig(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!topic.trim()) {
      toast.error('Please enter a topic');
      return;
    }
    
    setGenerating(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/youtube-thumbnail-generator/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ topic, niche, emotion })
      });
      
      const data = await res.json();
      
      if (res.ok && data.success) {
        setThumbnails(data.thumbnails);
        setGenerationTime(data.generation_time_ms);
        toast.success(`Generated 10 thumbnails in ${data.generation_time_ms}ms!`);
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (e) {
      toast.error('Failed to generate');
    } finally {
      setGenerating(false);
    }
  };

  const copyText = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopied(index);
    setTimeout(() => setCopied(null), 2000);
    toast.success('Copied!');
  };

  const downloadAll = () => {
    const content = thumbnails.map((t, i) => 
      `${i + 1}.\nOriginal: ${t.original}\nALL CAPS: ${t.all_caps}\nTitle Case: ${t.title_case}\nBold Short: ${t.bold_short}\n`
    ).join('\n---\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'thumbnail-texts.txt';
    a.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <Type className="w-6 h-6 text-red-400" />
                YouTube Thumbnail Text Generator
              </h1>
              <p className="text-slate-400 text-sm">Generate 10 high-converting thumbnail phrases</p>
            </div>
          </div>
          <button
            onClick={() => setShowManual(!showManual)}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg text-slate-300 hover:bg-slate-700 text-sm"
          >
            <BookOpen className="w-4 h-4" /> User Manual
          </button>
        </div>

        {/* User Manual */}
        {showManual && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
            <h3 className="text-lg font-bold text-white mb-4">How to Use</h3>
            <ol className="space-y-2 text-slate-300 text-sm list-decimal list-inside">
              <li>Enter your video topic (e.g., "Morning Routine")</li>
              <li>Choose your niche category</li>
              <li>Select the emotion you want to evoke</li>
              <li>Click Generate</li>
              <li>Pick the best text for your thumbnail</li>
            </ol>
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
              <h4 className="text-green-400 font-medium mb-2">Best Practices</h4>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>✔ Keep under 4 words</li>
                <li>✔ Use emotional trigger</li>
                <li>✔ Avoid too many emojis</li>
              </ul>
            </div>
          </div>
        )}

        {/* Copyright Disclaimer */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-6 flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-amber-200 text-sm">
            All generated content is original and generic. Do not include copyrighted or trademarked content.
          </p>
        </div>

        {/* Generator Form */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
          <div className="space-y-4">
            {/* Topic Input */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Video Topic *</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., Morning Routine, Productivity Tips, Crypto Trading"
                maxLength={100}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500"
                data-testid="topic-input"
              />
              <p className="text-xs text-slate-500 mt-1">{topic.length}/100</p>
            </div>

            {/* Niche & Emotion */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Niche</label>
                <select
                  value={niche}
                  onChange={(e) => setNiche(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="niche-select"
                >
                  {config?.niches?.map(n => (
                    <option key={n} value={n}>{n.charAt(0).toUpperCase() + n.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Emotion</label>
                <select
                  value={emotion}
                  onChange={(e) => setEmotion(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="emotion-select"
                >
                  {config?.emotions?.map(e => (
                    <option key={e} value={e}>{e.charAt(0).toUpperCase() + e.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={generating || !topic.trim()}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white font-medium py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="generate-btn"
            >
              {generating ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Generate Thumbnails (5 Credits)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {thumbnails.length > 0 && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-xl font-bold text-white">Your Thumbnail Texts</h2>
                <p className="text-slate-400 text-sm">Generated in {generationTime}ms</p>
              </div>
              <button
                onClick={downloadAll}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm"
              >
                <Download className="w-4 h-4" /> Download All
              </button>
            </div>

            <div className="space-y-4">
              {thumbnails.map((thumb, index) => (
                <div key={index} className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <span className="text-red-400 font-medium">#{index + 1}</span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Original */}
                    <div className="flex items-center justify-between bg-slate-900/50 rounded-lg p-3">
                      <div>
                        <span className="text-xs text-slate-500 block">Original</span>
                        <span className="text-white">{thumb.original}</span>
                      </div>
                      <button
                        onClick={() => copyText(thumb.original, `${index}-orig`)}
                        className="p-2 hover:bg-slate-700 rounded-lg"
                      >
                        {copied === `${index}-orig` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                      </button>
                    </div>
                    
                    {/* ALL CAPS */}
                    <div className="flex items-center justify-between bg-slate-900/50 rounded-lg p-3">
                      <div>
                        <span className="text-xs text-slate-500 block">ALL CAPS</span>
                        <span className="text-white font-bold">{thumb.all_caps}</span>
                      </div>
                      <button
                        onClick={() => copyText(thumb.all_caps, `${index}-caps`)}
                        className="p-2 hover:bg-slate-700 rounded-lg"
                      >
                        {copied === `${index}-caps` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                      </button>
                    </div>
                    
                    {/* Title Case */}
                    <div className="flex items-center justify-between bg-slate-900/50 rounded-lg p-3">
                      <div>
                        <span className="text-xs text-slate-500 block">Title Case</span>
                        <span className="text-white">{thumb.title_case}</span>
                      </div>
                      <button
                        onClick={() => copyText(thumb.title_case, `${index}-title`)}
                        className="p-2 hover:bg-slate-700 rounded-lg"
                      >
                        {copied === `${index}-title` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                      </button>
                    </div>
                    
                    {/* Bold Short */}
                    <div className="flex items-center justify-between bg-slate-900/50 rounded-lg p-3">
                      <div>
                        <span className="text-xs text-slate-500 block">Bold Short</span>
                        <span className="text-white font-black">{thumb.bold_short}</span>
                      </div>
                      <button
                        onClick={() => copyText(thumb.bold_short, `${index}-short`)}
                        className="p-2 hover:bg-slate-700 rounded-lg"
                      >
                        {copied === `${index}-short` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-xs">
          Copyright 2026 CreatorStudio AI. All rights reserved.
        </div>
      </div>
    </div>
  );
};

export default YouTubeThumbnailGenerator;
