import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { generationAPI, creditAPI } from '../utils/api';
import { markFeatureUsed } from '../utils/feedbackSession';
import { useProductGuide } from '../contexts/ProductGuideContext';
import { toast } from 'sonner';
import {
  Sparkles, Copy, Download, Loader2, ArrowLeft, Coins, AlertCircle,
  ChevronDown, ChevronUp, Zap, Target, Eye, Video, Hash,
  Camera, Mic, FileText, Lightbulb, Settings, Play, Check,
  Link2, FileCode, MessageSquare, Layers,
} from 'lucide-react';

import ShareButton from '../components/ShareButton';
import CreationActionsBar from '../components/CreationActionsBar';
import NextActionHooks from '../components/NextActionHooks';
import RemixBanner from '../components/RemixBanner';
import { useRemixData, mapRemixToFields } from '../hooks/useRemixData';
import UpgradeBanner from '../components/UpgradeBanner';
import UpgradeModal from '../components/UpgradeModal';
import UpsellModal from '../components/UpsellModal';
import ReelProgressBar from '../components/ReelProgressBar';
import HelpGuide from '../components/HelpGuide';
import RatingModal from '../components/RatingModal';
import WaitingWithGames from '../components/WaitingWithGames';
import analytics from '../utils/analytics';

// ── Constants ──────────────────────────────────────────────
const PLATFORMS = ['Short-Form Feed', 'Vertical Video', 'Viral Clips', 'Social Video'];
const HOOK_STYLES = ['Curiosity', 'Shock', 'Emotional', 'Luxury', 'Educational', 'Story', 'FOMO', 'Problem-Solution'];
const REEL_FORMATS = ['Talking Head', 'Faceless', 'Voiceover', 'Cinematic', 'Slideshow', 'UGC Ad', 'Meme', 'Story'];
const CTA_TYPES = ['Follow', 'Save', 'Comment', 'Buy', 'DM', 'Share'];
const CONTENT_OBJECTIVES = ['Followers', 'Engagement', 'Sales', 'Leads', 'Education', 'Retention'];
const OUTPUT_TYPES = [
  { value: 'script_only', label: 'Script Only' },
  { value: 'script_caption', label: 'Script + Caption' },
  { value: 'script_visuals', label: 'Script + Visual Prompts' },
  { value: 'full_plan', label: 'Full Video Plan' },
];
const TONES = ['Bold', 'Calm', 'Funny', 'Emotional', 'Authority', 'Luxury', 'Conversational', 'Urgent'];
const DURATIONS = [
  { value: '15s', label: '15 seconds' },
  { value: '30s', label: '30 seconds' },
  { value: '60s', label: '60 seconds' },
  { value: '90s', label: '90 seconds' },
];

const QUICK_PRESETS = [
  {
    id: 'viral_hook', label: 'Viral Hook', icon: Zap, color: 'rose',
    config: { platform: 'Short-Form Feed', hookStyle: 'Shock', reelFormat: 'Talking Head', ctaType: 'Share', goal: 'Engagement', outputType: 'full_plan', tone: 'Bold', duration: '15s', niche: 'Entertainment', audience: 'Gen Z (13-24)' },
  },
  {
    id: 'luxury_reel', label: 'Luxury Reel', icon: Sparkles, color: 'amber',
    config: { platform: 'Short-Form Feed', hookStyle: 'Luxury', reelFormat: 'Cinematic', ctaType: 'Follow', goal: 'Followers', outputType: 'full_plan', tone: 'Luxury', duration: '30s', niche: 'Luxury', audience: 'Luxury Consumers' },
  },
  {
    id: 'product_promo', label: 'Product Promo', icon: Target, color: 'emerald',
    config: { platform: 'Short-Form Feed', hookStyle: 'Problem-Solution', reelFormat: 'UGC Ad', ctaType: 'Buy', goal: 'Sales', outputType: 'full_plan', tone: 'Conversational', duration: '30s', niche: 'Finance', audience: 'Young Professionals' },
  },
  {
    id: 'ugc_ad', label: 'UGC Ad', icon: Camera, color: 'sky',
    config: { platform: 'Viral Clips', hookStyle: 'Story', reelFormat: 'UGC Ad', ctaType: 'Buy', goal: 'Sales', outputType: 'full_plan', tone: 'Conversational', duration: '30s', niche: 'General', audience: 'Millennials (25-40)' },
  },
  {
    id: 'storytelling', label: 'Storytelling', icon: FileText, color: 'violet',
    config: { platform: 'Short-Form Feed', hookStyle: 'Emotional', reelFormat: 'Story', ctaType: 'Save', goal: 'Retention', outputType: 'full_plan', tone: 'Emotional', duration: '60s', niche: 'Relationships', audience: 'General' },
  },
  {
    id: 'educational', label: 'Educational', icon: Lightbulb, color: 'indigo',
    config: { platform: 'Vertical Video', hookStyle: 'Educational', reelFormat: 'Talking Head', ctaType: 'Save', goal: 'Education', outputType: 'full_plan', tone: 'Authority', duration: '60s', niche: 'Education', audience: 'College Students' },
  },
  {
    id: 'kids_story', label: 'Kids Story', icon: Play, color: 'pink',
    config: { platform: 'Vertical Video', hookStyle: 'Story', reelFormat: 'Story', ctaType: 'Follow', goal: 'Retention', outputType: 'full_plan', tone: 'Funny', duration: '60s', niche: 'Education', audience: 'Parents' },
  },
  {
    id: 'faceless_biz', label: 'Faceless Biz', icon: Eye, color: 'teal',
    config: { platform: 'Viral Clips', hookStyle: 'Curiosity', reelFormat: 'Faceless', ctaType: 'DM', goal: 'Leads', outputType: 'full_plan', tone: 'Authority', duration: '30s', niche: 'Finance', audience: 'Entrepreneurs' },
  },
];

const PRESET_COLORS = {
  rose: 'bg-rose-500/10 text-rose-300 border-rose-500/25 hover:bg-rose-500/20',
  amber: 'bg-amber-500/10 text-amber-300 border-amber-500/25 hover:bg-amber-500/20',
  emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25 hover:bg-emerald-500/20',
  sky: 'bg-sky-500/10 text-sky-300 border-sky-500/25 hover:bg-sky-500/20',
  violet: 'bg-violet-500/10 text-violet-300 border-violet-500/25 hover:bg-violet-500/20',
  indigo: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/25 hover:bg-indigo-500/20',
  pink: 'bg-pink-500/10 text-pink-300 border-pink-500/25 hover:bg-pink-500/20',
  teal: 'bg-teal-500/10 text-teal-300 border-teal-500/25 hover:bg-teal-500/20',
};

const PRESET_ACTIVE_COLORS = {
  rose: 'bg-rose-500/25 text-rose-200 border-rose-500/50 ring-1 ring-rose-500/30',
  amber: 'bg-amber-500/25 text-amber-200 border-amber-500/50 ring-1 ring-amber-500/30',
  emerald: 'bg-emerald-500/25 text-emerald-200 border-emerald-500/50 ring-1 ring-emerald-500/30',
  sky: 'bg-sky-500/25 text-sky-200 border-sky-500/50 ring-1 ring-sky-500/30',
  violet: 'bg-violet-500/25 text-violet-200 border-violet-500/50 ring-1 ring-violet-500/30',
  indigo: 'bg-indigo-500/25 text-indigo-200 border-indigo-500/50 ring-1 ring-indigo-500/30',
  pink: 'bg-pink-500/25 text-pink-200 border-pink-500/50 ring-1 ring-pink-500/30',
  teal: 'bg-teal-500/25 text-teal-200 border-teal-500/50 ring-1 ring-teal-500/30',
};
const PERFORMANCE_VARIATIONS = [
  { id: 'stronger_hook', label: 'Stronger Hook', icon: Target },
  { id: 'higher_retention', label: 'Higher Retention', icon: Eye },
  { id: 'more_emotional', label: 'More Emotional', icon: Sparkles },
  { id: 'more_viral', label: 'More Viral', icon: Zap },
  { id: 'more_sales', label: 'More Sales-focused', icon: Coins },
  { id: 'shorter_punchier', label: 'Shorter & Punchier', icon: Target },
  { id: 'better_cta', label: 'Better CTA', icon: Play },
  { id: 'platform_optimized', label: 'Platform Optimized', icon: Settings },
];

const OUTPUT_TABS = [
  { id: 'script', label: 'Script', icon: FileText },
  { id: 'hooks', label: 'Hook Variants', icon: Target },
  { id: 'caption', label: 'Caption', icon: FileText },
  { id: 'hashtags', label: 'Hashtags', icon: Hash },
  { id: 'shot_list', label: 'Shot List', icon: Camera },
  { id: 'visual_prompts', label: 'Visual Prompts', icon: Eye },
  { id: 'voiceover', label: 'Voiceover', icon: Mic },
  { id: 'reference_analysis', label: 'Reference DNA', icon: Layers },
];

// Blocked words for content filtering
const blockedWords = [
  'sex', 'porn', 'xxx', 'nude', 'naked', 'erotic', 'adult', 'nsfw', 'explicit',
  'orgasm', 'masturbat', 'penis', 'vagina', 'boob', 'breast', 'nipple', 'genital',
  'prostitut', 'escort', 'stripper', 'onlyfans', 'fetish', 'bdsm', 'kinky',
  'kill', 'murder', 'blood', 'gore', 'violent', 'torture', 'abuse', 'assault',
  'rape', 'molest', 'stab', 'shoot', 'bomb', 'terrorist', 'massacre', 'genocide',
  'decapitat', 'dismember', 'mutilat', 'brutal',
  'racist', 'racism', 'nazi', 'hitler', 'hate', 'discriminat', 'slur', 'bigot',
  'homophob', 'transphob', 'sexist', 'supremac', 'extremist',
  'cocaine', 'heroin', 'meth', 'crack', 'ecstasy', 'lsd', 'overdose', 'drug deal',
  'suicide', 'self-harm', 'cutting', 'anorex', 'bulimi',
  'pedophil', 'incest', 'bestiality', 'necrophil', 'cannibal',
  'fuck', 'shit', 'bitch', 'asshole', 'bastard', 'cunt', 'dick', 'cock', 'whore'
];

function validateContent(text) {
  if (!text || text.trim() === '') return { valid: false, message: 'Please enter a topic' };
  const lower = text.toLowerCase();
  for (const w of blockedWords) {
    if (lower.includes(w)) return { valid: false, message: 'Your topic contains inappropriate content. Please use family-friendly language.' };
  }
  return { valid: true };
}

// ── Inline Select for compact controls ──────────────────
function CompactSelect({ label, value, onChange, options, testId }) {
  return (
    <div>
      <Label className="text-slate-400 text-xs font-medium mb-1.5 block">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="bg-slate-900/60 border-slate-700/50 text-white text-sm h-9 focus:ring-indigo-500/20" data-testid={testId}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-slate-800 border-slate-700 max-h-[280px]">
          {options.map(opt => {
            const val = typeof opt === 'string' ? opt : opt.value;
            const lab = typeof opt === 'string' ? opt : opt.label;
            return <SelectItem key={val} value={val} className="text-white focus:bg-indigo-600 text-sm">{lab}</SelectItem>;
          })}
        </SelectContent>
      </Select>
    </div>
  );
}

// ── Output Tab Content Components ───────────────────────
function ScriptTab({ result }) {
  if (!result?.script?.scenes) return <EmptyTab message="No script data available" />;
  return (
    <div className="space-y-3" data-testid="output-tab-script">
      {result.script.scenes.map((scene, idx) => (
        <div key={idx} className="border border-slate-700/50 bg-slate-900/40 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Scene {idx + 1}</span>
            <span className="text-xs text-slate-500 font-mono">{scene.time}</span>
          </div>
          {scene.on_screen_text && (
            <div className="mb-2">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">On-Screen Text</span>
              <p className="text-sm text-white font-medium mt-0.5">{scene.on_screen_text}</p>
            </div>
          )}
          {scene.voiceover && (
            <div className="mb-2">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Voiceover</span>
              <p className="text-sm text-slate-300 mt-0.5">{scene.voiceover}</p>
            </div>
          )}
          {scene.visual_direction && (
            <div className="mb-2">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Visual Direction</span>
              <p className="text-sm text-slate-400 mt-0.5 italic">{scene.visual_direction}</p>
            </div>
          )}
          {scene.broll?.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">B-Roll</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {scene.broll.map((b, i) => (
                  <span key={i} className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700/50">{b}</span>
                ))}
              </div>
            </div>
          )}
          {scene.retention_note && (
            <div className="mt-2 pt-2 border-t border-slate-800">
              <span className="text-[10px] font-semibold text-emerald-500 uppercase tracking-wide">Retention</span>
              <p className="text-xs text-emerald-400/80 mt-0.5">{scene.retention_note}</p>
            </div>
          )}
        </div>
      ))}
      {result.script?.cta && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
          <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Call to Action</span>
          <p className="text-sm text-emerald-200 mt-1 font-medium">{result.script.cta}</p>
        </div>
      )}
    </div>
  );
}

function HooksTab({ result }) {
  if (!result?.hooks?.length) return <EmptyTab message="No hook variants available" />;
  return (
    <div className="space-y-2" data-testid="output-tab-hooks">
      {result.best_hook && (
        <div className="bg-gradient-to-r from-indigo-500/15 to-purple-500/15 border border-indigo-500/30 rounded-xl p-4 mb-3">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Top Performer</span>
          </div>
          <p className="text-white font-semibold">{result.best_hook}</p>
        </div>
      )}
      {result.hooks.map((hook, idx) => (
        <div key={idx} className="bg-slate-900/50 border border-slate-700/50 p-3 rounded-xl flex items-start gap-3 group hover:border-indigo-500/30 transition-colors">
          <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">{idx + 1}</span>
          <p className="text-sm text-slate-200 flex-1">{hook}</p>
          <button onClick={() => { navigator.clipboard.writeText(hook); toast.success('Hook copied!'); }} className="opacity-0 group-hover:opacity-100 transition-opacity">
            <Copy className="w-3.5 h-3.5 text-slate-500 hover:text-white" />
          </button>
        </div>
      ))}
    </div>
  );
}

function CaptionTab({ result }) {
  if (!result?.caption_short && !result?.caption_long) return <EmptyTab message="No caption data available" />;
  return (
    <div className="space-y-4" data-testid="output-tab-caption">
      {result.caption_short && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Short Caption</span>
            <button onClick={() => { navigator.clipboard.writeText(result.caption_short); toast.success('Copied!'); }} className="text-slate-500 hover:text-white"><Copy className="w-3.5 h-3.5" /></button>
          </div>
          <p className="text-sm bg-slate-900/50 border border-slate-700/50 p-3 rounded-xl text-slate-200">{result.caption_short}</p>
        </div>
      )}
      {result.caption_long && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Long Caption</span>
            <button onClick={() => { navigator.clipboard.writeText(result.caption_long); toast.success('Copied!'); }} className="text-slate-500 hover:text-white"><Copy className="w-3.5 h-3.5" /></button>
          </div>
          <p className="text-sm bg-slate-900/50 border border-slate-700/50 p-3 rounded-xl text-slate-200 whitespace-pre-wrap">{result.caption_long}</p>
        </div>
      )}
    </div>
  );
}

function HashtagsTab({ result }) {
  if (!result?.hashtags?.length) return <EmptyTab message="No hashtags available" />;
  return (
    <div data-testid="output-tab-hashtags">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{result.hashtags.length} Hashtags</span>
        <button onClick={() => { navigator.clipboard.writeText(result.hashtags.join(' ')); toast.success('All hashtags copied!'); }} className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">Copy All</button>
      </div>
      <div className="flex flex-wrap gap-2">
        {result.hashtags.map((tag, idx) => (
          <span key={idx} onClick={() => { navigator.clipboard.writeText(tag); toast.success('Copied!'); }} className="bg-blue-500/10 text-blue-300 border border-blue-500/20 px-3 py-1.5 rounded-full text-sm cursor-pointer hover:bg-blue-500/20 transition-colors">{tag}</span>
        ))}
      </div>
    </div>
  );
}

function ShotListTab({ result }) {
  if (!result?.shot_list?.length) return <EmptyTab message="No shot list available. Try 'Full Video Plan' output type." />;
  return (
    <div className="space-y-2" data-testid="output-tab-shot-list">
      {result.shot_list.map((shot, idx) => (
        <div key={idx} className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-3">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-purple-400 bg-purple-500/10 w-6 h-6 rounded-full flex items-center justify-center">{shot.shot_number || idx + 1}</span>
              <span className="text-xs text-slate-500 uppercase font-mono">{shot.type}</span>
            </div>
            <span className="text-xs text-slate-500">{shot.duration}</span>
          </div>
          <p className="text-sm text-slate-200">{shot.description}</p>
          {shot.notes && <p className="text-xs text-slate-500 mt-1 italic">{shot.notes}</p>}
        </div>
      ))}
    </div>
  );
}

function VisualPromptsTab({ result }) {
  if (!result?.visual_prompts?.length) return <EmptyTab message="No visual prompts available. Try 'Script + Visual Prompts' or 'Full Video Plan'." />;
  return (
    <div className="space-y-3" data-testid="output-tab-visual-prompts">
      {result.visual_prompts.map((prompt, idx) => (
        <div key={idx} className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-4 group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Scene {idx + 1} Prompt</span>
            <button onClick={() => { navigator.clipboard.writeText(prompt); toast.success('Visual prompt copied!'); }} className="opacity-0 group-hover:opacity-100 transition-opacity"><Copy className="w-3.5 h-3.5 text-slate-500 hover:text-white" /></button>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">{prompt}</p>
        </div>
      ))}
    </div>
  );
}

function VoiceoverTab({ result }) {
  const voText = result?.voiceover_full;
  if (!voText) return <EmptyTab message="No voiceover script available" />;
  return (
    <div data-testid="output-tab-voiceover">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Full Voiceover Script</span>
        <button onClick={() => { navigator.clipboard.writeText(voText); toast.success('Voiceover copied!'); }} className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">Copy</button>
      </div>
      <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
        <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{voText}</p>
      </div>
    </div>
  );
}

function ReferenceAnalysisTab({ result }) {
  const analysis = result?.reference_analysis;
  if (!analysis || !result?.is_reference_based) return <EmptyTab message="No reference analysis — this was a standard generation." />;
  const items = [
    { label: 'Hook Pattern', value: analysis.hook_pattern, icon: Target },
    { label: 'Pacing Structure', value: analysis.pacing_structure, icon: Play },
    { label: 'Emotional Arc', value: analysis.emotional_arc, icon: Sparkles },
    { label: 'CTA Approach', value: analysis.cta_approach, icon: Zap },
    { label: 'Format Choices', value: analysis.format_choices, icon: Settings },
  ].filter(i => i.value);
  return (
    <div className="space-y-4" data-testid="output-tab-reference-analysis">
      <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Layers className="w-4 h-4 text-amber-400" />
          <span className="text-sm font-bold text-white">Structural DNA Extracted</span>
          <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-medium">
            {result.reference_source === 'url' ? 'From URL' : 'From Text'}
          </span>
        </div>
        <div className="space-y-3">
          {items.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2.5">
              <item.icon className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">{item.label}</span>
                <p className="text-xs text-slate-300 leading-relaxed">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      {(analysis.what_was_kept || analysis.what_was_changed) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {analysis.what_was_kept && (
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-3">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Preserved from Reference</span>
              <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">{analysis.what_was_kept}</p>
            </div>
          )}
          {analysis.what_was_changed && (
            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-3">
              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Made Original</span>
              <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">{analysis.what_was_changed}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmptyTab({ message }) {
  return (
    <div className="text-center py-8 text-slate-500">
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ── AI Recommendations Panel ────────────────────────────
function AIRecommendations({ result }) {
  const rec = result?.ai_recommendations;
  if (!rec) return null;
  const items = [
    { label: 'Best Hook Type', value: rec.best_hook_type, icon: Target },
    { label: 'Recommended Duration', value: rec.recommended_duration, icon: Settings },
    { label: 'Best Posting Time', value: rec.suggested_posting_time, icon: Lightbulb },
    { label: 'Emotional Trigger', value: rec.emotional_trigger, icon: Sparkles },
    { label: 'Retention Strategy', value: rec.retention_strategy, icon: Eye },
  ].filter(i => i.value);
  if (!items.length) return null;
  return (
    <div className="bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border border-indigo-500/20 rounded-xl p-4" data-testid="ai-recommendations">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-4 h-4 text-indigo-400" />
        <span className="text-sm font-bold text-white">AI Recommendations</span>
      </div>
      <div className="grid gap-2">
        {items.map((item, idx) => (
          <div key={idx} className="flex items-start gap-2.5">
            <item.icon className="w-3.5 h-3.5 text-indigo-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">{item.label}</span>
              <p className="text-xs text-slate-300">{item.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Video Config Modal ──────────────────────────────────
function VideoConfigModal({ isOpen, onClose, onGenerate }) {
  const [config, setConfig] = useState({
    videoStyle: 'ai',
    voiceover: true,
    subtitles: true,
    aspectRatio: '9:16',
    quality: 'fast',
  });
  if (!isOpen) return null;
  const estimatedCredits = config.quality === 'high' ? 50 : 25;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="video-config-modal">
      <div className="bg-slate-900 border border-slate-700/50 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-4">Video Generation Settings</h3>
        <div className="space-y-4">
          <CompactSelect label="Video Style" value={config.videoStyle} onChange={v => setConfig(p => ({...p, videoStyle: v}))} options={[
            { value: 'ai', label: 'AI Generated' },
            { value: 'stock', label: 'Stock Footage' },
            { value: 'mixed', label: 'Mixed' },
            { value: 'avatar', label: 'AI Avatar' },
          ]} testId="video-style-select" />
          <div className="grid grid-cols-2 gap-3">
            <label className="flex items-center gap-2 cursor-pointer bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <input type="checkbox" checked={config.voiceover} onChange={e => setConfig(p => ({...p, voiceover: e.target.checked}))} className="rounded border-slate-600 bg-slate-900 text-indigo-500" />
              <span className="text-sm text-slate-300">Voiceover</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <input type="checkbox" checked={config.subtitles} onChange={e => setConfig(p => ({...p, subtitles: e.target.checked}))} className="rounded border-slate-600 bg-slate-900 text-indigo-500" />
              <span className="text-sm text-slate-300">Subtitles</span>
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <CompactSelect label="Aspect Ratio" value={config.aspectRatio} onChange={v => setConfig(p => ({...p, aspectRatio: v}))} options={[
              { value: '9:16', label: '9:16 (Vertical)' },
              { value: '16:9', label: '16:9 (Landscape)' },
              { value: '1:1', label: '1:1 (Square)' },
            ]} testId="aspect-ratio-select" />
            <CompactSelect label="Quality Mode" value={config.quality} onChange={v => setConfig(p => ({...p, quality: v}))} options={[
              { value: 'fast', label: 'Fast' },
              { value: 'high', label: 'High Quality' },
            ]} testId="quality-mode-select" />
          </div>
          <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-3 flex items-center justify-between">
            <span className="text-sm text-indigo-300 font-medium">Estimated Cost</span>
            <span className="text-sm text-white font-bold">{estimatedCredits} credits</span>
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <Button variant="outline" onClick={onClose} className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800">Cancel</Button>
          <Button onClick={() => { onGenerate(config); onClose(); }} className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white" data-testid="video-generate-confirm">
            <Video className="w-4 h-4 mr-2" />
            Generate Video
          </Button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// ── Main Component ────────────────────────────────────
// ═══════════════════════════════════════════════════════
export default function ReelGenerator() {
  const [credits, setCredits] = useState(null);
  const [creditsLoaded, setCreditsLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [isFreeTier, setIsFreeTier] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [showUpsellModal, setShowUpsellModal] = useState(false);
  const [showVideoConfig, setShowVideoConfig] = useState(false);
  const [lastGenerationId, setLastGenerationId] = useState(null);
  const [activeTab, setActiveTab] = useState('script');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [referenceMode, setReferenceMode] = useState(false);
  const [referenceUrl, setReferenceUrl] = useState('');
  const [referenceText, setReferenceText] = useState('');
  const [referenceNotes, setReferenceNotes] = useState('');
  const [activePreset, setActivePreset] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { updateStep: trackJourneyStep } = useProductGuide();
  const { remixData: incomingRemix, sourceTool: remixSource, sourceTitle: remixTitle, consumed: hasRemix, dismiss: dismissRemix } = useRemixData('reels');

  const [formData, setFormData] = useState({
    topic: '',
    platform: 'Short-Form Feed',
    hookStyle: 'Curiosity',
    reelFormat: 'Talking Head',
    ctaType: 'Follow',
    goal: 'Followers',
    outputType: 'full_plan',
    niche: 'Luxury',
    tone: 'Bold',
    duration: '30s',
    language: 'English',
    audience: 'General',
  });

  useEffect(() => {
    fetchCredits();
    if (hasRemix && incomingRemix) {
      const fields = mapRemixToFields(incomingRemix, 'reels');
      if (fields.topic) setFormData(prev => ({ ...prev, topic: fields.topic }));
      if (fields.niche) setFormData(prev => ({ ...prev, niche: fields.niche }));
      if (fields.tone) setFormData(prev => ({ ...prev, tone: fields.tone }));
      if (fields.duration) setFormData(prev => ({ ...prev, duration: fields.duration }));
    }
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await creditAPI.getBalance();
      const data = response.data;
      setCredits(data.balance ?? data.credits ?? 0);
      setIsFreeTier(data.isFreeTier ?? (data.plan === 'free'));
    } catch (error) {
      setCredits(0);
      toast.error('Failed to load credits');
    } finally {
      setCreditsLoaded(true);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validation = validateContent(formData.topic);
    if (!validation.valid) { toast.error(validation.message); return; }
    if ((credits ?? 0) < 1) { toast.error('Insufficient credits! Please buy more.'); navigate('/pricing'); return; }

    setResult(null);
    setLoading(true);
    setActiveTab('script');
    try {
      const payload = { ...formData };
      if (referenceMode) {
        if (referenceUrl) payload.reference_url = referenceUrl;
        if (referenceText) payload.reference_text = referenceText;
        if (referenceNotes) payload.reference_notes = referenceNotes;
      }
      const response = await generationAPI.generateReel(payload);
      setResult(response.data.result);
      setCredits(response.data.remainingCredits || credits - 1);
      setLastGenerationId(response.data.generationId || null);
      // Auto-switch to Reference DNA tab if reference mode
      if (referenceMode && response.data.result?.is_reference_based) {
        setActiveTab('reference_analysis');
      }
      toast.success('Reel content pack generated!');
      markFeatureUsed('reel_generator');
      trackJourneyStep('generate', 'generation_complete', 'reel_generator');
      analytics.trackGeneration('reel_generator', 10);
      setTimeout(() => setShowRatingModal(true), 2000);
      setTimeout(() => setShowUpsellModal(true), 4000);
    } catch (error) {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePerformanceVariation = async (variationType) => {
    if (!result || loading) return;
    const variationMap = {
      stronger_hook: 'Rewrite with a much stronger, more scroll-stopping hook using shock or curiosity. Make the first 2 seconds irresistible.',
      higher_retention: 'Optimize for maximum watch time. Add pattern interrupts, cliffhangers, and keep viewers watching until the end.',
      more_emotional: 'Make the content deeply emotional. Use storytelling, vulnerability, or aspirational emotions to create a strong connection.',
      more_viral: 'Optimize for shareability and virality. Make people want to tag friends, save, and share. Use trending formats.',
      more_sales: 'Shift focus to drive sales or conversions. Make the CTA more compelling and the value proposition crystal clear.',
      shorter_punchier: 'Cut all filler. Make every word count. Compress the script to be shorter, faster-paced, and more impactful.',
      better_cta: 'Rewrite with a much stronger call-to-action that feels natural but creates urgency to act immediately.',
      platform_optimized: `Optimize specifically for ${formData.platform}. Use platform-native language, trends, and formatting.`,
    };
    const instruction = variationMap[variationType];
    if (!instruction) return;

    setLoading(true);
    try {
      const variationData = {
        ...formData,
        topic: `[VARIATION: ${instruction}] Original topic: ${formData.topic}. Previous best hook: ${result.best_hook || ''}. Previous CTA: ${result.script?.cta || ''}.`,
      };
      const response = await generationAPI.generateReel(variationData);
      setResult(response.data.result);
      setCredits(response.data.remainingCredits || credits - 1);
      setLastGenerationId(response.data.generationId || null);
      toast.success('Performance variation generated!');
    } catch (error) {
      toast.error('Variation failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadClick = () => {
    if (isFreeTier) { setShowUpgradeModal(true); } else { downloadJSON(false); }
  };

  const downloadJSON = (withWatermark = true) => {
    setShowUpgradeModal(false);
    const downloadContent = (isFreeTier && withWatermark)
      ? { ...result, watermark: 'Made with Visionary Suite - Upgrade to remove watermark', free_tier: true }
      : result;
    const blob = new Blob([JSON.stringify(downloadContent, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reel-content-pack-${Date.now()}.json`;
    a.click();
    toast.success('Downloaded!');
  };

  const handleGenerateVideo = (config) => {
    toast.info(`Video generation with ${config.quality} quality coming soon!`);
  };

  const set = (key) => (value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    setActivePreset(null); // Clear preset indicator when user customizes
  };

  const handlePresetSelect = (preset) => {
    if (activePreset === preset.id) {
      setActivePreset(null);
      return;
    }
    setActivePreset(preset.id);
    setFormData(prev => ({ ...prev, ...preset.config }));
    toast.success(`${preset.label} preset applied`);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'script': return <ScriptTab result={result} />;
      case 'hooks': return <HooksTab result={result} />;
      case 'caption': return <CaptionTab result={result} />;
      case 'hashtags': return <HashtagsTab result={result} />;
      case 'shot_list': return <ShotListTab result={result} />;
      case 'visual_prompts': return <VisualPromptsTab result={result} />;
      case 'voiceover': return <VoiceoverTab result={result} />;
      case 'reference_analysis': return <ReferenceAnalysisTab result={result} />;
      default: return <ScriptTab result={result} />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} onDownloadWithWatermark={() => downloadJSON(true)} />
      <VideoConfigModal isOpen={showVideoConfig} onClose={() => setShowVideoConfig(false)} onGenerate={handleGenerateVideo} />

      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800">
                <ArrowLeft className="w-4 h-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">Dashboard</span>
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <span className="text-lg font-bold text-white">Reel Engine</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 bg-indigo-500/20 border border-indigo-500/30 rounded-full px-3 py-1.5">
              <Coins className="w-3.5 h-3.5 text-indigo-400" />
              <span className="font-semibold text-indigo-300 text-sm" data-testid="reel-credits-display">
                {credits === null ? <span className="inline-block w-8 h-4 bg-indigo-500/20 rounded animate-pulse" /> : credits >= 999999 ? 'Unlimited' : credits.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {creditsLoaded && credits === 0 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="exhausted" />}
        {creditsLoaded && credits > 0 && credits <= 10 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="low" />}
        {creditsLoaded && isFreeTier && credits > 10 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="watermark" />}

        <div className="grid lg:grid-cols-5 gap-6">
          {/* ──────────── INPUT PANEL (2 cols) ──────────── */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-xl">
              <h2 className="text-lg font-bold text-white mb-3">Create Reel</h2>

              {/* Quick Presets */}
              <div className="mb-3" data-testid="quick-presets">
                <Label className="text-slate-400 text-[10px] font-semibold uppercase tracking-wider mb-2 block">Quick Presets</Label>
                <div className="flex flex-wrap gap-1.5">
                  {QUICK_PRESETS.map(preset => {
                    const Icon = preset.icon;
                    const isActive = activePreset === preset.id;
                    return (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() => handlePresetSelect(preset)}
                        className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all ${
                          isActive ? PRESET_ACTIVE_COLORS[preset.color] : PRESET_COLORS[preset.color]
                        }`}
                        data-testid={`preset-${preset.id}`}
                      >
                        <Icon className="w-3 h-3" />
                        {preset.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {hasRemix && <RemixBanner sourceTool={remixSource} sourceTitle={remixTitle} onDismiss={dismissRemix} />}

              {/* Reference Mode Toggle */}
              <div className="flex items-center gap-2 mb-1" data-testid="reference-mode-section">
                <button
                  type="button"
                  onClick={() => setReferenceMode(false)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    !referenceMode
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-500 hover:text-slate-300 border border-transparent'
                  }`}
                  data-testid="mode-fresh"
                >
                  <Sparkles className="w-3 h-3" />
                  Fresh Create
                </button>
                <button
                  type="button"
                  onClick={() => setReferenceMode(true)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    referenceMode
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'text-slate-500 hover:text-slate-300 border border-transparent'
                  }`}
                  data-testid="mode-reference"
                >
                  <Link2 className="w-3 h-3" />
                  From Reference
                </button>
              </div>

              {/* Reference Inputs (visible in reference mode) */}
              {referenceMode && (
                <div className="space-y-3 bg-amber-500/5 border border-amber-500/15 rounded-xl p-3.5 mb-1" data-testid="reference-inputs">
                  <div>
                    <Label className="text-amber-400/80 text-xs font-medium mb-1.5 block flex items-center gap-1.5">
                      <Link2 className="w-3 h-3" />
                      Reel URL (optional)
                    </Label>
                    <input
                      type="url"
                      value={referenceUrl}
                      onChange={(e) => setReferenceUrl(e.target.value)}
                      placeholder="https://example.com/reel/... or any video URL"
                      className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-white text-sm placeholder:text-slate-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none"
                      data-testid="reference-url-input"
                    />
                    <p className="text-[10px] text-slate-600 mt-1">We'll extract structure from the page. If extraction fails, paste text below.</p>
                  </div>
                  <div>
                    <Label className="text-amber-400/80 text-xs font-medium mb-1.5 block flex items-center gap-1.5">
                      <FileCode className="w-3 h-3" />
                      Paste Script / Caption / Transcript
                    </Label>
                    <Textarea
                      value={referenceText}
                      onChange={(e) => setReferenceText(e.target.value)}
                      placeholder="Paste the reel's script, caption, or transcript here..."
                      rows={3}
                      className="bg-slate-900/60 border-slate-700/50 text-white placeholder:text-slate-600 focus:border-amber-500/50 focus:ring-amber-500/20 resize-none text-sm"
                      data-testid="reference-text-input"
                    />
                  </div>
                  <div>
                    <Label className="text-amber-400/80 text-xs font-medium mb-1.5 block flex items-center gap-1.5">
                      <MessageSquare className="w-3 h-3" />
                      Notes (optional)
                    </Label>
                    <input
                      type="text"
                      value={referenceNotes}
                      onChange={(e) => setReferenceNotes(e.target.value)}
                      placeholder="e.g., Keep the hook style but make it more luxury"
                      className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-white text-sm placeholder:text-slate-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none"
                      data-testid="reference-notes-input"
                    />
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4" data-testid="reel-form">
                {/* Topic */}
                <div>
                  <Label className="text-slate-400 text-xs font-medium mb-1.5 block">Topic / Idea *</Label>
                  <Textarea
                    value={formData.topic}
                    onChange={(e) => set('topic')(e.target.value)}
                    placeholder="E.g., Morning routines of millionaires, 5 fashion hacks for winter"
                    required rows={3}
                    className="bg-slate-900/60 border-slate-700/50 text-white placeholder:text-slate-600 focus:border-indigo-500 focus:ring-indigo-500/20 resize-none text-sm"
                    data-testid="reel-topic-input"
                    data-guide="reel-input"
                  />
                </div>

                {/* Primary Controls Grid */}
                <div className="grid grid-cols-2 gap-3" data-guide="reel-options">
                  <CompactSelect label="Platform" value={formData.platform} onChange={set('platform')} options={PLATFORMS} testId="reel-platform-select" />
                  <CompactSelect label="Hook Style" value={formData.hookStyle} onChange={set('hookStyle')} options={HOOK_STYLES} testId="reel-hook-style-select" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <CompactSelect label="Reel Format" value={formData.reelFormat} onChange={set('reelFormat')} options={REEL_FORMATS} testId="reel-format-select" />
                  <CompactSelect label="CTA Type" value={formData.ctaType} onChange={set('ctaType')} options={CTA_TYPES} testId="reel-cta-select" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <CompactSelect label="Objective" value={formData.goal} onChange={set('goal')} options={CONTENT_OBJECTIVES} testId="reel-objective-select" />
                  <CompactSelect label="Output Type" value={formData.outputType} onChange={set('outputType')} options={OUTPUT_TYPES} testId="reel-output-type-select" />
                </div>

                {/* Advanced Controls (Collapsible) */}
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-slate-300 transition-colors py-1"
                  data-testid="advanced-controls-toggle"
                >
                  <span className="font-medium">Advanced Controls</span>
                  {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showAdvanced && (
                  <div className="space-y-3 pt-1 border-t border-slate-700/30">
                    <div className="grid grid-cols-2 gap-3">
                      <CompactSelect label="Niche" value={formData.niche} onChange={set('niche')} options={['Luxury', 'Relationships', 'Health', 'Finance', 'Tech', 'Fashion', 'Food', 'Travel', 'Education', 'Entertainment', 'Custom']} testId="reel-niche-select" />
                      <CompactSelect label="Tone" value={formData.tone} onChange={set('tone')} options={TONES} testId="reel-tone-select" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <CompactSelect label="Duration" value={formData.duration} onChange={set('duration')} options={DURATIONS} testId="reel-duration-select" />
                      <CompactSelect label="Language" value={formData.language} onChange={set('language')} options={[
                        'English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese', 'Russian',
                        'Japanese', 'Korean', 'Chinese', 'Arabic', 'Hindi', 'Hinglish',
                        'Telugu', 'Tamil', 'Kannada', 'Malayalam', 'Marathi', 'Bengali', 'Gujarati', 'Punjabi',
                        'Dutch', 'Polish', 'Swedish', 'Norwegian', 'Turkish', 'Thai', 'Vietnamese', 'Indonesian',
                      ]} testId="reel-language-select" />
                    </div>
                    <CompactSelect label="Audience" value={formData.audience} onChange={set('audience')} options={[
                      'General', 'Gen Z (13-24)', 'Millennials (25-40)', 'Gen X (41-56)',
                      'Young Professionals', 'Entrepreneurs', 'Business Executives', 'Freelancers',
                      'College Students', 'Parents', 'Fitness Enthusiasts', 'Travelers', 'Foodies',
                      'Tech Enthusiasts', 'Fashion Lovers', 'Investors', 'Crypto Enthusiasts', 'Luxury Consumers',
                    ]} testId="reel-audience-select" />
                  </div>
                )}

                {/* Cost + Generate */}
                <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-indigo-300 text-sm">
                    <Coins className="w-3.5 h-3.5" />
                    <span className="font-medium">10 credits</span>
                  </div>
                  <span className="text-xs text-slate-500">per generation</span>
                </div>

                <Button
                  type="submit" disabled={loading}
                  className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-indigo-500/20"
                  data-testid="reel-generate-btn"
                  data-guide="generate-btn"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating...</>
                  ) : (
                    <><Sparkles className="w-4 h-4 mr-2" />Generate Content Pack</>
                  )}
                </Button>
              </form>
            </div>
          </div>

          {/* ──────────── OUTPUT PANEL (3 cols) ──────────── */}
          <div className="lg:col-span-3 space-y-4" data-guide="reel-output">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-xl">
              {/* Output Header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-white">
                  {result ? 'Content Pack' : 'Generated Output'}
                </h2>
                {result && (
                  <div className="flex gap-2">
                    <ShareButton type="REEL" title={result.best_hook || ''} preview={result.caption_short || ''} />
                    <Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(JSON.stringify(result, null, 2)); toast.success('Copied!'); }} className="border-slate-700 text-slate-300 hover:bg-slate-700 h-8 text-xs" data-testid="copy-result-btn">
                      <Copy className="w-3.5 h-3.5 mr-1" />Copy
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleDownloadClick} className="border-slate-700 text-slate-300 hover:bg-slate-700 h-8 text-xs" data-testid="download-result-btn">
                      <Download className="w-3.5 h-3.5 mr-1" />Export
                    </Button>
                  </div>
                )}
              </div>

              {/* Progress */}
              <ReelProgressBar isGenerating={loading} />

              {/* Empty State */}
              {!result && !loading && (
                <div className="text-center py-16 text-slate-500">
                  <Sparkles className="w-10 h-10 mx-auto mb-3 text-slate-700" />
                  <p className="text-sm">Your content pack will appear here</p>
                  <p className="text-xs text-slate-600 mt-1">Configure your reel settings and hit Generate</p>
                </div>
              )}

              {/* Loading */}
              {loading && !result && (
                <WaitingWithGames
                  progress={50} status="Generating your content pack..."
                  estimatedTime="10-30 seconds"
                  onCancel={() => toast.info('Generation in progress - please wait')}
                  currentFeature="/app/reel" showExploreFeatures={true}
                />
              )}

              {/* Result Tabs */}
              {result && (
                <>
                  {/* Free Tier Banner */}
                  {isFreeTier && (
                    <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-3 flex items-start gap-2.5 mb-4">
                      <AlertCircle className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-purple-300 font-medium text-xs">Free tier content includes watermark</p>
                        <p className="text-purple-400/70 text-[11px] mt-0.5"><Link to="/pricing" className="underline font-medium hover:text-purple-300">Upgrade</Link> to remove watermarks.</p>
                      </div>
                    </div>
                  )}

                  {/* Tab Navigation */}
                  <div className="flex overflow-x-auto gap-1 mb-4 pb-1 -mx-1 px-1 scrollbar-hide" data-testid="output-tabs">
                    {OUTPUT_TABS.filter(tab => {
                      // Only show Reference DNA tab when result has reference data
                      if (tab.id === 'reference_analysis') return result?.is_reference_based;
                      return true;
                    }).map(tab => {
                      const Icon = tab.icon;
                      const isActive = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex-shrink-0 ${
                            isActive
                              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                              : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border border-transparent'
                          }`}
                          data-testid={`tab-${tab.id}`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>

                  {/* Tab Content */}
                  <div className="max-h-[500px] overflow-y-auto pr-1 custom-scrollbar">
                    {renderTabContent()}
                  </div>

                  {/* AI Recommendations */}
                  <div className="mt-4">
                    <AIRecommendations result={result} />
                  </div>

                  {/* Generate Video CTA */}
                  <div className="mt-4">
                    <Button
                      onClick={() => setShowVideoConfig(true)}
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-3 rounded-xl"
                      data-testid="generate-video-btn"
                    >
                      <Video className="w-4 h-4 mr-2" />
                      Generate Video from Script
                    </Button>
                  </div>

                  {/* Performance Variations */}
                  <div className="mt-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap className="w-4 h-4 text-amber-400" />
                      <span className="text-sm font-bold text-white">Performance Variations</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="performance-variations">
                      {PERFORMANCE_VARIATIONS.map(v => {
                        const Icon = v.icon;
                        return (
                          <button
                            key={v.id}
                            onClick={() => handlePerformanceVariation(v.id)}
                            disabled={loading}
                            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700/50 text-xs text-slate-400 hover:text-white hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all disabled:opacity-40"
                            data-testid={`variation-${v.id}`}
                          >
                            <Icon className="w-3 h-3" />
                            {v.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Posting Tips */}
                  {result.posting_tips?.length > 0 && (
                    <div className="mt-4 bg-slate-900/30 border border-slate-700/30 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                        <span className="text-xs font-bold text-white uppercase tracking-wider">Posting Tips</span>
                      </div>
                      <ul className="space-y-1.5">
                        {result.posting_tips.map((tip, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-xs text-slate-400">
                            <Check className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Cross-tool actions */}
                  <div className="mt-4">
                    <NextActionHooks
                      toolType="reels" prompt={formData.topic}
                      settings={{ niche: formData.niche, tone: formData.tone, duration: formData.duration }}
                      generationId={lastGenerationId} title={result.best_hook}
                    />
                  </div>
                  <div className="mt-4">
                    <CreationActionsBar
                      toolType="reels" originalPrompt={formData.topic}
                      originalSettings={{ niche: formData.niche, tone: formData.tone, duration: formData.duration }}
                      parentGenerationId={lastGenerationId} remixSourceTitle={result.best_hook}
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* HelpGuide removed Apr 26 2026 — P0 UI cleanup */}
      <RatingModal isOpen={showRatingModal} onClose={() => setShowRatingModal(false)} featureKey="reel_generator" relatedRequestId={lastGenerationId} onSubmitSuccess={() => setShowRatingModal(false)} />
      {showUpsellModal && <UpsellModal isOpen={showUpsellModal} credits={credits} onClose={() => setShowUpsellModal(false)} />}
    </div>
  );
}
