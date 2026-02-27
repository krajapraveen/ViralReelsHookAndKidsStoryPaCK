import React, { useState } from 'react';
import { HelpCircle, X, ChevronRight, ExternalLink, Sparkles, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAppTour } from './AppTour';
import { toast } from 'sonner';

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
  'analytics': {
    title: 'Analytics Dashboard',
    description: 'Track your content performance and usage statistics.',
    credits: 'FREE',
    steps: [
      'View your generation history',
      'Track credits usage over time',
      'Analyze content performance',
      'Export reports as needed'
    ],
    tips: [
      'Check weekly trends for insights',
      'Monitor credit usage to plan ahead',
      'Use data to optimize content strategy'
    ]
  },
  'admin': {
    title: 'Admin Dashboard',
    description: 'Manage users, content, and system settings.',
    credits: 'Admin Only',
    steps: [
      'View user statistics and activity',
      'Manage user accounts and credits',
      'Monitor system health',
      'Configure platform settings'
    ],
    tips: [
      'Check daily active users regularly',
      'Monitor for unusual activity',
      'Keep system notifications enabled'
    ]
  },
  'admin-monitoring': {
    title: 'System Monitoring',
    description: 'Real-time monitoring of system health and user activity.',
    credits: 'Admin Only',
    steps: [
      'View real-time activity stream',
      'Monitor API response times',
      'Check error rates and alerts',
      'Track resource utilization'
    ],
    tips: [
      'Set up alerts for critical metrics',
      'Review logs during peak hours',
      'Archive data regularly'
    ]
  },
  'comix-ai': {
    title: 'Comix AI - Photo to Comic',
    description: 'Transform photos into comic-style characters and panels.',
    credits: '5-10 credits per generation',
    steps: [
      'Choose mode: Character, Panel, or Story',
      'Upload a photo or enter a prompt',
      'Select comic style (Manga, American, European)',
      'Add negative prompts to refine output',
      'Click Generate and wait for results',
      'Download your comic creation'
    ],
    tips: [
      'Use clear, well-lit photos for best character results',
      'Negative prompts help exclude unwanted elements',
      'Combine Character + Panel modes for full comics'
    ]
  },
  'gif-maker': {
    title: 'GIF Maker',
    description: 'Create animated GIFs from AI-generated content.',
    credits: '8-15 credits per GIF',
    steps: [
      'Choose GIF type: Text, Reaction, or Meme',
      'Enter a description or upload an image',
      'Configure frame count and animation speed',
      'Click Generate GIF',
      'Preview and download your animation'
    ],
    tips: [
      'More frames = smoother but costs more',
      'Reaction GIFs are great for social media',
      'Simple prompts create clearer animations'
    ]
  },
  'comic-storybook': {
    title: 'Comic Story Book',
    description: 'Create 20-page illustrated comic story books.',
    credits: '25-40 credits per book',
    steps: [
      'Enter story title and main character',
      'Select theme, genre, and age group',
      'Choose comic style and page count',
      'Add custom character descriptions',
      'Click Generate Story Book',
      'Wait 2-5 minutes for generation',
      'Download as PDF or images'
    ],
    tips: [
      'Detailed character descriptions improve consistency',
      'Shorter books (10 pages) generate faster',
      'Include a moral for educational value'
    ]
  },
  'photo-to-comic': {
    title: 'Photo to Comic',
    description: 'Transform your photos into comic-style characters with multiple styles.',
    credits: '15-45 credits per generation',
    steps: [
      'Choose mode: Comic Avatar or Comic Strip',
      'Upload your photo (PNG, JPG, WEBP)',
      'Select a comic style from 24 safe styles',
      'Add optional custom details',
      'Choose add-ons (transparent BG, multiple poses, HD)',
      'Click Generate and wait for results'
    ],
    tips: [
      'Use clear, front-facing photos for best results',
      'Multiple poses option gives you 3 variations',
      'HD export is recommended for printing'
    ]
  },
  'brand-story-builder': {
    title: 'Brand Story Builder',
    description: 'Create compelling brand stories for your business.',
    credits: '5 credits per story',
    steps: [
      'Enter your brand/business name',
      'Describe your industry and target audience',
      'Select your brand values and tone',
      'Click Generate Brand Story',
      'Copy and use in your marketing materials'
    ],
    tips: [
      'Be specific about your unique selling points',
      'Include your mission and vision for better stories',
      'Use generated stories for About Us pages and pitches'
    ]
  },
  'story-hook-generator': {
    title: 'Story Hook Generator',
    description: 'Generate attention-grabbing hooks for your stories and content.',
    credits: '3 credits per hook set',
    steps: [
      'Select your content type (video, blog, social)',
      'Enter your topic or theme',
      'Choose hook style (question, statistic, story)',
      'Click Generate Hooks',
      'Copy your favorite hooks to use'
    ],
    tips: [
      'Questions hooks drive curiosity and engagement',
      'Use shocking facts or statistics for authority',
      'Test different hooks to see what resonates'
    ]
  },
  'offer-generator': {
    title: 'Offer Generator',
    description: 'Create irresistible offers and promotions for your products.',
    credits: '3 credits per offer',
    steps: [
      'Enter your product or service name',
      'Set your regular and sale prices',
      'Choose offer type (discount, bundle, limited)',
      'Click Generate Offer',
      'Copy offer text for your marketing'
    ],
    tips: [
      'Urgency and scarcity increase conversions',
      'Bundle offers increase average order value',
      'Always highlight the value, not just the discount'
    ]
  },
  'daily-viral-ideas': {
    title: 'Daily Viral Ideas',
    description: 'Get fresh viral content ideas delivered daily.',
    credits: '1 credit per idea (Pro: unlimited)',
    steps: [
      'Select your niche category',
      'Click Get Todays Idea',
      'View the viral idea with hooks and tips',
      'Save ideas you like for later',
      'Implement within 24 hours for best results'
    ],
    tips: [
      'Check daily for fresh trending topics',
      'Combine ideas with your unique perspective',
      'Pro plan gives unlimited daily ideas'
    ]
  },
  'youtube-thumbnail': {
    title: 'YouTube Thumbnail Text',
    description: 'Generate eye-catching text for YouTube thumbnails.',
    credits: 'FREE',
    steps: [
      'Enter your video topic or title',
      'Select emotion/vibe (shock, curiosity, excitement)',
      'Click Generate Text',
      'Choose from multiple suggestions',
      'Use in your thumbnail design tool'
    ],
    tips: [
      'Short text (2-4 words) works best on thumbnails',
      'Use contrast colors for text visibility',
      'Emotional words drive higher CTR'
    ]
  },
  'coloring-book': {
    title: 'Coloring Book Generator',
    description: 'Create printable coloring book pages with AI.',
    credits: '5-15 credits per page',
    steps: [
      'Choose theme (animals, fantasy, nature)',
      'Set complexity level (simple to detailed)',
      'Enter custom prompt for specific designs',
      'Click Generate Page',
      'Download as PDF for printing'
    ],
    tips: [
      'Simple designs work best for young children',
      'Detailed pages are great for adult coloring books',
      'Use high quality print settings'
    ]
  },
  'challenge-generator': {
    title: 'Challenge Generator',
    description: 'Create viral challenge ideas for social media.',
    credits: '5 credits per challenge',
    steps: [
      'Select platform (TikTok, Instagram, YouTube)',
      'Choose challenge category',
      'Set difficulty and duration',
      'Click Generate Challenge',
      'Get complete challenge brief with hashtags'
    ],
    tips: [
      'Simple challenges get more participation',
      'Include clear rules and examples',
      'Create a unique hashtag for tracking'
    ]
  },
  'caption-rewriter': {
    title: 'Caption Rewriter Pro',
    description: 'Rewrite and improve your social media captions.',
    credits: '2 credits per rewrite',
    steps: [
      'Paste your original caption',
      'Select target tone and platform',
      'Choose length preference',
      'Click Rewrite Caption',
      'Compare versions and pick the best'
    ],
    tips: [
      'Include your key message in the first line',
      'Use emojis strategically, not excessively',
      'End with a clear call-to-action'
    ]
  },
  'tone-switcher': {
    title: 'Tone Switcher',
    description: 'Convert content between different tones and styles.',
    credits: '2 credits per conversion',
    steps: [
      'Paste your content',
      'Select source and target tones',
      'Click Convert Tone',
      'Review and refine the output',
      'Copy the converted text'
    ],
    tips: [
      'Works great for repurposing content',
      'Convert formal to casual for social media',
      'Use professional tone for business contexts'
    ]
  },
  'profile': {
    title: 'Profile Settings',
    description: 'Manage your account settings and preferences.',
    credits: 'N/A',
    steps: [
      'Update your display name and avatar',
      'Change email or password',
      'View your subscription status',
      'Manage notification preferences',
      'Download your data or delete account'
    ],
    tips: [
      'Keep your email updated for important notifications',
      'Enable 2FA for enhanced security',
      'Check subscription status before renewal'
    ]
  },
  'history': {
    title: 'Generation History',
    description: 'View and manage all your past generations.',
    credits: 'N/A',
    steps: [
      'Browse your generation history',
      'Filter by type, date, or status',
      'Click any item to view details',
      'Re-download or share completed items',
      'Delete unwanted generations'
    ],
    tips: [
      'Starred items appear at the top',
      'Use filters to find specific generations',
      'Export history for your records'
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
  const { restartTour } = useAppTour();
  
  const content = HELP_CONTENT[pageId] || HELP_CONTENT['default'];
  const tabContent = activeTab && content.tabs ? content.tabs[activeTab] : null;

  const handleStartTour = () => {
    setIsOpen(false);
    restartTour();
    toast.success('Quick Tour started! Follow along to learn the features.');
  };

  return (
    <>
      {/* Floating Help Button - Made more prominent */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-40 right-6 z-50 w-14 h-14 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-full shadow-lg shadow-purple-500/40 flex items-center justify-center transition-all hover:scale-110 animate-pulse"
        data-testid="help-guide-btn"
        aria-label="Open help guide"
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <HelpCircle className="w-6 h-6" />
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

            {/* Quick Tour Button - Prominent at top */}
            <button
              onClick={handleStartTour}
              className="w-full mb-4 flex items-center justify-center gap-2 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-400 hover:to-emerald-400 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-lg shadow-green-500/30 hover:scale-[1.02]"
              data-testid="quick-tour-btn"
            >
              <Play className="w-5 h-5" />
              <span>Start Quick Tour</span>
            </button>

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
