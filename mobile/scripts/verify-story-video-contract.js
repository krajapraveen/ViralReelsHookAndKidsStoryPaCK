const fs = require('fs');
const path = require('path');

const contractPath = path.join(__dirname, '..', 'src', 'contracts', 'storyVideo.ts');
const toolPath = path.join(__dirname, '..', 'app', 'tools', '[tool].tsx');
const contract = fs.readFileSync(contractPath, 'utf8');
const tool = fs.readFileSync(toolPath, 'utf8');

const requiredSnippets = [
  "STORY_VIDEO_QUALITY_OPTIONS",
  "{ label: 'Fast - 1-2 min', value: 'fast' }",
  "{ label: 'Balanced - 2-4 min', value: 'balanced' }",
  "{ label: 'High Quality - 4-8 min', value: 'high_quality' }",
  "quality_mode: z.string().default('balanced')",
  "quality_mode: data.quality_mode",
  "duration_seconds: durationSeconds",
];

for (const snippet of requiredSnippets) {
  if (!contract.includes(snippet)) {
    throw new Error(`Missing Story Video contract snippet: ${snippet}`);
  }
}

if (!tool.includes("quality_mode: 'balanced'")) {
  throw new Error("Story Video form must default quality_mode to balanced");
}

if (!tool.includes("options={STORY_VIDEO_QUALITY_OPTIONS}")) {
  throw new Error("Story Video form must render the quality mode selector");
}

console.log("Story Video mobile contract checks passed");
