import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { Flame, Zap, Lock, ArrowRight, Eye, ChevronDown, Sparkles } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const NICHE_GRADIENTS = {
  Tech: 'from-sky-600 to-cyan-500', Finance: 'from-emerald-600 to-green-500',
  Fitness: 'from-rose-600 to-red-500', Food: 'from-amber-600 to-yellow-500',
  Travel: 'from-violet-600 to-purple-500', Fashion: 'from-pink-600 to-rose-500',
  Gaming: 'from-indigo-600 to-blue-500', Education: 'from-teal-600 to-cyan-500',
  Business: 'from-slate-600 to-gray-500', Lifestyle: 'from-orange-600 to-amber-500',
  Health: 'from-lime-600 to-green-500', Entertainment: 'from-fuchsia-600 to-purple-500',
};

export default function ViralPackShare() {
  const { jobId } = useParams();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeaser();
  }, [jobId]);

  const fetchTeaser = async () => {
    try {
      const ref = searchParams.get('ref') || '';
      const res = await fetch(`${API_URL}/api/viral-ideas/share/${jobId}?ref=${ref}`);
      if (res.ok) setData(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const getAssetUrl = (url) => {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `${API_URL}${url.startsWith('/api') ? url : `/api${url}`}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-3 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-center px-4">
        <div>
          <Flame className="w-12 h-12 text-orange-500 mx-auto mb-4 opacity-50" />
          <h1 className="text-2xl font-bold text-white mb-2">Pack Not Found</h1>
          <p className="text-slate-400 mb-6">This content pack may have been removed.</p>
          <Link to="/signup" className="px-6 py-3 bg-orange-500 hover:bg-orange-400 text-white font-semibold rounded-xl transition-colors">
            Create Your Own Pack
          </Link>
        </div>
      </div>
    );
  }

  const gradient = NICHE_GRADIENTS[data.niche] || 'from-orange-600 to-red-500';

  return (
    <div className="min-h-screen bg-[#070b14]" data-testid="viral-share-page">
      {/* ===== ABOVE THE FOLD — HOOK ZONE ===== */}
      <div className="relative overflow-hidden">
        {/* Background gradient glow */}
        <div className={`absolute inset-0 bg-gradient-to-b ${gradient} opacity-[0.08]`} />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-gradient-to-r from-orange-500/10 to-red-500/10 blur-3xl" />

        <div className="relative max-w-xl mx-auto px-4 pt-12 pb-8">
          {/* Niche tag */}
          <div className="flex justify-center mb-4">
            <span className={`px-3 py-1 rounded-lg text-xs font-bold bg-gradient-to-r ${gradient} text-white`}>
              {data.niche}
            </span>
          </div>

          {/* Top Hook — BIG AND BOLD */}
          <h1 className="text-3xl sm:text-4xl font-black text-white text-center leading-tight mb-6" data-testid="share-hook">
            {data.top_hook || data.idea}
          </h1>

          {/* Curiosity overlay */}
          <p className="text-center text-orange-300/80 text-sm font-medium mb-8">
            Wait till you see the full breakdown...
          </p>

          {/* Thumbnail — partially visible with blur overlay */}
          {data.thumbnail_url && (
            <div className="relative rounded-2xl overflow-hidden mb-8 mx-auto max-w-sm" data-testid="share-thumbnail">
              <img
                src={getAssetUrl(data.thumbnail_url)}
                alt="Content preview"
                className="w-full"
                style={{ filter: 'blur(3px) brightness(0.8)' }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#070b14] via-transparent to-transparent" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex items-center gap-2 px-4 py-2 bg-black/60 backdrop-blur-sm rounded-xl border border-white/10">
                  <Eye className="w-4 h-4 text-orange-400" />
                  <span className="text-sm text-white font-medium">Full pack inside</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===== TEASER CONTENT ===== */}
      <div className="max-w-xl mx-auto px-4 space-y-6">
        {/* Partial script preview */}
        {data.script_teaser && (
          <div className="relative" data-testid="share-script-teaser">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Script Preview</span>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{data.script_teaser}</p>
            </div>
            {/* Fade out */}
            <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-[#070b14] to-transparent rounded-b-2xl flex items-end justify-center pb-2">
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <ChevronDown className="w-3 h-3" />
                Full script unlocked inside
              </div>
            </div>
          </div>
        )}

        {/* Partial caption */}
        {data.caption_teaser && (
          <div className="bg-slate-900/60 border border-slate-800/60 rounded-xl p-4">
            <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wider">Caption Preview</p>
            <p className="text-sm text-slate-400 truncate">{data.caption_teaser}</p>
          </div>
        )}

        {/* ===== PRIMARY CTA ===== */}
        <div className="space-y-3 pt-4" data-testid="share-ctas">
          <Link
            to="/signup"
            className="w-full flex items-center justify-center gap-2 py-4 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white text-lg font-bold rounded-2xl shadow-xl shadow-orange-500/25 transition-all"
            data-testid="share-cta-generate"
          >
            <Sparkles className="w-5 h-5" />
            Generate Your Own Free Pack
          </Link>

          <Link
            to="/login"
            className="w-full flex items-center justify-center gap-2 py-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl border border-slate-700/60 transition-colors"
            data-testid="share-cta-unlock"
          >
            <Lock className="w-4 h-4" />
            Unlock Full Pack
          </Link>
        </div>

        {/* ===== SOCIAL PROOF ===== */}
        <div className="text-center py-6 space-y-2" data-testid="share-social-proof">
          <p className="text-sm text-slate-500">
            <span className="text-orange-400 font-bold">{(data.total_packs_generated || 0).toLocaleString()}+</span> packs generated
          </p>
          <p className="text-xs text-slate-600">Creators using this to grow faster</p>
        </div>

        {/* Speed proof */}
        <div className="bg-slate-900/40 border border-slate-800/40 rounded-xl p-4 text-center mb-8">
          <p className="text-sm text-slate-400">
            This took <span className="text-white font-semibold">30 seconds</span> to generate.
            <Link to="/signup" className="text-orange-400 hover:text-orange-300 ml-1 font-medium">
              Try your own <ArrowRight className="w-3 h-3 inline" />
            </Link>
          </p>
        </div>

        {/* Footer */}
        <div className="text-center pb-8">
          <Link to="/" className="flex items-center justify-center gap-2 text-xs text-slate-600 hover:text-slate-400 transition-colors">
            <Flame className="w-3 h-3" /> Viral Idea Drop
          </Link>
        </div>
      </div>
    </div>
  );
}
