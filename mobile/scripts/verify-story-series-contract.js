const fs = require('fs');
const path = require('path');

const api = fs.readFileSync(path.join(__dirname, '..', 'src', 'api', 'storySeries.ts'), 'utf8');
const contract = fs.readFileSync(path.join(__dirname, '..', 'src', 'contracts', 'storySeries.ts'), 'utf8');
const listScreen = fs.readFileSync(path.join(__dirname, '..', 'app', 'tools', 'story-series.tsx'), 'utf8');
const detailScreen = fs.readFileSync(path.join(__dirname, '..', 'app', 'series', '[seriesId].tsx'), 'utf8');

const requiredApi = [
  '/api/story-series/create',
  '/api/story-series/my-series',
  '/plan-episode',
  '/generate-episode',
  '/suggestions',
  '/update-memory',
  '/share',
  '/rewards',
  '/extracted-characters',
  '/confirm-characters',
  '/dismiss-extraction',
];

for (const snippet of requiredApi) {
  if (!api.includes(snippet)) {
    throw new Error(`Story Series API client missing ${snippet}`);
  }
}

for (const value of ['cartoon_2d', 'anime', 'watercolor', 'cinematic', 'comic', 'kids_storybook', 'black_white_ink']) {
  if (!contract.includes(value)) {
    throw new Error(`Story Series style option missing ${value}`);
  }
}

for (const value of ['story_video', 'comic', 'continue', 'twist', 'stakes', 'flashback', 'spinoff', 'custom']) {
  if (!contract.includes(value)) {
    throw new Error(`Story Series option missing ${value}`);
  }
}

for (const snippet of ['createSeriesSchema', 'SERIES_STYLE_OPTIONS', 'SERIES_TOOL_OPTIONS']) {
  if (!listScreen.includes(snippet)) {
    throw new Error(`Story Series list/create screen missing ${snippet}`);
  }
}

for (const snippet of ['planEpisode', 'generateEpisode', 'episodeStatus', 'suggestions', 'updateMemory', 'share', 'rewards']) {
  if (!detailScreen.includes(snippet)) {
    throw new Error(`Story Series detail screen missing ${snippet}`);
  }
}

if (!detailScreen.includes('_fallback')) {
  throw new Error('Story Series detail screen must surface fallback planner status');
}

console.log('Story Series mobile contract checks passed');
