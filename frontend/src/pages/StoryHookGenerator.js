import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, AlertTriangle, BookOpen, Pen, Download, Zap, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const StoryHookGenerator = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [copied, setCopied] = useState(null);
  
  // Form state
  const [genre, setGenre] = useState('Fantasy');
  const [tone, setTone] = useState('suspenseful');
  const [characterType, setCharacterType] = useState('hero');
  const [setting, setSetting] = useState('urban');
  
  // Results
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/story-hook-generator/config`);
      if (res.ok) setConfig(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/story-hook-generator/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          genre,
          tone,
          character_type: characterType,
          setting
        })
      });
      
      const data = await res.json();
      
      if (res.ok && data.success) {
        setResult(data);
        toast.success(`Generated in ${data.generation_time_ms}ms!`);
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (e) {
      toast.error('Failed to generate');
    } finally {
      setGenerating(false);
    }
  };

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
    toast.success('Copied!');
  };

  const downloadAll = () => {
    if (!result) return;
    const content = `STORY HOOKS - ${genre.toUpperCase()}\n${'='.repeat(50)}\n\nOPENING HOOKS:\n${result.hooks.map((h, i) => `${i+1}. ${h}`).join('\n')}\n\n\nCLIFFHANGERS:\n${result.cliffhangers.map((c, i) => `${i+1}. ${c}`).join('\n')}\n\n\nPLOT TWISTS:\n${result.plot_twists.map((t, i) => `${i+1}. ${t}`).join('\n')}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${genre.toLowerCase()}-story-hooks.txt`;
    a.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
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
                <Pen className="w-6 h-6 text-purple-400" />
                Story Hook Generator
              </h1>
              <p className="text-slate-400 text-sm">Create captivating hooks for fiction writers</p>
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
              <li>Select your story genre</li>
              <li>Choose the tone</li>
              <li>Pick character type and setting</li>
              <li>Click generate</li>
              <li>Use hooks in your first chapter</li>
            </ol>
          </div>
        )}

        {/* Copyright Disclaimer */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-6 flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-amber-200 text-sm">
            All generated content is original. No copyrighted characters, settings, or IP references are used.
          </p>
        </div>

        {/* Generator Form */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
          <div className="space-y-4">
            {/* Genre & Tone */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Genre</label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="genre-select"
                >
                  {config?.genres?.map(g => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Tone</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="tone-select"
                >
                  {config?.tones?.map(t => (
                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Character & Setting */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Character Type</label>
                <select
                  value={characterType}
                  onChange={(e) => setCharacterType(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="character-select"
                >
                  {config?.character_types?.map(c => (
                    <option key={c} value={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Setting</label>
                <select
                  value={setting}
                  onChange={(e) => setSetting(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="setting-select"
                >
                  {config?.settings?.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-medium py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="generate-btn"
            >
              {generating ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  Generating Hooks...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Generate Story Hooks (8 Credits)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-white">Your Story Hooks</h2>
              <button
                onClick={downloadAll}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm"
              >
                <Download className="w-4 h-4" /> Download All
              </button>
            </div>

            {/* Opening Hooks */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" /> High-Tension Opening Hooks (10)
              </h3>
              <div className="space-y-3">
                {result.hooks?.map((hook, i) => (
                  <div key={i} className="flex items-start justify-between bg-slate-800/50 rounded-xl p-4">
                    <div className="flex-1">
                      <span className="text-purple-400 font-medium mr-2">#{i+1}</span>
                      <span className="text-slate-200">{hook}</span>
                    </div>
                    <button onClick={() => copyText(hook, `hook-${i}`)} className="p-2 hover:bg-slate-700 rounded-lg ml-2">
                      {copied === `hook-${i}` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Cliffhangers */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-400" /> Cliffhanger Lines (5)
              </h3>
              <div className="space-y-3">
                {result.cliffhangers?.map((cliff, i) => (
                  <div key={i} className="flex items-start justify-between bg-slate-800/50 rounded-xl p-4">
                    <div className="flex-1">
                      <span className="text-red-400 font-medium mr-2">#{i+1}</span>
                      <span className="text-slate-200 italic">{cliff}</span>
                    </div>
                    <button onClick={() => copyText(cliff, `cliff-${i}`)} className="p-2 hover:bg-slate-700 rounded-lg ml-2">
                      {copied === `cliff-${i}` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Plot Twists */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-400" /> Plot Twist Ideas (3)
              </h3>
              <div className="space-y-3">
                {result.plot_twists?.map((twist, i) => (
                  <div key={i} className="flex items-start justify-between bg-slate-800/50 rounded-xl p-4">
                    <div className="flex-1">
                      <span className="text-cyan-400 font-medium mr-2">#{i+1}</span>
                      <span className="text-slate-200">{twist}</span>
                    </div>
                    <button onClick={() => copyText(twist, `twist-${i}`)} className="p-2 hover:bg-slate-700 rounded-lg ml-2">
                      {copied === `twist-${i}` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-xs">
          Copyright 2026 CreatorStudio AI. All rights reserved.
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="story-hook-generator" />
    </div>
  );
};

export default StoryHookGenerator;
