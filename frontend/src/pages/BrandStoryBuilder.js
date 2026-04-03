import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Sparkles, Copy, Check, Download, FileText, Archive,
  Palette, Type, Lightbulb, Target, Megaphone, Globe2, Zap, Crown,
  ChevronRight, RefreshCw, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ─── Stage definitions ───
const STAGES = [
  { key: 'ENRICHING', label: 'Understanding your brand', icon: Lightbulb },
  { key: 'TEXT_GENERATING', label: 'Crafting story & messaging', icon: FileText },
  { key: 'VISUAL_PLANNING', label: 'Designing visual identity', icon: Palette },
  { key: 'PACKAGING', label: 'Packaging your brand kit', icon: Archive },
  { key: 'COMPLETE', label: 'Brand kit ready', icon: Check },
];

const STAGE_ORDER = STAGES.map(s => s.key);

// ─── Artifact display config ───
const ARTIFACT_CONFIG = {
  short_brand_story: { label: 'Short Brand Story', icon: FileText, tab: 'story' },
  long_brand_story: { label: 'Full Brand Story', icon: FileText, tab: 'story' },
  mission_vision_values: { label: 'Mission, Vision & Values', icon: Target, tab: 'story' },
  taglines: { label: 'Taglines', icon: Megaphone, tab: 'story' },
  elevator_pitch: { label: 'Elevator Pitch', icon: Zap, tab: 'story' },
  website_hero: { label: 'Website Hero Copy', icon: Globe2, tab: 'marketing' },
  social_ad_copy: { label: 'Social Ad Copy', icon: Megaphone, tab: 'marketing' },
  color_palettes: { label: 'Color Palettes', icon: Palette, tab: 'identity' },
  typography: { label: 'Typography', icon: Type, tab: 'identity' },
  logo_concepts: { label: 'Logo Concepts', icon: Lightbulb, tab: 'identity' },
};

const TABS = [
  { key: 'story', label: 'Story & Messaging' },
  { key: 'marketing', label: 'Marketing Copy' },
  { key: 'identity', label: 'Visual Identity' },
];

// ─── Tone chip config ───
const TONE_CHIPS = [
  { value: 'professional', label: 'Professional' },
  { value: 'bold', label: 'Bold' },
  { value: 'luxury', label: 'Luxury' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'emotional', label: 'Emotional' },
  { value: 'gen-z', label: 'Gen-Z' },
  { value: 'startup', label: 'Startup' },
  { value: 'premium', label: 'Premium' },
];

const PERSONALITY_CHIPS = [
  { value: 'innovative', label: 'Innovative' },
  { value: 'trustworthy', label: 'Trustworthy' },
  { value: 'playful', label: 'Playful' },
  { value: 'sophisticated', label: 'Sophisticated' },
  { value: 'disruptive', label: 'Disruptive' },
  { value: 'warm', label: 'Warm' },
  { value: 'authoritative', label: 'Authoritative' },
  { value: 'minimalist', label: 'Minimalist' },
];

export default function BrandStoryBuilder() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(null);

  // Form state
  const [businessName, setBusinessName] = useState('');
  const [mission, setMission] = useState('');
  const [founderStory, setFounderStory] = useState('');
  const [industry, setIndustry] = useState('Technology');
  const [tone, setTone] = useState('professional');
  const [audience, setAudience] = useState('');
  const [personality, setPersonality] = useState('');
  const [competitors, setCompetitors] = useState('');
  const [market, setMarket] = useState('Global');
  const [problemSolved, setProblemSolved] = useState('');
  const [mode, setMode] = useState('pro');

  // Job state
  const [phase, setPhase] = useState('input'); // input | generating | results
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobResult, setJobResult] = useState(null);
  const [activeTab, setActiveTab] = useState('story');
  const pollRef = useRef(null);

  useEffect(() => {
    fetchConfig();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/brand-story-builder/config`);
      if (res.ok) setConfig(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleGenerate = async () => {
    if (!businessName.trim()) { toast.error('Business name is required'); return; }
    setPhase('generating');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/brand-story-builder/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_name: businessName, mission, founder_story: founderStory,
          industry, tone, audience, personality, competitors, market,
          problem_solved: problemSolved, mode,
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setJobId(data.jobId);
        toast.success('Generation started!');
        startPolling(data.jobId);
      } else {
        toast.error(data.detail || 'Generation failed');
        setPhase('input');
      }
    } catch (e) { toast.error('Failed to start generation'); setPhase('input'); }
  };

  const startPolling = useCallback((id) => {
    const poll = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_URL}/api/brand-story-builder/job/${id}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setJobStatus(data);
          if (data.status === 'READY' || data.status === 'PARTIAL_READY' || data.status === 'FAILED') {
            clearInterval(pollRef.current);
            // Fetch full results
            const resResult = await fetch(`${API_URL}/api/brand-story-builder/job/${id}/result`, {
              headers: { 'Authorization': `Bearer ${token}` },
            });
            if (resResult.ok) {
              const resultData = await resResult.json();
              setJobResult(resultData);
              setPhase('results');
              toast.success(data.status === 'FAILED' ? 'Some outputs failed — showing what we have' : 'Brand kit ready!');
            }
          }
        }
      } catch (e) { console.error('Poll error:', e); }
    };
    poll();
    pollRef.current = setInterval(poll, 2000);
  }, []);

  const copyText = (text, id) => {
    navigator.clipboard.writeText(typeof text === 'string' ? text : JSON.stringify(text, null, 2));
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
    toast.success('Copied!');
  };

  const handleDownloadPdf = async () => {
    if (!jobId) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/brand-story-builder/job/${jobId}/pdf`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${businessName.replace(/\s+/g, '_')}_brand_kit.pdf`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('PDF downloaded!');
      } else { toast.error('PDF download failed'); }
    } catch { toast.error('PDF download failed'); }
  };

  const handleDownloadZip = async () => {
    if (!jobId) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/brand-story-builder/job/${jobId}/zip`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${businessName.replace(/\s+/g, '_')}_brand_kit.zip`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('ZIP downloaded!');
      } else { toast.error('ZIP download failed'); }
    } catch { toast.error('ZIP download failed'); }
  };

  const handleDownloadTxt = () => {
    if (!jobResult) return;
    let txt = `=== ${businessName} BRAND KIT ===\n\n`;
    const outputs = jobResult.outputs || {};
    for (const [key, art] of Object.entries(outputs)) {
      if (art.status === 'READY' || art.status === 'FALLBACK_READY') {
        txt += `--- ${key.toUpperCase().replace(/_/g, ' ')} ---\n`;
        txt += JSON.stringify(art.data, null, 2) + '\n\n';
      }
    }
    const blob = new Blob([txt], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${businessName.replace(/\s+/g, '_')}_brand_kit.txt`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    toast.success('TXT downloaded!');
  };

  const creditCost = mode === 'fast' ? 10 : 25;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#060612] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // PHASE: GENERATING (Progress UI)
  // ═══════════════════════════════════════════════════════════════
  if (phase === 'generating') {
    const currentStageIdx = jobStatus ? STAGE_ORDER.indexOf(jobStatus.current_stage) : 0;
    const progress = jobStatus?.progress || 0;
    const artifacts = jobStatus?.artifacts || {};

    return (
      <div className="min-h-screen bg-[#060612] flex items-center justify-center px-4">
        <div className="max-w-lg w-full">
          <div className="text-center mb-10">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-white animate-pulse" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2" data-testid="generating-title">
              Building your brand universe...
            </h2>
            <p className="text-slate-400 text-sm">{businessName} | {mode.toUpperCase()} Mode</p>
          </div>

          {/* Progress bar */}
          <div className="mb-8">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-purple-600 rounded-full transition-all duration-700"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Stages */}
          <div className="space-y-3" data-testid="generation-stages">
            {STAGES.map((stage, i) => {
              const isActive = i === currentStageIdx;
              const isDone = i < currentStageIdx;
              const Icon = stage.icon;
              return (
                <div
                  key={stage.key}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-500 ${
                    isDone ? 'bg-green-900/20 border border-green-800/30' :
                    isActive ? 'bg-blue-900/20 border border-blue-700/40 shadow-lg shadow-blue-900/20' :
                    'bg-slate-900/30 border border-slate-800/40 opacity-40'
                  }`}
                  data-testid={`stage-${stage.key}`}
                >
                  {isDone ? (
                    <Check className="w-5 h-5 text-green-400" />
                  ) : isActive ? (
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5 text-slate-600" />
                  )}
                  <span className={`text-sm font-medium ${
                    isDone ? 'text-green-300' : isActive ? 'text-blue-300' : 'text-slate-600'
                  }`}>{stage.label}</span>
                </div>
              );
            })}
          </div>

          {/* Live artifact cards */}
          {Object.keys(artifacts).length > 0 && (
            <div className="mt-8">
              <p className="text-xs text-slate-500 mb-3 uppercase tracking-wider">Artifacts</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(artifacts).map(([key, art]) => {
                  const cfg = ARTIFACT_CONFIG[key];
                  if (!cfg) return null;
                  const ready = art.status === 'READY' || art.status === 'FALLBACK_READY';
                  return (
                    <span key={key} className={`text-xs px-3 py-1.5 rounded-full border ${
                      ready ? 'bg-green-900/30 border-green-700/40 text-green-300' :
                      art.status === 'PROCESSING' ? 'bg-blue-900/30 border-blue-700/40 text-blue-300 animate-pulse' :
                      art.status === 'FAILED' ? 'bg-red-900/30 border-red-700/40 text-red-400' :
                      'bg-slate-800/50 border-slate-700/40 text-slate-500'
                    }`}>
                      {ready && <Check className="w-3 h-3 inline mr-1" />}
                      {cfg.label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // PHASE: RESULTS (Dashboard)
  // ═══════════════════════════════════════════════════════════════
  if (phase === 'results' && jobResult) {
    const outputs = jobResult.outputs || {};
    const readyCount = Object.values(outputs).filter(a => a.status === 'READY' || a.status === 'FALLBACK_READY').length;
    const totalCount = Object.keys(outputs).length;

    return (
      <div className="min-h-screen bg-[#060612] py-6 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <button onClick={() => { setPhase('input'); setJobId(null); setJobResult(null); setJobStatus(null); }}
                className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700" data-testid="back-to-input">
                <ArrowLeft className="w-5 h-5 text-slate-400" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-white" data-testid="results-title">{businessName} Brand Kit</h1>
                <p className="text-slate-400 text-xs">{readyCount}/{totalCount} outputs ready | {mode.toUpperCase()} mode</p>
              </div>
            </div>
            <button onClick={() => { setPhase('input'); setJobId(null); setJobResult(null); setJobStatus(null); }}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm"
              data-testid="new-kit-btn">
              <RefreshCw className="w-4 h-4" /> New Kit
            </button>
          </div>

          {/* Download bar */}
          <div className="flex gap-3 mb-6 p-4 bg-slate-900/60 border border-slate-800 rounded-xl" data-testid="download-bar">
            <Button onClick={handleDownloadPdf} className="bg-emerald-600 hover:bg-emerald-500 text-sm" data-testid="download-pdf">
              <Download className="w-4 h-4 mr-1.5" /> Download PDF
            </Button>
            <Button onClick={handleDownloadZip} variant="outline" className="border-slate-700 text-slate-300 hover:text-white text-sm" data-testid="download-zip">
              <Archive className="w-4 h-4 mr-1.5" /> Download ZIP
            </Button>
            <Button onClick={handleDownloadTxt} variant="outline" className="border-slate-700 text-slate-300 hover:text-white text-sm" data-testid="download-txt">
              <FileText className="w-4 h-4 mr-1.5" /> Download TXT
            </Button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-slate-900/60 p-1 rounded-lg border border-slate-800" data-testid="result-tabs">
            {TABS.filter(t => {
              // Only show tabs that have ready artifacts
              return Object.entries(outputs).some(([k, a]) =>
                ARTIFACT_CONFIG[k]?.tab === t.key && (a.status === 'READY' || a.status === 'FALLBACK_READY')
              );
            }).map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
                data-testid={`tab-${tab.key}`}>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Artifact cards */}
          <div className="space-y-4">
            {Object.entries(outputs)
              .filter(([key]) => ARTIFACT_CONFIG[key]?.tab === activeTab)
              .map(([key, art]) => {
                if (art.status !== 'READY' && art.status !== 'FALLBACK_READY') return null;
                const cfg = ARTIFACT_CONFIG[key];
                const Icon = cfg?.icon || FileText;
                return (
                  <div key={key} className="bg-slate-900/60 border border-slate-800 rounded-xl p-5" data-testid={`artifact-${key}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Icon className="w-5 h-5 text-blue-400" />
                        <h3 className="font-semibold text-white text-base">{cfg?.label || key}</h3>
                        {art.status === 'FALLBACK_READY' && (
                          <span className="text-xs bg-amber-900/30 text-amber-400 px-2 py-0.5 rounded">fallback</span>
                        )}
                      </div>
                      <button onClick={() => copyText(art.data, key)} className="p-2 hover:bg-slate-700 rounded-lg" data-testid={`copy-${key}`}>
                        {copied === key ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                      </button>
                    </div>
                    <ArtifactRenderer type={key} data={art.data} />
                  </div>
                );
              })}
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // PHASE: INPUT (Form)
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-[#060612] py-6 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link to="/app" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
              <Sparkles className="w-6 h-6 text-blue-400" />
              AI Brand Kit Generator
            </h1>
            <p className="text-slate-400 text-sm">Build your entire brand identity in minutes</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Form */}
          <div className="lg:col-span-2 space-y-5">
            {/* Core info */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Target className="w-4 h-4 text-blue-400" /> Core Brand Info
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Business Name *</label>
                  <input type="text" value={businessName} onChange={e => setBusinessName(e.target.value)}
                    placeholder="e.g., Visionary Suite" maxLength={100}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                    data-testid="business-name-input" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">Industry</label>
                    <select value={industry} onChange={e => setIndustry(e.target.value)}
                      className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm"
                      data-testid="industry-select">
                      {(config?.industries || []).map(i => <option key={i} value={i}>{i}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">Market</label>
                    <input type="text" value={market} onChange={e => setMarket(e.target.value)}
                      placeholder="Global, US, India..." maxLength={100}
                      className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                      data-testid="market-input" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Mission Statement</label>
                  <textarea value={mission} onChange={e => setMission(e.target.value)}
                    placeholder="What is your mission? What do you aim to achieve?" maxLength={500} rows={2}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                    data-testid="mission-input" />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Founder Story</label>
                  <textarea value={founderStory} onChange={e => setFounderStory(e.target.value)}
                    placeholder="Share the journey — what inspired you to start?" maxLength={500} rows={3}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                    data-testid="founder-story-input" />
                </div>
              </div>
            </div>

            {/* Strategy inputs */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-purple-400" /> Brand Strategy
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Target Audience</label>
                  <input type="text" value={audience} onChange={e => setAudience(e.target.value)}
                    placeholder="e.g., Founders, creators, small businesses" maxLength={300}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                    data-testid="audience-input" />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Core Problem Solved</label>
                  <input type="text" value={problemSolved} onChange={e => setProblemSolved(e.target.value)}
                    placeholder="e.g., Making professional branding accessible" maxLength={300}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                    data-testid="problem-input" />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1.5">Competitors (optional)</label>
                  <input type="text" value={competitors} onChange={e => setCompetitors(e.target.value)}
                    placeholder="e.g., Canva, Looka, Wix" maxLength={300}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                    data-testid="competitors-input" />
                </div>
              </div>
            </div>

            {/* Tone & Personality chips */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Palette className="w-4 h-4 text-cyan-400" /> Tone & Personality
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Tone</label>
                  <div className="flex flex-wrap gap-2" data-testid="tone-chips">
                    {TONE_CHIPS.map(t => (
                      <button key={t.value} onClick={() => setTone(t.value)}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                          tone === t.value
                            ? 'bg-blue-600 border-blue-500 text-white'
                            : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                        }`}
                        data-testid={`tone-${t.value}`}>
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Brand Personality</label>
                  <div className="flex flex-wrap gap-2" data-testid="personality-chips">
                    {PERSONALITY_CHIPS.map(p => (
                      <button key={p.value} onClick={() => setPersonality(p.value)}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                          personality === p.value
                            ? 'bg-purple-600 border-purple-500 text-white'
                            : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                        }`}
                        data-testid={`personality-${p.value}`}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Sticky sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-4">
              {/* Mode toggle */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4" data-testid="mode-selector">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">Generation Mode</h3>
                <div className="space-y-2">
                  {[
                    { key: 'fast', label: 'Fast', icon: Zap, credits: 10, desc: 'Text essentials', color: 'blue' },
                    { key: 'pro', label: 'Pro', icon: Crown, credits: 25, desc: 'Full brand kit', color: 'purple' },
                  ].map(m => (
                    <button key={m.key} onClick={() => setMode(m.key)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${
                        mode === m.key
                          ? `bg-${m.color}-900/30 border-${m.color}-700/50 ring-1 ring-${m.color}-500/30`
                          : 'bg-slate-800/40 border-slate-700/40 hover:border-slate-600'
                      }`}
                      data-testid={`mode-${m.key}`}>
                      <m.icon className={`w-5 h-5 ${mode === m.key ? 'text-blue-400' : 'text-slate-500'}`} />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className={`text-sm font-semibold ${mode === m.key ? 'text-white' : 'text-slate-400'}`}>{m.label}</span>
                          <span className={`text-xs ${mode === m.key ? 'text-blue-400' : 'text-slate-500'}`}>{m.credits} credits</span>
                        </div>
                        <span className="text-xs text-slate-500">{m.desc}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* What you'll get */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">What you'll get</h3>
                <div className="space-y-1.5">
                  {(config?.modes?.[mode]?.artifacts || []).map(a => {
                    const cfg = ARTIFACT_CONFIG[a];
                    return cfg ? (
                      <div key={a} className="flex items-center gap-2 text-xs text-slate-400">
                        <ChevronRight className="w-3 h-3 text-blue-400" />
                        <span>{cfg.label}</span>
                      </div>
                    ) : null;
                  })}
                  <div className="flex items-center gap-2 text-xs text-slate-400 mt-2 pt-2 border-t border-slate-800">
                    <Download className="w-3 h-3 text-emerald-400" />
                    <span>PDF + ZIP + TXT downloads</span>
                  </div>
                </div>
              </div>

              {/* Generate CTA */}
              <button onClick={handleGenerate} disabled={!businessName.trim()}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold py-4 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-900/30"
                data-testid="generate-btn">
                <Sparkles className="w-5 h-5" />
                Build Brand Kit ({creditCost} Credits)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ─── Artifact Renderer ───
function ArtifactRenderer({ type, data }) {
  if (!data) return <p className="text-slate-500 text-sm">No data available</p>;

  switch (type) {
    case 'short_brand_story':
      return <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{data.short_brand_story}</p>;
    case 'long_brand_story':
      return <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{data.long_brand_story}</p>;
    case 'mission_vision_values':
      return (
        <div className="space-y-4">
          {data.mission && <div><h4 className="text-blue-400 font-semibold text-sm mb-1">Mission</h4><p className="text-slate-300 text-sm">{data.mission}</p></div>}
          {data.vision && <div><h4 className="text-purple-400 font-semibold text-sm mb-1">Vision</h4><p className="text-slate-300 text-sm">{data.vision}</p></div>}
          {data.values && <div><h4 className="text-cyan-400 font-semibold text-sm mb-1">Values</h4><div className="flex flex-wrap gap-2">{data.values.map((v, i) => <span key={i} className="px-3 py-1 bg-slate-800 border border-slate-700 rounded-full text-xs text-slate-300">{v}</span>)}</div></div>}
        </div>
      );
    case 'taglines':
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {(data.taglines || []).map((t, i) => {
            const text = typeof t === 'string' ? t : t.text;
            const style = typeof t === 'string' ? '' : t.style;
            return (
              <div key={i} className="flex items-center justify-between px-3 py-2 bg-slate-800/60 rounded-lg border border-slate-700/50">
                <span className="text-slate-200 text-sm font-medium">"{text}"</span>
                {style && <span className="text-xs text-slate-500 ml-2">{style}</span>}
              </div>
            );
          })}
        </div>
      );
    case 'elevator_pitch':
      return (
        <div className="space-y-3">
          {data.one_line && <div><h4 className="text-amber-400 font-semibold text-xs mb-1">One-Liner</h4><p className="text-slate-300 text-sm">{data.one_line}</p></div>}
          {data.thirty_sec && <div><h4 className="text-amber-400 font-semibold text-xs mb-1">30-Second</h4><p className="text-slate-300 text-sm">{data.thirty_sec}</p></div>}
          {data.sixty_sec && <div><h4 className="text-amber-400 font-semibold text-xs mb-1">60-Second</h4><p className="text-slate-300 text-sm">{data.sixty_sec}</p></div>}
        </div>
      );
    case 'website_hero':
      return (
        <div className="space-y-3 p-4 bg-slate-800/40 rounded-lg border border-slate-700/50">
          {data.headline && <h3 className="text-white font-bold text-lg">{data.headline}</h3>}
          {data.subheadline && <p className="text-slate-300 text-sm">{data.subheadline}</p>}
          {data.cta && <span className="inline-block bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">{data.cta}</span>}
          {data.trust_bullets && <div className="flex flex-wrap gap-2 mt-2">{data.trust_bullets.map((b, i) => <span key={i} className="text-xs text-slate-400 flex items-center gap-1"><Check className="w-3 h-3 text-green-400" />{b}</span>)}</div>}
        </div>
      );
    case 'social_ad_copy':
      return (
        <div className="space-y-3">
          {data.instagram?.length > 0 && <div><h4 className="text-pink-400 font-semibold text-xs mb-1.5">Instagram</h4>{data.instagram.map((c, i) => <p key={i} className="text-slate-300 text-sm mb-1 pl-3 border-l-2 border-pink-800">{c}</p>)}</div>}
          {data.facebook?.length > 0 && <div><h4 className="text-blue-400 font-semibold text-xs mb-1.5">Facebook</h4>{data.facebook.map((c, i) => <p key={i} className="text-slate-300 text-sm mb-1 pl-3 border-l-2 border-blue-800">{c}</p>)}</div>}
          {data.cta_lines?.length > 0 && <div><h4 className="text-emerald-400 font-semibold text-xs mb-1.5">CTA Lines</h4><div className="flex flex-wrap gap-2">{data.cta_lines.map((c, i) => <span key={i} className="px-3 py-1 bg-slate-800 border border-emerald-800/40 rounded-full text-xs text-emerald-300">{c}</span>)}</div></div>}
        </div>
      );
    case 'color_palettes':
      return (
        <div className="space-y-4">
          {(data.palettes || []).map((p, i) => (
            <div key={i} className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/50">
              <h4 className="text-white font-semibold text-sm mb-2">{p.name}</h4>
              <div className="flex gap-2 mb-2">
                {['primary', 'secondary', 'accent', 'background'].map(key => p[key] ? (
                  <div key={key} className="text-center">
                    <div className="w-12 h-12 rounded-lg border border-slate-600" style={{ backgroundColor: p[key] }} />
                    <span className="text-[10px] text-slate-500 mt-1 block">{p[key]}</span>
                    <span className="text-[10px] text-slate-600">{key}</span>
                  </div>
                ) : null)}
              </div>
              {p.meaning && <p className="text-xs text-slate-400 italic">{p.meaning}</p>}
            </div>
          ))}
        </div>
      );
    case 'typography':
      return (
        <div className="space-y-3">
          {(data.pairings || []).map((p, i) => (
            <div key={i} className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/50">
              <h4 className="text-white font-semibold text-sm mb-1">{p.name}</h4>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                <div><span className="text-slate-500">Heading:</span> {p.heading}</div>
                <div><span className="text-slate-500">Body:</span> {p.body}</div>
              </div>
              {p.personality && <p className="text-xs text-slate-500 mt-1">{p.personality}</p>}
            </div>
          ))}
        </div>
      );
    case 'logo_concepts':
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(data.concepts || []).map((c, i) => (
            <div key={i} className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/50">
              <h4 className="text-white font-semibold text-sm mb-1">{c.name}</h4>
              <p className="text-xs text-slate-400 mb-1"><span className="text-slate-500">Symbol:</span> {c.symbol}</p>
              <p className="text-xs text-slate-400 mb-1"><span className="text-slate-500">Layout:</span> {c.layout}</p>
              <p className="text-xs text-slate-400"><span className="text-slate-500">Feel:</span> {c.feel}</p>
            </div>
          ))}
        </div>
      );
    default:
      return <pre className="text-slate-400 text-xs overflow-auto">{JSON.stringify(data, null, 2)}</pre>;
  }
}
