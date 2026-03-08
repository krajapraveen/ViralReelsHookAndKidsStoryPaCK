import React, { useState } from 'react';
import { HelpCircle, X, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Lightbulb, Zap, Copy, Info } from 'lucide-react';
import { Button } from './ui/button';

/**
 * Feature Help Panel Component
 * Provides contextual help for each feature with:
 * - Step-by-step instructions
 * - Example inputs (one-click try)
 * - What not to do section
 * - Common errors & fixes
 * - Credits required
 */

const FeatureHelpPanel = ({ 
  featureName,
  steps = [],
  exampleInput = null,
  onTryExample = null,
  doNotList = [],
  commonErrors = [],
  creditsRequired = 1,
  tips = [],
  isExpanded = false
}) => {
  const [expanded, setExpanded] = useState(isExpanded);
  const [showDoNot, setShowDoNot] = useState(false);
  const [showErrors, setShowErrors] = useState(false);

  return (
    <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl overflow-hidden" data-testid="feature-help-panel">
      {/* Header - Always visible */}
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-violet-400" />
          <span className="font-medium text-white">How to use {featureName}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-violet-400 bg-violet-500/20 px-2 py-0.5 rounded">
            {creditsRequired} credits
          </span>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-slate-700/50">
          {/* Steps */}
          <div className="pt-4">
            <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              Quick Steps
            </h4>
            <ol className="space-y-2">
              {steps.map((step, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 flex items-center justify-center text-xs font-bold">
                    {idx + 1}
                  </span>
                  <span className="text-slate-300 pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Try Example Button */}
          {exampleInput && onTryExample && (
            <div className="bg-slate-900/50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Try this example:</p>
                  <p className="text-sm text-white font-mono truncate max-w-[200px]">
                    "{typeof exampleInput === 'string' ? exampleInput : 'Example Input'}"
                  </p>
                </div>
                <Button 
                  size="sm" 
                  onClick={onTryExample}
                  className="bg-violet-600 hover:bg-violet-700"
                  data-testid="try-example-btn"
                >
                  <Zap className="w-4 h-4 mr-1" />
                  Try It
                </Button>
              </div>
            </div>
          )}

          {/* Tips */}
          {tips.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-amber-400 mb-2 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" />
                Pro Tips
              </h4>
              <ul className="space-y-1.5">
                {tips.map((tip, idx) => (
                  <li key={idx} className="text-xs text-amber-200/80 flex items-start gap-2">
                    <span>•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* What NOT to do - Collapsible */}
          {doNotList.length > 0 && (
            <div className="border border-red-500/20 rounded-lg overflow-hidden">
              <button
                onClick={() => setShowDoNot(!showDoNot)}
                className="w-full px-3 py-2 bg-red-500/10 flex items-center justify-between hover:bg-red-500/20 transition-colors"
              >
                <span className="text-sm font-medium text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  What NOT to include
                </span>
                {showDoNot ? (
                  <ChevronUp className="w-4 h-4 text-red-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-red-400" />
                )}
              </button>
              {showDoNot && (
                <ul className="px-3 py-2 space-y-1.5">
                  {doNotList.map((item, idx) => (
                    <li key={idx} className="text-xs text-red-300/80 flex items-start gap-2">
                      <X className="w-3 h-3 flex-shrink-0 mt-0.5" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Common Errors - Collapsible */}
          {commonErrors.length > 0 && (
            <div className="border border-slate-600/30 rounded-lg overflow-hidden">
              <button
                onClick={() => setShowErrors(!showErrors)}
                className="w-full px-3 py-2 bg-slate-800/50 flex items-center justify-between hover:bg-slate-800 transition-colors"
              >
                <span className="text-sm font-medium text-slate-300 flex items-center gap-2">
                  <Info className="w-4 h-4" />
                  Common Errors & Fixes
                </span>
                {showErrors ? (
                  <ChevronUp className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                )}
              </button>
              {showErrors && (
                <div className="px-3 py-2 space-y-3">
                  {commonErrors.map((error, idx) => (
                    <div key={idx} className="text-xs">
                      <p className="text-red-400 font-medium">{error.error}</p>
                      <p className="text-green-400 mt-1">→ {error.fix}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Feature-specific help configurations
 */
export const FEATURE_HELP_CONFIG = {
  photoToComic: {
    featureName: "Photo to Comic",
    creditsRequired: 5,
    steps: [
      "Upload a clear photo with a visible face",
      "Select your preferred comic style (Anime, Storybook, etc.)",
      "Click Generate and wait for the magic!",
      "Download your comic character"
    ],
    exampleInput: "Clear front-facing portrait photo",
    doNotList: [
      "Copyrighted characters (Disney, Marvel, etc.)",
      "Celebrity photos or real people likeness",
      "Blurry or low-quality images",
      "Images where face is obscured or too small",
      "Adult or violent content"
    ],
    commonErrors: [
      { error: "No face detected", fix: "Use a photo where your face is clearly visible and front-facing" },
      { error: "Image too small", fix: "Upload an image at least 512x512 pixels" },
      { error: "Generation failed", fix: "Try a different photo with better lighting" }
    ],
    tips: [
      "Front-facing photos with good lighting work best",
      "Avoid sunglasses or hats covering your face",
      "Simple backgrounds produce cleaner results"
    ]
  },
  coloringBook: {
    featureName: "Coloring Book Creator",
    creditsRequired: 3,
    steps: [
      "Enter a description of what you want to color",
      "Choose a style (Classic, Detailed, Simple, Mandala)",
      "Select the complexity level",
      "Generate and download your coloring page"
    ],
    exampleInput: "A friendly dragon playing with butterflies in a garden",
    doNotList: [
      "Copyrighted characters or brands",
      "Violent or scary content",
      "Celebrity faces or real people",
      "Adult themes"
    ],
    commonErrors: [
      { error: "Lines too thin", fix: "Choose 'Bold' outline style for easier coloring" },
      { error: "Too complex for kids", fix: "Select 'Simple' style for younger children" }
    ],
    tips: [
      "Add details like 'with flowers' or 'in a forest' for richer scenes",
      "Specify age group: 'suitable for 5-year-olds' for simpler designs",
      "Request 'large areas to color' for easier coloring"
    ]
  },
  comicStorybook: {
    featureName: "Comic Storybook Builder",
    creditsRequired: 15,
    steps: [
      "Choose a story template or start from scratch",
      "Define your characters and setting",
      "Write your story scenes or let AI help",
      "Generate comic panels for each scene",
      "Download your complete comic book"
    ],
    exampleInput: "A brave mouse who becomes a knight and saves the cheese kingdom",
    doNotList: [
      "Copyrighted story elements",
      "Real celebrities or public figures",
      "Violent or inappropriate content",
      "Brand names or logos"
    ],
    commonErrors: [
      { error: "Story too long", fix: "Limit to 8-12 scenes for best results" },
      { error: "Characters inconsistent", fix: "Use detailed character descriptions" }
    ],
    tips: [
      "Start with a template for easier story structure",
      "Keep character names simple and unique",
      "Add visual descriptions for each scene"
    ]
  },
  gifMaker: {
    featureName: "Photo Reaction GIF Creator",
    creditsRequired: 5,
    steps: [
      "Upload a photo (preferably with a face)",
      "Select a reaction emotion",
      "Choose animation style and text overlay",
      "Generate and download your GIF"
    ],
    exampleInput: "Surprised reaction with 'OMG!' text",
    doNotList: [
      "Celebrity photos",
      "Copyrighted images",
      "Inappropriate gestures",
      "Brand logos"
    ],
    commonErrors: [
      { error: "GIF not animating", fix: "Try a different browser or download again" },
      { error: "File too large", fix: "Choose 'Optimized' quality for smaller files" }
    ],
    tips: [
      "Expressive faces make better reaction GIFs",
      "Keep text short for readability",
      "Test different emotions to find the perfect one"
    ]
  },
  storyEpisode: {
    featureName: "Story Episode Creator",
    creditsRequired: 8,
    steps: [
      "Select a genre (Adventure, Fantasy, Sci-Fi, etc.)",
      "Name your main character",
      "Choose a theme or moral",
      "Generate your story episode"
    ],
    exampleInput: "Luna, a curious rabbit who discovers a magical forest",
    doNotList: [
      "Copyrighted character names",
      "Real celebrity names",
      "Violent or scary themes for kids",
      "Brand references"
    ],
    commonErrors: [
      { error: "Story too short", fix: "Add more details to your character description" },
      { error: "Theme not matching", fix: "Be specific about the moral or lesson" }
    ],
    tips: [
      "Unique character names avoid copyright issues",
      "Add personality traits for richer stories",
      "Specify target age group for appropriate content"
    ]
  },
  contentChallenge: {
    featureName: "Content Challenge Planner",
    creditsRequired: 5,
    steps: [
      "Select your content platform (Instagram, TikTok, etc.)",
      "Choose challenge duration (7, 14, 30 days)",
      "Pick your niche or topic",
      "Generate your content calendar"
    ],
    exampleInput: "30-day fitness motivation challenge for Instagram",
    doNotList: [
      "Copyrighted challenge names",
      "Misleading health claims",
      "Dangerous challenge ideas",
      "Content promoting harmful behavior"
    ],
    commonErrors: [
      { error: "Ideas too generic", fix: "Be specific about your niche and audience" },
      { error: "Schedule too intense", fix: "Start with a 7-day challenge" }
    ],
    tips: [
      "Pick a specific niche for more targeted ideas",
      "Consider your posting frequency realistically",
      "Add hashtag themes for consistency"
    ]
  },
  captionRewriter: {
    featureName: "Caption Rewriter Pro",
    creditsRequired: 2,
    steps: [
      "Paste your original caption",
      "Select the desired tone (Professional, Casual, Funny, etc.)",
      "Choose the platform for optimization",
      "Get multiple rewritten versions"
    ],
    exampleInput: "Just had coffee. It was good.",
    doNotList: [
      "Copyrighted quotes",
      "Offensive language",
      "Misleading claims",
      "Spam-like content"
    ],
    commonErrors: [
      { error: "Rewrite too different", fix: "Choose 'Light' intensity for subtle changes" },
      { error: "Lost original meaning", fix: "Include key message in your input" }
    ],
    tips: [
      "Include the main message you want to keep",
      "Specify your target audience",
      "Try different tones to find your voice"
    ]
  },
  blueprintLibrary: {
    featureName: "Content Blueprint Library",
    creditsRequired: "Varies",
    steps: [
      "Browse the catalog (Hooks, Frameworks, Story Ideas)",
      "Filter by niche or category",
      "Preview items before purchasing",
      "Unlock individual items or full packs"
    ],
    exampleInput: "Browse viral hooks for the Fitness niche",
    doNotList: [
      "Sharing purchased content publicly",
      "Reselling content as your own product",
      "Using without customization"
    ],
    commonErrors: [
      { error: "Can't unlock", fix: "Check if you have enough credits" },
      { error: "Content locked", fix: "Purchase the item or pack first" }
    ],
    tips: [
      "Start with single items to test",
      "Full packs offer best value",
      "Customize hooks for your niche"
    ]
  }
};

export default FeatureHelpPanel;
