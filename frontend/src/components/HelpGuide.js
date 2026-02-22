import React, { useState } from 'react';
import { HelpCircle, X, ChevronRight, ExternalLink, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

// Help content for each page/section
const HELP_CONTENT = {
  'reel-generator': {
    title: 'Reel Generator',
    description: 'Create viral reel scripts with hooks, captions, and hashtags.',
    credits: '10 credits per reel',
    steps: [
      'Enter your niche (e.g., fitness, business, motivation)',
      'Select tone and style preferences',
      'Click "Generate" to create your content',
      'Copy scripts, hooks, or hashtags individually'
    ],
    tips: [
      'Use specific niches for better results',
      'Mix trending topics with evergreen content',
      'The first hook is usually the strongest performer'
    ]
  },
  'story-generator': {
    title: 'Story Generator',
    description: 'Generate complete kids story video packs with scenes and voiceovers.',
    credits: '25 credits per story',
    steps: [
      'Enter a story theme or moral lesson',
      'Choose age group and story length',
      'Click "Generate" to create your story pack',
      'Download scene prompts and voiceover scripts'
    ],
    tips: [
      'Keep morals simple and relatable',
      'Shorter stories (8-10 scenes) perform better on YouTube',
      'Use the scene prompts for AI image generation'
    ]
  },
  'creator-tools': {
    title: 'Creator Tools',
    description: 'Suite of tools for content creators: calendars, carousels, hashtags, and more.',
    credits: 'Varies by tool (see each tab)',
    steps: [
      'Choose a tool from the tabs above',
      'Fill in the required fields',
      'Click the generate/get button',
      'Copy or download your results'
    ],
    tips: [
      'Hashtag Bank is FREE - no credits needed',
      'Trending Topics is FREE and updates weekly',
      'Content Calendar helps plan your posting schedule'
    ],
    tabs: {
      calendar: { title: 'Content Calendar', credits: '10-25 credits', desc: 'Plan 30 days of content ideas' },
      carousel: { title: 'Carousel Generator', credits: '3 credits', desc: 'Create engaging carousel posts' },
      hashtags: { title: 'Hashtag Bank', credits: 'FREE', desc: 'Curated hashtags by niche' },
      thumbnails: { title: 'Thumbnail Text', credits: 'FREE', desc: 'Generate attention-grabbing text' },
      trending: { title: 'Trending Topics', credits: 'FREE', desc: 'Weekly trending content ideas' }
    }
  },
  'genstudio': {
    title: 'GenStudio',
    description: 'AI-powered image and video generation studio.',
    credits: 'Text-to-Image: 5 credits | Image-to-Video: 15 credits',
    steps: [
      'Navigate to the desired generation type',
      'Enter your prompt or upload media',
      'Adjust settings and style options',
      'Click "Generate" and wait for results'
    ],
    tips: [
      'Be descriptive in your prompts',
      'Use style presets for consistent branding',
      'Higher quality settings use more credits'
    ]
  },
  'dashboard': {
    title: 'Dashboard Overview',
    description: 'Your content creation hub with quick access to all features.',
    credits: 'N/A',
    steps: [
      'View your credit balance in the header',
      'Click any feature card to start creating',
      'Check recent generations in History',
      'Manage your account in Profile'
    ],
    tips: [
      'New users get 100 free credits on signup',
      'Use the quick action buttons for faster access',
      'Enable notifications for generation updates'
    ]
  },
  'feature-requests': {
    title: 'Feature Requests',
    description: 'Submit and vote on new feature ideas.',
    credits: 'FREE',
    steps: [
      'Click "Request Feature" to submit an idea',
      'Fill in title, description, and category',
      'Vote on other users\' requests',
      'Track status updates on your submissions'
    ],
    tips: [
      'Detailed descriptions get more votes',
      'Check existing requests before submitting',
      'Popular requests are prioritized'
    ]
  },
  'billing': {
    title: 'Billing & Credits',
    description: 'Manage your subscription and purchase credits.',
    credits: 'N/A',
    steps: [
      'View your current credit balance',
      'Choose a credit pack or subscription',
      'Complete secure payment via Cashfree',
      'Credits are added instantly'
    ],
    tips: [
      'Subscriptions save up to 40% on credits',
      'Credits never expire',
      'Contact support for refund requests'
    ]
  },
  'default': {
    title: 'Help Guide',
    description: 'Get help with CreatorStudio AI features.',
    credits: 'N/A',
    steps: [
      'Navigate to the feature you need help with',
      'Click the help icon on each page',
      'Read tips and step-by-step guides',
      'Visit User Manual for detailed documentation'
    ],
    tips: [
      'Each page has contextual help available',
      'Credits are shown in the header',
      'Contact support for account issues'
    ]
  }
};

export default function HelpGuide({ pageId = 'default', activeTab = null }) {
  const [isOpen, setIsOpen] = useState(false);
  
  const content = HELP_CONTENT[pageId] || HELP_CONTENT['default'];
  const tabContent = activeTab && content.tabs ? content.tabs[activeTab] : null;

  return (
    <>
      {/* Floating Help Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-40 right-6 z-50 w-12 h-12 bg-purple-600 hover:bg-purple-500 text-white rounded-full shadow-lg shadow-purple-500/30 flex items-center justify-center transition-all hover:scale-110"
        data-testid="help-guide-btn"
        aria-label="Open help guide"
      >
        {isOpen ? (
          <X className="w-5 h-5" />
        ) : (
          <HelpCircle className="w-5 h-5" />
        )}
      </button>

      {/* Help Panel */}
      {isOpen && (
        <div 
          className="fixed bottom-56 right-6 z-50 w-80 max-h-[60vh] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-2 fade-in duration-200"
          data-testid="help-guide-panel"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-white" />
              <h3 className="font-bold text-white">{tabContent?.title || content.title}</h3>
            </div>
            <p className="text-purple-200 text-sm mt-1">
              {tabContent?.desc || content.description}
            </p>
          </div>

          {/* Content */}
          <div className="p-4 max-h-[50vh] overflow-y-auto">
            {/* Credits */}
            {(tabContent?.credits || content.credits) && (
              <div className="mb-4 bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                <p className="text-sm text-green-400 font-medium">
                  💰 Cost: {tabContent?.credits || content.credits}
                </p>
              </div>
            )}

            {/* Steps */}
            {content.steps && !tabContent && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-300 mb-2">How to Use:</h4>
                <ol className="space-y-2">
                  {content.steps.map((step, idx) => (
                    <li key={idx} className="flex gap-2 text-sm text-slate-400">
                      <span className="text-purple-400 font-bold shrink-0">{idx + 1}.</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Tab list for creator-tools */}
            {content.tabs && !tabContent && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-300 mb-2">Available Tools:</h4>
                <div className="space-y-2">
                  {Object.entries(content.tabs).map(([key, tab]) => (
                    <div key={key} className="bg-slate-800/50 rounded-lg p-2 border border-slate-700">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white font-medium">{tab.title}</span>
                        <span className="text-xs text-green-400 bg-green-500/20 px-2 py-0.5 rounded">{tab.credits}</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{tab.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tips */}
            {content.tips && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-300 mb-2">Pro Tips:</h4>
                <ul className="space-y-1">
                  {content.tips.map((tip, idx) => (
                    <li key={idx} className="flex gap-2 text-sm text-slate-400">
                      <span className="text-yellow-400 shrink-0">💡</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Full Manual Link */}
            <Link 
              to="/user-manual" 
              className="flex items-center justify-between w-full bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg p-3 transition-colors"
              data-testid="full-manual-link"
            >
              <span className="text-sm text-purple-400 font-medium">View Full Manual</span>
              <ExternalLink className="w-4 h-4 text-purple-400" />
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
