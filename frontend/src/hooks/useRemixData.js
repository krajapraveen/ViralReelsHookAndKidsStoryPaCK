import { useState, useEffect } from 'react';
import { trackToolOpenPrefilled } from '../utils/growthAnalytics';

const TTL_MS = 10 * 60 * 1000; // 10 minutes

// Tool-specific field mapping: what each tool can consume from remix_data
const TOOL_FIELDS = {
  'story-video-studio': ['story_text', 'animation_style', 'age_group', 'voice_preset', 'title'],
  'reels': ['topic', 'niche', 'tone', 'duration', 'language', 'goal', 'audience'],
  'photo-to-comic': ['style'],
  'gif-maker': ['emotion', 'style', 'background'],
  'comic-storybook': ['story_text', 'genre', 'style'],
  'bedtime-story-builder': ['theme', 'character', 'moral', 'ageGroup'],
  'caption-rewriter': ['text', 'tone'],
  'brand-story-builder': ['businessName', 'mission', 'industry', 'tone'],
  'daily-viral-ideas': [],
};

/**
 * useRemixData — reads and clears remix_data from localStorage.
 * Returns { remixData, sourceTool, sourceTitle, consumed } 
 * where remixData.settings contains the source tool's settings.
 * 
 * @param {string} currentTool - current tool identifier 
 * @returns {{ remixData: object|null, sourceTool: string|null, sourceTitle: string|null, consumed: boolean, dismiss: () => void }}
 */
export function useRemixData(currentTool) {
  const [state, setState] = useState({
    remixData: null,
    sourceTool: null,
    sourceTitle: null,
    consumed: false,
  });

  useEffect(() => {
    try {
      // Check navigation state first, then localStorage
      const navState = window.history?.state?.usr;
      let raw = navState;

      if (!raw?.remixFrom) {
        const stored = localStorage.getItem('remix_data');
        if (!stored) return;
        raw = JSON.parse(stored);
      }

      if (!raw) return;

      // TTL check
      if (raw.timestamp && Date.now() - raw.timestamp > TTL_MS) {
        localStorage.removeItem('remix_data');
        return;
      }

      // Don't consume your own data (remix-to-self is handled differently by tools)
      const sourceFrom = raw.remixFrom?.tool || raw.source_tool;

      // Validate the data has meaningful content
      if (!raw.prompt && !raw.remixFrom?.prompt) {
        localStorage.removeItem('remix_data');
        return;
      }

      setState({
        remixData: raw,
        sourceTool: sourceFrom,
        sourceTitle: raw.remixFrom?.title || raw.title || null,
        consumed: true,
      });

      // Track prefilled tool open
      trackToolOpenPrefilled(currentTool, raw.remixFrom?.parentId || raw.source_slug);

      // Clear immediately — single consumption
      localStorage.removeItem('remix_data');
    } catch {
      localStorage.removeItem('remix_data');
    }
  }, [currentTool]);

  const dismiss = () => setState(prev => ({ ...prev, consumed: false }));

  return { ...state, dismiss };
}

// Map source tool settings to target tool fields
export function mapRemixToFields(remixData, targetTool) {
  if (!remixData) return {};

  const prompt = remixData.prompt || remixData.remixFrom?.prompt || '';
  const settings = remixData.remixFrom?.settings || {};
  const mapped = {};

  switch (targetTool) {
    case 'story-video-studio':
      mapped.story_text = prompt;
      if (settings.animation_style || settings.style) mapped.animation_style = settings.animation_style || settings.style;
      if (settings.age_group || settings.ageGroup) mapped.age_group = settings.age_group || settings.ageGroup;
      if (settings.voice_preset) mapped.voice_preset = settings.voice_preset;
      mapped.title = remixData.remixFrom?.title ? `From: ${remixData.remixFrom.title}` : '';
      break;

    case 'reels':
      mapped.topic = prompt;
      if (settings.niche) mapped.niche = settings.niche;
      if (settings.tone) mapped.tone = settings.tone;
      if (settings.duration) mapped.duration = settings.duration;
      break;

    case 'gif-maker':
      if (settings.emotion) mapped.emotion = settings.emotion;
      if (settings.style) mapped.style = settings.style;
      if (settings.background) mapped.background = settings.background;
      break;

    case 'comic-storybook':
      mapped.story_text = prompt;
      if (settings.genre) mapped.genre = settings.genre;
      if (settings.style) mapped.style = settings.style;
      break;

    case 'comic-storybook-builder':
      mapped.storyIdea = prompt;
      if (settings.genre) mapped.genre = settings.genre;
      break;

    case 'bedtime-story-builder':
      mapped.prompt = prompt;
      if (settings.theme) mapped.theme = settings.theme;
      if (settings.ageGroup) mapped.ageGroup = settings.ageGroup;
      if (settings.moral) mapped.moral = settings.moral;
      break;

    case 'caption-rewriter':
      mapped.text = prompt;
      if (settings.tone) mapped.tone = settings.tone;
      break;

    case 'brand-story-builder':
      mapped.mission = prompt;
      if (settings.industry) mapped.industry = settings.industry;
      if (settings.tone) mapped.tone = settings.tone;
      break;

    default:
      mapped.prompt = prompt;
      break;
  }

  return mapped;
}

// Pretty-print source tool names
const TOOL_LABELS = {
  'gif-maker': 'GIF Maker',
  'reels': 'Reel Generator',
  'photo-to-comic': 'Photo to Comic',
  'story-video-studio': 'Story Video',
  'comic-storybook': 'Comic Storybook',
  'comic-storybook-builder': 'Comic Storybook',
  'bedtime-story-builder': 'Bedtime Story',
  'caption-rewriter': 'Caption Rewriter',
  'brand-story-builder': 'Brand Story',
  'daily-viral-ideas': 'Viral Ideas',
};

export function getToolLabel(toolId) {
  return TOOL_LABELS[toolId] || toolId;
}
