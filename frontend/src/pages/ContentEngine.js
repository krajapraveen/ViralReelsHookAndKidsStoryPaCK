import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Flame, Sparkles, Play, Trash2, Star, Tag,
  Copy, Filter, RefreshCcw, Send, ChevronDown, Check, X,
  Zap, Eye, BookOpen, TrendingUp, Instagram, Share2, Film
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORIES = [
  { id: 'emotional', label: 'Emotional', color: 'rose' },
  { id: 'mystery', label: 'Mystery', color: 'indigo' },
  { id: 'kids', label: 'Kids', color: 'emerald' },
  { id: 'horror', label: 'Horror', color: 'red' },
  { id: 'viral', label: 'Viral', color: 'amber' },
];

const TAG_COLORS = {
  HIGH_VIRAL: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
  EMOTIONAL_HOOK: 'bg-rose-500/15 text-rose-400 border-rose-500/20',
  FAST_CONVERSION: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  WEAK: 'bg-red-500/15 text-red-400 border-red-500/20',
};

function api() {
  const token = localStorage.getItem('token');
  return axios.create({ headers: { Authorization: `Bearer ${token}` } });
}

export default function ContentEngine() {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);

  // Filters
  const [filterCat, setFilterCat] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterTag, setFilterTag] = useState('');

  // Generate modal
  const [showGenModal, setShowGenModal] = useState(false);
  const [genCount, setGenCount] = useState(10);
  const [genCategories, setGenCategories] = useState([]);
  const [genAutoPublish, setGenAutoPublish] = useState(false);

  // Social scripts modal
  const [socialModal, setSocialModal] = useState(null);

  // Controlled batch
  const [showControlledModal, setShowControlledModal] = useState(false);
  const [controlledGenerating, setControlledGenerating] = useState(false);
  const [batchMetrics, setBatchMetrics] = useState(null);

  // Selected stories
  const [selected, setSelected] = useState(new Set());

  const fetchStories = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterCat) params.set('category', filterCat);
      if (filterStatus) params.set('status', filterStatus);
      if (filterTag) params.set('tag', filterTag);
      params.set('limit', '50');

      const res = await api().get(`${API}/api/content-engine/list?${params}`);
      if (res.data.success) {
        setStories(res.data.stories);
        setStats(res.data.stats);
      }
    } catch (e) {
      toast.error('Failed to load stories');
    }
    setLoading(false);
  }, [filterCat, filterStatus, filterTag]);

  useEffect(() => { fetchStories(); }, [fetchStories]);

  const fetchBatchMetrics = useCallback(async () => {
    try {
      const res = await api().get(`${API}/api/content-engine/batch-metrics`);
      if (res.data.success) setBatchMetrics(res.data);
    } catch {}
  }, []);

  useEffect(() => { fetchBatchMetrics(); }, [fetchBatchMetrics]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api().post(`${API}/api/content-engine/generate`, {
        count: genCount,
        categories: genCategories.length ? genCategories : null,
        auto_publish: genAutoPublish,
      });
      if (res.data.success) {
        toast.success(`Generated ${res.data.generated} stories${res.data.published ? `, published ${res.data.published}` : ''}`);
        setShowGenModal(false);
        fetchStories();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Generation failed');
    }
    setGenerating(false);
  };

  const handlePublish = async (storyId) => {
    try {
      const res = await api().post(`${API}/api/content-engine/publish/${storyId}`);
      if (res.data.success) {
        toast.success('Queued for video generation');
        fetchStories();
      }
    } catch (e) {
      toast.error('Publish failed');
    }
  };

  const handlePublishAll = async () => {
    setPublishing(true);
    try {
      const res = await api().post(`${API}/api/content-engine/publish-batch`);
      if (res.data.success) {
        toast.success(`Published ${res.data.published} stories to pipeline`);
        fetchStories();
      }
    } catch (e) {
      toast.error('Batch publish failed');
    }
    setPublishing(false);
  };

  const [scoring, setScoring] = useState(false);
  const handleScoreAll = async () => {
    setScoring(true);
    try {
      const res = await api().post(`${API}/api/content-engine/score-all`);
      if (res.data.success) {
        toast.success(`Scored ${res.data.total_scored} stories: ${res.data.breakdown?.HIGH || 0} HIGH, ${res.data.breakdown?.MEDIUM || 0} MED, ${res.data.breakdown?.LOW || 0} LOW`);
        fetchStories();
        fetchBatchMetrics();
      }
    } catch (e) {
      toast.error('Scoring failed — check LLM budget for GPT stage');
    }
    setScoring(false);
  };

  const handleControlledBatch = async (dist) => {
    setControlledGenerating(true);
    try {
      const res = await api().post(`${API}/api/content-engine/generate-controlled`, dist);
      if (res.data.success) {
        const msg = `Generated ${res.data.generated} stories, published ${res.data.published} to ${dist.use_story_engine ? 'Story Engine' : 'Pipeline'}`;
        toast.success(msg);
        setShowControlledModal(false);
        fetchStories();
        fetchBatchMetrics();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Controlled batch failed');
    }
    setControlledGenerating(false);
  };

  const handlePublishToStoryEngine = async (storyId) => {
    try {
      const res = await api().post(`${API}/api/content-engine/publish-to-story-engine/${storyId}`);
      if (res.data.success) {
        toast.success(`Queued for real video generation (Job: ${res.data.job_id.slice(0, 8)})`);
        fetchStories();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Story Engine publish failed — check LLM budget');
    }
  };

  const handleRateVideo = async (jobId, rating, wouldContinue, wouldShare) => {
    try {
      await api().post(`${API}/api/content-engine/rate-video`, {
        job_id: jobId,
        hook_rating: rating,
        would_continue: wouldContinue,
        would_share: wouldShare,
      });
      toast.success(`Rated as ${rating}`);
      fetchBatchMetrics();
    } catch (e) {
      toast.error('Rating failed');
    }
  };

  const handleFeature = async (storyIds, featured) => {
    try {
      await api().post(`${API}/api/content-engine/feature`, { story_ids: storyIds, featured });
      toast.success(featured ? 'Marked as featured' : 'Unfeatured');
      fetchStories();
    } catch { toast.error('Failed'); }
  };

  const handleTag = async (storyId, tag) => {
    try {
      await api().post(`${API}/api/content-engine/tag`, { story_id: storyId, tag });
      toast.success(`Tagged as ${tag}`);
      fetchStories();
    } catch { toast.error('Failed'); }
  };

  const handleDelete = async (storyId) => {
    try {
      await api().delete(`${API}/api/content-engine/${storyId}`);
      toast.success('Deleted');
      fetchStories();
    } catch { toast.error('Delete failed'); }
  };

  const handleSocialScripts = async (storyId) => {
    try {
      const res = await api().get(`${API}/api/content-engine/social-scripts/${storyId}`);
      if (res.data.success) setSocialModal(res.data);
    } catch { toast.error('Failed to load scripts'); }
  };

  const copyText = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied!');
  };

  const toggleSelect = (id) => {
    setSelected(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  return (
    <div className="min-h-screen bg-[var(--vs-bg-primary)] text-white" data-testid="content-engine-page">
      {/* Header */}
      <div className="sticky top-0 z-30 bg-[var(--vs-bg-primary)]/95 backdrop-blur-md border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/app/admin')} className="p-2 rounded-lg hover:bg-slate-800/50 transition-colors" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4 text-slate-400" />
            </button>
            <div>
              <h1 className="text-lg font-black flex items-center gap-2" style={{ fontFamily: 'var(--vs-font-heading)' }}>
                <Sparkles className="w-5 h-5 text-violet-400" /> Content Engine
              </h1>
              <p className="text-[10px] text-slate-500">AI-powered story hook generation for viral growth</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleScoreAll}
              disabled={scoring}
              className="h-8 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center gap-1.5 disabled:opacity-50 transition-colors"
              data-testid="score-all-btn"
            >
              <TrendingUp className="w-3.5 h-3.5" /> {scoring ? 'Scoring...' : 'Score All Hooks'}
            </button>
            <button
              onClick={handlePublishAll}
              disabled={publishing}
              className="h-8 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 disabled:opacity-50 transition-colors"
              data-testid="publish-all-btn"
            >
              <Send className="w-3.5 h-3.5" /> {publishing ? 'Publishing...' : 'Publish All Drafts'}
            </button>
            <button
              onClick={() => setShowControlledModal(true)}
              className="h-8 px-4 rounded-lg bg-gradient-to-r from-amber-600 to-rose-600 text-white text-xs font-bold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              data-testid="controlled-batch-btn"
            >
              <Flame className="w-3.5 h-3.5" /> Controlled Batch (10)
            </button>
            <button
              onClick={() => setShowGenModal(true)}
              className="h-8 px-4 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-xs font-bold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              data-testid="generate-btn"
            >
              <Zap className="w-3.5 h-3.5" /> Generate Batch
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Row */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6" data-testid="content-stats">
            <StatCard label="Total Stories" value={stats.total} icon={BookOpen} color="violet" />
            <StatCard label="Drafts" value={stats.draft} icon={Sparkles} color="amber" />
            <StatCard label="Published" value={stats.published} icon={Send} color="emerald" />
            <StatCard label="Featured" value={stats.featured} icon={Star} color="rose" />
          </div>
        )}

        {/* Batch Metrics — Hook Quality Tracking */}
        {batchMetrics && batchMetrics.total_rated > 0 && (
          <div className="mb-6 bg-slate-900/60 border border-slate-800/60 rounded-xl p-5" data-testid="batch-metrics">
            <h2 className="text-sm font-black text-white mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-amber-400" /> Micro Metrics ({batchMetrics.total_rated} rated)
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <div className="bg-emerald-500/[0.06] border border-emerald-500/20 rounded-lg p-3">
                <p className="text-[10px] text-emerald-400 font-bold uppercase">Continuation Rate</p>
                <p className="text-xl font-black text-white">{batchMetrics.metrics.continuation_rate}%</p>
              </div>
              <div className="bg-violet-500/[0.06] border border-violet-500/20 rounded-lg p-3">
                <p className="text-[10px] text-violet-400 font-bold uppercase">Share Rate</p>
                <p className="text-xl font-black text-white">{batchMetrics.metrics.share_rate}%</p>
              </div>
              {Object.entries(batchMetrics.by_rating || {}).map(([level, data]) => (
                <div key={level} className={`${level === 'HIGH' ? 'bg-amber-500/[0.06] border-amber-500/20' : level === 'MEDIUM' ? 'bg-blue-500/[0.06] border-blue-500/20' : 'bg-red-500/[0.06] border-red-500/20'} border rounded-lg p-3`}>
                  <p className={`text-[10px] font-bold ${level === 'HIGH' ? 'text-amber-400' : level === 'MEDIUM' ? 'text-blue-400' : 'text-red-400'}`}>{level} HOOK</p>
                  <p className="text-xl font-black text-white">{data.count}</p>
                  <p className="text-[9px] text-slate-500">Continue: {data.continuation_rate}% | Share: {data.share_rate}%</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Category Pills */}
        {stats?.by_category && (
          <div className="flex flex-wrap gap-2 mb-4">
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => setFilterCat(filterCat === cat.id ? '' : cat.id)}
                className={`text-[10px] font-bold px-3 py-1.5 rounded-full border transition-all ${
                  filterCat === cat.id
                    ? `bg-${cat.color}-500/20 text-${cat.color}-400 border-${cat.color}-500/40`
                    : 'bg-slate-800/50 text-slate-400 border-slate-700/50 hover:border-slate-600'
                }`}
                data-testid={`filter-cat-${cat.id}`}
              >
                {cat.label} ({stats.by_category[cat.id] || 0})
              </button>
            ))}
          </div>
        )}

        {/* Filters Row */}
        <div className="flex items-center gap-2 mb-5">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-7 text-[11px] bg-slate-800/60 border border-slate-700/50 text-slate-300 rounded-lg px-2 focus:outline-none focus:border-violet-500/50"
            data-testid="filter-status"
          >
            <option value="">All Status</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="rejected">Rejected</option>
          </select>
          <select
            value={filterTag}
            onChange={(e) => setFilterTag(e.target.value)}
            className="h-7 text-[11px] bg-slate-800/60 border border-slate-700/50 text-slate-300 rounded-lg px-2 focus:outline-none focus:border-violet-500/50"
            data-testid="filter-tag"
          >
            <option value="">All Tags</option>
            <option value="HIGH_VIRAL">High Viral</option>
            <option value="EMOTIONAL_HOOK">Emotional Hook</option>
            <option value="FAST_CONVERSION">Fast Conversion</option>
          </select>
          <button onClick={fetchStories} className="h-7 w-7 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-center hover:bg-slate-700/60 transition-colors">
            <RefreshCcw className="w-3 h-3 text-slate-400" />
          </button>
          {selected.size > 0 && (
            <button
              onClick={() => handleFeature([...selected], true)}
              className="h-7 px-3 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-400 text-[10px] font-bold flex items-center gap-1"
            >
              <Star className="w-3 h-3" /> Feature {selected.size} selected
            </button>
          )}
        </div>

        {/* Story Grid */}
        {loading ? (
          <div className="text-center py-16 text-slate-500">Loading stories...</div>
        ) : stories.length === 0 ? (
          <div className="text-center py-16" data-testid="empty-state">
            <Sparkles className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-500 font-medium mb-1">No stories yet</p>
            <p className="text-xs text-slate-600">Generate your first batch to fuel the content engine</p>
            <button
              onClick={() => setShowGenModal(true)}
              className="mt-4 h-9 px-5 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white text-sm font-bold hover:opacity-90"
            >
              Generate Stories
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="stories-grid">
            {stories.map(story => (
              <StoryCard
                key={story.story_id}
                story={story}
                selected={selected.has(story.story_id)}
                onToggleSelect={() => toggleSelect(story.story_id)}
                onPublish={() => handlePublish(story.story_id)}
                onPublishSE={() => handlePublishToStoryEngine(story.story_id)}
                onFeature={() => handleFeature([story.story_id], !story.is_featured)}
                onTag={(tag) => handleTag(story.story_id, tag)}
                onDelete={() => handleDelete(story.story_id)}
                onSocialScripts={() => handleSocialScripts(story.story_id)}
                onCopy={() => copyText(story.story_text)}
                onRate={(rating, cont, share) => handleRateVideo(story.story_engine_job_id || story.pipeline_job_id, rating, cont, share)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Generate Modal */}
      {showGenModal && (
        <GenerateModal
          count={genCount}
          setCount={setGenCount}
          categories={genCategories}
          setCategories={setGenCategories}
          autoPublish={genAutoPublish}
          setAutoPublish={setGenAutoPublish}
          generating={generating}
          onGenerate={handleGenerate}
          onClose={() => setShowGenModal(false)}
        />
      )}

      {/* Controlled Batch Modal */}
      {showControlledModal && (
        <ControlledBatchModal
          generating={controlledGenerating}
          onGenerate={handleControlledBatch}
          onClose={() => setShowControlledModal(false)}
        />
      )}

      {/* Social Scripts Modal */}
      {socialModal && (
        <SocialScriptsModal
          data={socialModal}
          onCopy={copyText}
          onClose={() => setSocialModal(null)}
        />
      )}
    </div>
  );
}

/* ─── Sub-components ─── */

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className={`bg-${color}-500/[0.06] border border-${color}-500/20 rounded-xl p-4`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-3.5 h-3.5 text-${color}-400`} />
        <span className={`text-[10px] font-bold text-${color}-400 uppercase tracking-wider`}>{label}</span>
      </div>
      <p className="text-2xl font-black text-white">{value}</p>
    </div>
  );
}

function StoryCard({ story, selected, onToggleSelect, onPublish, onPublishSE, onFeature, onTag, onDelete, onSocialScripts, onCopy, onRate }) {
  const [showTags, setShowTags] = useState(false);
  const [showRating, setShowRating] = useState(false);
  const catColor = CATEGORIES.find(c => c.id === story.category)?.color || 'slate';
  const isPublished = story.status === 'published' || story.status === 'published_se';

  return (
    <div
      className={`bg-slate-900/60 border rounded-xl p-4 transition-all ${
        selected ? 'border-violet-500/50 bg-violet-500/[0.04]' : 'border-slate-800/60 hover:border-slate-700/60'
      }`}
      data-testid={`story-card-${story.story_id?.slice(0, 8)}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            className="w-3.5 h-3.5 rounded bg-slate-800 border-slate-600 accent-violet-500"
          />
          <h3 className="text-sm font-bold text-white truncate">{story.title}</h3>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0 ml-2">
          {story.is_featured && <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />}
          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full bg-${catColor}-500/15 text-${catColor}-400`}>
            {story.category_label}
          </span>
        </div>
      </div>

      {/* Story text */}
      <div className="bg-slate-800/40 rounded-lg p-3 mb-3 border-l-2 border-violet-500/30">
        <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">{story.story_text}</p>
      </div>

      {/* Hook Score + Tags */}
      <div className="flex flex-wrap items-center gap-1 mb-3">
        {story.hook_final_score != null && (
          <span className={`text-[9px] font-black px-2 py-0.5 rounded-full border ${
            story.hook_tag === 'HIGH' ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' :
            story.hook_tag === 'MEDIUM' ? 'bg-blue-500/15 text-blue-400 border-blue-500/30' :
            'bg-red-500/15 text-red-400 border-red-500/30'
          }`} data-testid="hook-score-badge">
            HOOK {story.hook_final_score}
          </span>
        )}
        {story.hook_ready_for_video && (
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            VIDEO READY
          </span>
        )}
        {(story.quality_tags || []).map(tag => (
          <span key={tag} className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${TAG_COLORS[tag] || 'bg-slate-800 text-slate-400 border-slate-700'}`}>
            {tag.replace('_', ' ')}
          </span>
        ))}
        {story.hook_rejection_reasons?.length > 0 && (
          <span className="text-[9px] text-red-400/60 ml-1" title={story.hook_rejection_reasons.join(', ')}>
            {story.hook_rejection_reasons[0]}
          </span>
        )}
      </div>

      {/* Status + Actions */}
      <div className="flex items-center justify-between">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
          story.status === 'published' || story.status === 'published_se' ? 'bg-emerald-500/15 text-emerald-400' :
          story.status === 'rejected' ? 'bg-red-500/15 text-red-400' :
          'bg-amber-500/15 text-amber-400'
        }`}>
          {story.status === 'published_se' ? 'SE Published' : story.status}
        </span>
        <div className="flex items-center gap-1">
          <button onClick={onSocialScripts} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors" title="Social Scripts">
            <Instagram className="w-3.5 h-3.5 text-slate-500 hover:text-pink-400" />
          </button>
          <button onClick={onCopy} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors" title="Copy">
            <Copy className="w-3.5 h-3.5 text-slate-500 hover:text-white" />
          </button>
          <button onClick={onFeature} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors" title="Feature">
            <Star className={`w-3.5 h-3.5 ${story.is_featured ? 'text-amber-400 fill-amber-400' : 'text-slate-500 hover:text-amber-400'}`} />
          </button>
          <div className="relative">
            <button onClick={() => setShowTags(!showTags)} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors" title="Tag">
              <Tag className="w-3.5 h-3.5 text-slate-500 hover:text-violet-400" />
            </button>
            {showTags && (
              <div className="absolute right-0 bottom-8 bg-slate-900 border border-slate-700 rounded-lg p-1 shadow-xl z-10 min-w-[130px]">
                {['HIGH_VIRAL', 'EMOTIONAL_HOOK', 'FAST_CONVERSION', 'WEAK'].map(t => (
                  <button key={t} onClick={() => { onTag(t); setShowTags(false); }} className="w-full text-left text-[10px] px-2 py-1.5 rounded hover:bg-slate-800 text-slate-300">
                    {t.replace('_', ' ')}
                  </button>
                ))}
              </div>
            )}
          </div>
          {story.status === 'draft' && (
            <>
              <button onClick={onPublish} className="p-1.5 rounded-lg hover:bg-emerald-500/10 transition-colors" title="Publish to Pipeline">
                <Send className="w-3.5 h-3.5 text-slate-500 hover:text-emerald-400" />
              </button>
              <button onClick={onPublishSE} className="p-1.5 rounded-lg hover:bg-amber-500/10 transition-colors" title="Publish to Story Engine (Sora 2)">
                <Film className="w-3.5 h-3.5 text-slate-500 hover:text-amber-400" />
              </button>
            </>
          )}
          {/* Rate hook quality if published */}
          {isPublished && (
            <div className="relative">
              <button onClick={() => setShowRating(!showRating)} className="p-1.5 rounded-lg hover:bg-amber-500/10 transition-colors" title="Rate Hook Quality">
                <Flame className="w-3.5 h-3.5 text-slate-500 hover:text-amber-400" />
              </button>
              {showRating && (
                <div className="absolute right-0 bottom-8 bg-slate-900 border border-slate-700 rounded-lg p-2 shadow-xl z-10 min-w-[180px]">
                  <p className="text-[9px] text-slate-500 font-bold mb-1.5">RATE HOOK QUALITY</p>
                  {[
                    { level: 'HIGH', color: 'amber', label: 'HIGH — Addictive' },
                    { level: 'MEDIUM', color: 'blue', label: 'MEDIUM — Decent' },
                    { level: 'LOW', color: 'red', label: 'LOW — Weak' },
                  ].map(r => (
                    <button key={r.level} onClick={() => { onRate(r.level, r.level === 'HIGH', r.level !== 'LOW'); setShowRating(false); }} className={`w-full text-left text-[10px] px-2 py-1.5 rounded hover:bg-${r.color}-500/10 text-slate-300 flex items-center gap-2`}>
                      <span className={`w-2 h-2 rounded-full bg-${r.color}-400`} />
                      {r.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <button onClick={onDelete} className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors" title="Delete">
            <Trash2 className="w-3.5 h-3.5 text-slate-500 hover:text-red-400" />
          </button>
        </div>
      </div>
    </div>
  );
}

function GenerateModal({ count, setCount, categories, setCategories, autoPublish, setAutoPublish, generating, onGenerate, onClose }) {
  const toggleCat = (id) => {
    setCategories(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="generate-modal">
      <div className="w-full max-w-md mx-4 bg-[#0c0c14] border border-violet-500/30 rounded-2xl overflow-hidden shadow-2xl">
        <div className="h-1 bg-gradient-to-r from-violet-600 via-rose-500 to-amber-500" />
        <div className="p-6">
          <h2 className="text-lg font-black text-white mb-1 flex items-center gap-2">
            <Zap className="w-5 h-5 text-violet-400" /> Generate Story Hooks
          </h2>
          <p className="text-xs text-slate-500 mb-5">AI creates hook stories with strict HOOK → BUILD → CLIFFHANGER format</p>

          {/* Count selector */}
          <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2 block">Batch Size</label>
          <div className="flex gap-2 mb-5">
            {[10, 25, 50].map(n => (
              <button
                key={n}
                onClick={() => setCount(n)}
                className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${
                  count === n
                    ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20'
                    : 'bg-slate-800/60 text-slate-400 hover:bg-slate-700/60'
                }`}
                data-testid={`gen-count-${n}`}
              >
                {n}
              </button>
            ))}
          </div>

          {/* Category selector */}
          <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2 block">Categories (empty = all)</label>
          <div className="flex flex-wrap gap-2 mb-5">
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => toggleCat(cat.id)}
                className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${
                  categories.includes(cat.id)
                    ? 'bg-violet-500/20 text-violet-400 border-violet-500/40'
                    : 'bg-slate-800/60 text-slate-500 border-slate-700/50'
                }`}
                data-testid={`gen-cat-${cat.id}`}
              >
                {categories.includes(cat.id) && <Check className="w-3 h-3 inline mr-1" />}
                {cat.label}
              </button>
            ))}
          </div>

          {/* Auto-publish toggle */}
          <label className="flex items-center gap-2 mb-6 cursor-pointer">
            <input
              type="checkbox"
              checked={autoPublish}
              onChange={(e) => setAutoPublish(e.target.checked)}
              className="w-4 h-4 rounded bg-slate-800 border-slate-600 accent-violet-500"
              data-testid="gen-auto-publish"
            />
            <span className="text-xs text-slate-300">Auto-publish to video pipeline</span>
          </label>

          {/* Actions */}
          <div className="flex gap-2">
            <button onClick={onClose} className="flex-1 py-3 rounded-xl bg-slate-800 text-slate-400 text-sm font-bold hover:bg-slate-700 transition-colors">
              Cancel
            </button>
            <button
              onClick={onGenerate}
              disabled={generating}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white text-sm font-bold flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50 transition-opacity"
              data-testid="gen-confirm-btn"
            >
              {generating ? (
                <><RefreshCcw className="w-4 h-4 animate-spin" /> Generating...</>
              ) : (
                <><Sparkles className="w-4 h-4" /> Generate {count} Stories</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ControlledBatchModal({ generating, onGenerate, onClose }) {
  const [emotional, setEmotional] = useState(4);
  const [mystery, setMystery] = useState(3);
  const [kids, setKids] = useState(2);
  const [viral, setViral] = useState(1);
  const [useStoryEngine, setUseStoryEngine] = useState(true);
  const total = emotional + mystery + kids + viral;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="controlled-batch-modal">
      <div className="w-full max-w-md mx-4 bg-[#0c0c14] border border-amber-500/30 rounded-2xl overflow-hidden shadow-2xl">
        <div className="h-1 bg-gradient-to-r from-amber-500 via-rose-500 to-violet-500" />
        <div className="p-6">
          <h2 className="text-lg font-black text-white mb-1 flex items-center gap-2">
            <Flame className="w-5 h-5 text-amber-400" /> Controlled Batch ({total} videos)
          </h2>
          <p className="text-xs text-slate-500 mb-5">Exact category distribution — test hook quality before scaling</p>

          <div className="space-y-3 mb-5">
            {[
              { label: 'Emotional', color: 'rose', value: emotional, set: setEmotional },
              { label: 'Mystery', color: 'indigo', value: mystery, set: setMystery },
              { label: 'Kids', color: 'emerald', value: kids, set: setKids },
              { label: 'Viral', color: 'amber', value: viral, set: setViral },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between">
                <span className={`text-xs font-bold text-${item.color}-400`}>{item.label}</span>
                <div className="flex items-center gap-2">
                  <button onClick={() => item.set(Math.max(0, item.value - 1))} className="w-7 h-7 rounded-lg bg-slate-800 text-white text-sm font-bold hover:bg-slate-700">-</button>
                  <span className="text-sm font-bold text-white w-6 text-center">{item.value}</span>
                  <button onClick={() => item.set(Math.min(20, item.value + 1))} className="w-7 h-7 rounded-lg bg-slate-800 text-white text-sm font-bold hover:bg-slate-700">+</button>
                </div>
              </div>
            ))}
          </div>

          <label className="flex items-center gap-2 mb-6 cursor-pointer">
            <input
              type="checkbox"
              checked={useStoryEngine}
              onChange={(e) => setUseStoryEngine(e.target.checked)}
              className="w-4 h-4 rounded bg-slate-800 border-slate-600 accent-amber-500"
              data-testid="controlled-use-se"
            />
            <span className="text-xs text-slate-300">Use Story Engine (real Sora 2 video)</span>
          </label>

          <div className="flex gap-2">
            <button onClick={onClose} className="flex-1 py-3 rounded-xl bg-slate-800 text-slate-400 text-sm font-bold hover:bg-slate-700 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => onGenerate({ emotional, mystery, kids, viral, use_story_engine: useStoryEngine })}
              disabled={generating || total === 0}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-amber-600 to-rose-600 text-white text-sm font-bold flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50 transition-opacity"
              data-testid="controlled-confirm-btn"
            >
              {generating ? (
                <><RefreshCcw className="w-4 h-4 animate-spin" /> Generating...</>
              ) : (
                <><Flame className="w-4 h-4" /> Generate {total} Videos</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SocialScriptsModal({ data, onCopy, onClose }) {
  const scripts = data?.social_scripts;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="social-scripts-modal">
      <div className="w-full max-w-lg mx-4 bg-[#0c0c14] border border-violet-500/30 rounded-2xl overflow-hidden shadow-2xl max-h-[80vh] overflow-y-auto">
        <div className="h-1 bg-gradient-to-r from-pink-500 to-violet-500" />
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Instagram className="w-5 h-5 text-pink-400" /> Social Media Scripts
            </h2>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 transition-colors">
              <X className="w-4 h-4 text-slate-400" />
            </button>
          </div>

          <div className="bg-slate-800/40 rounded-lg p-3 mb-5 border-l-2 border-violet-500/30">
            <p className="text-[10px] text-slate-500 mb-1 font-bold">ORIGINAL STORY</p>
            <p className="text-xs text-slate-300 whitespace-pre-wrap">{data?.story_text}</p>
          </div>

          {scripts ? (
            <div className="space-y-4">
              {/* Reel Script */}
              <ScriptBlock
                label="Reel Script"
                icon={<Play className="w-3.5 h-3.5" />}
                text={scripts.reel_script}
                onCopy={() => onCopy(scripts.reel_script)}
                color="rose"
              />
              {/* Caption */}
              <ScriptBlock
                label="Caption"
                icon={<Share2 className="w-3.5 h-3.5" />}
                text={scripts.caption}
                onCopy={() => onCopy(scripts.caption)}
                color="violet"
              />
              {/* Hashtags */}
              <ScriptBlock
                label="Hashtags"
                icon={<Tag className="w-3.5 h-3.5" />}
                text={scripts.hashtags}
                onCopy={() => onCopy(scripts.hashtags)}
                color="cyan"
              />
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-6">No social scripts generated yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ScriptBlock({ label, icon, text, onCopy, color }) {
  return (
    <div className={`bg-${color}-500/[0.04] border border-${color}-500/20 rounded-xl p-4`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-[10px] font-bold text-${color}-400 uppercase tracking-wider flex items-center gap-1`}>
          {icon} {label}
        </span>
        <button onClick={onCopy} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors" title="Copy">
          <Copy className="w-3 h-3 text-slate-500 hover:text-white" />
        </button>
      </div>
      <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">{text}</p>
    </div>
  );
}
