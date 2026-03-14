import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { toast } from 'sonner';
import {
  Zap, RefreshCw, Palette, ArrowRight, Edit3, ChevronDown,
  Sparkles, Wand2, Send
} from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const TOOL_ROUTES = {
  'story-video-studio': '/app/story-video-studio',
  'reels': '/app/reels',
  'photo-to-comic': '/app/photo-to-comic',
  'gif-maker': '/app/gif-maker',
  'stories': '/app/stories',
  'bedtime-story-builder': '/app/bedtime-story-builder',
  'comic-storybook': '/app/comic-storybook',
  'coloring-book': '/app/coloring-book',
};

export default function CreationActionsBar({
  toolType,
  originalPrompt = '',
  originalSettings = {},
  parentGenerationId = null,
  originalGenerationId = null,
  remixSourceTitle = null,
}) {
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [showPromptEdit, setShowPromptEdit] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState('');
  const [showStylePicker, setShowStylePicker] = useState(false);

  useEffect(() => {
    if (!toolType) return;
    axios.get(`${API}/api/remix/variations/${toolType}`)
      .then(r => setConfig(r.data))
      .catch(() => {});
  }, [toolType]);

  useEffect(() => {
    setEditedPrompt(originalPrompt);
  }, [originalPrompt]);

  const trackAndNavigate = async (targetTool, variationType, label, modifier, style) => {
    const token = localStorage.getItem('token');
    const finalPrompt = modifier
      ? `${originalPrompt}. ${modifier}`
      : originalPrompt;

    // Track remix event
    try {
      await axios.post(`${API}/api/remix/track`, {
        source_tool: toolType,
        target_tool: targetTool,
        original_prompt: originalPrompt,
        variation_type: variationType,
        variation_label: label,
        modifier: modifier || '',
        style: style || null,
        original_generation_id: originalGenerationId,
        parent_generation_id: parentGenerationId,
        original_settings: originalSettings,
      }, { headers: { Authorization: `Bearer ${token}` } });
    } catch {}

    // Navigate to target tool with remix context
    const route = TOOL_ROUTES[targetTool] || `/app/${targetTool}`;
    const stateData = {
      prompt: finalPrompt,
      remixFrom: {
        tool: toolType,
        prompt: originalPrompt,
        settings: originalSettings,
        title: remixSourceTitle,
        parentId: parentGenerationId,
        originalId: originalGenerationId || parentGenerationId,
      }
    };
    localStorage.setItem('remix_data', JSON.stringify(stateData));
    navigate(route, { state: stateData });
    toast.success(`Creating ${label}...`);
  };

  const handleQuickVariation = (item) => {
    trackAndNavigate(toolType, 'quick', item.label, item.modifier, null);
  };

  const handleStyleChange = (style) => {
    setShowStylePicker(false);
    trackAndNavigate(toolType, 'style', `Style: ${style}`, `Recreate in ${style} style`, style);
  };

  const handleAction = (action) => {
    const modifier = action.type === 'convert'
      ? `Convert this into a ${action.label.replace('Turn Into ', '').toLowerCase()}`
      : action.type === 'continue'
        ? 'Continue the story from where it left off'
        : action.label;
    trackAndNavigate(action.target, action.type, action.label, modifier, null);
  };

  const handleRegenerate = () => {
    trackAndNavigate(toolType, 'regenerate', 'Regenerate', '', null);
  };

  const handlePromptRemix = () => {
    if (!editedPrompt.trim()) return;
    const token = localStorage.getItem('token');
    try {
      axios.post(`${API}/api/remix/track`, {
        source_tool: toolType,
        target_tool: toolType,
        original_prompt: originalPrompt,
        variation_type: 'prompt_edit',
        variation_label: 'Prompt Remix',
        modifier: editedPrompt,
        original_generation_id: originalGenerationId,
        parent_generation_id: parentGenerationId,
      }, { headers: { Authorization: `Bearer ${token}` } });
    } catch {}

    const route = TOOL_ROUTES[toolType] || `/app/${toolType}`;
    navigate(route, {
      state: {
        prompt: editedPrompt,
        remixFrom: {
          tool: toolType,
          prompt: originalPrompt,
          settings: originalSettings,
          title: remixSourceTitle,
          parentId: parentGenerationId,
          originalId: originalGenerationId || parentGenerationId,
        }
      }
    });
    toast.success('Generating remix...');
  };

  if (!config || !originalPrompt) return null;

  const crossToolActions = config.actions?.filter(a => a.target !== toolType) || [];
  const sameToolActions = config.actions?.filter(a => a.target === toolType) || [];

  return (
    <div className="mt-5 rounded-2xl border border-white/[0.06] bg-[#0A1128]/80 backdrop-blur-sm overflow-hidden" data-testid="creation-actions-bar">
      {/* Remix Source Tag */}
      {remixSourceTitle && (
        <div className="px-4 py-2 bg-indigo-500/5 border-b border-white/[0.04] flex items-center gap-2">
          <RefreshCw className="w-3 h-3 text-indigo-400/60" />
          <span className="text-[11px] text-indigo-400/60">Remixed from: <span className="text-indigo-300/80">{remixSourceTitle}</span></span>
        </div>
      )}

      {/* Quick Variations Row */}
      {config.quick?.length > 0 && (
        <div className="px-4 pt-4 pb-3" data-testid="quick-variations">
          <div className="flex items-center gap-2 mb-2.5">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[11px] font-semibold text-white/40 uppercase tracking-wider">Quick Variations</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {config.quick.map((item, i) => (
              <button
                key={i}
                onClick={() => handleQuickVariation(item)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-white/60 hover:bg-indigo-500/10 hover:border-indigo-500/20 hover:text-indigo-300 transition-all"
                data-testid={`quick-var-${i}`}
              >
                {item.label}
              </button>
            ))}
            <button
              onClick={handleRegenerate}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-white/60 hover:bg-emerald-500/10 hover:border-emerald-500/20 hover:text-emerald-300 transition-all flex items-center gap-1.5"
              data-testid="regenerate-btn"
            >
              <RefreshCw className="w-3 h-3" /> Regenerate
            </button>
          </div>
        </div>
      )}

      <div className="border-t border-white/[0.04]" />

      {/* Style Switcher + Same-Tool Actions */}
      <div className="px-4 py-3 flex flex-wrap items-center gap-2">
        {/* Style Dropdown */}
        {config.styles?.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowStylePicker(!showStylePicker)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-white/50 hover:bg-violet-500/10 hover:border-violet-500/20 hover:text-violet-300 transition-all"
              data-testid="style-switcher-btn"
            >
              <Palette className="w-3 h-3" /> Change Style <ChevronDown className="w-3 h-3" />
            </button>
            {showStylePicker && (
              <div className="absolute top-full left-0 mt-1 bg-[#111827] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 z-20 min-w-[140px] py-1" data-testid="style-picker-dropdown">
                {config.styles.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleStyleChange(s)}
                    className="w-full text-left px-3 py-2 text-xs text-white/60 hover:bg-white/[0.05] hover:text-white transition-colors"
                    data-testid={`style-option-${i}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Same-tool variation actions */}
        {sameToolActions.map((action, i) => (
          <button
            key={i}
            onClick={() => handleAction(action)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-white/50 hover:bg-white/[0.06] hover:text-white/80 transition-all flex items-center gap-1.5"
            data-testid={`action-${action.label.replace(/\s/g, '-').toLowerCase()}`}
          >
            <Wand2 className="w-3 h-3" /> {action.label}
          </button>
        ))}

        {/* Prompt Edit Toggle */}
        <button
          onClick={() => setShowPromptEdit(!showPromptEdit)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-white/50 hover:bg-cyan-500/10 hover:border-cyan-500/20 hover:text-cyan-300 transition-all flex items-center gap-1.5"
          data-testid="prompt-remix-toggle"
        >
          <Edit3 className="w-3 h-3" /> Remix Prompt
        </button>
      </div>

      {/* Prompt Edit Box */}
      {showPromptEdit && (
        <div className="px-4 pb-3" data-testid="prompt-remix-section">
          <div className="flex gap-2">
            <input
              type="text"
              value={editedPrompt}
              onChange={(e) => setEditedPrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePromptRemix()}
              className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20"
              placeholder="Edit prompt and remix..."
              data-testid="prompt-remix-input"
            />
            <Button
              onClick={handlePromptRemix}
              size="sm"
              className="bg-gradient-to-r from-indigo-500 to-blue-600 text-white rounded-lg px-4"
              data-testid="prompt-remix-submit"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Cross-Tool Conversions */}
      {crossToolActions.length > 0 && (
        <>
          <div className="border-t border-white/[0.04]" />
          <div className="px-4 py-3" data-testid="cross-tool-conversions">
            <div className="flex items-center gap-2 mb-2.5">
              <ArrowRight className="w-3.5 h-3.5 text-pink-400" />
              <span className="text-[11px] font-semibold text-white/40 uppercase tracking-wider">Convert Creation</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {crossToolActions.map((action, i) => (
                <button
                  key={i}
                  onClick={() => handleAction(action)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-pink-500/[0.06] border border-pink-500/15 text-pink-300/70 hover:bg-pink-500/15 hover:border-pink-500/30 hover:text-pink-200 transition-all flex items-center gap-1.5"
                  data-testid={`convert-${action.label.replace(/\s/g, '-').toLowerCase()}`}
                >
                  <Sparkles className="w-3 h-3" /> {action.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
