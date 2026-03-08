import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, ArrowRight, Wand2, BookOpen, Loader2, Download, 
  Check, AlertTriangle, Shield, Sparkles, Crown, Eye,
  Palette, FileText, Star, Zap, Heart, Ghost, Rocket, Search, Smile
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';
import UpsellModal from '../components/UpsellModal';
import ShareCreation from '../components/ShareCreation';
import HelpGuide from '../components/HelpGuide';
import WaitingWithGames from '../components/WaitingWithGames';
import DownloadWithExpiry from '../components/DownloadWithExpiry';

// ============================================
// COPYRIGHT BLOCKED KEYWORDS
// ============================================
const BLOCKED_KEYWORDS = [
  // Superhero / Comic IP
  'marvel', 'dc', 'avengers', 'spiderman', 'spider-man', 'batman', 'superman',
  'ironman', 'iron man', 'captain america', 'thor', 'hulk', 'joker',
  'wonder woman', 'flash', 'deadpool', 'x-men', 'wolverine', 'venom',
  // Disney / Animation
  'disney', 'pixar', 'frozen', 'elsa', 'anna', 'mickey', 'minnie',
  'donald duck', 'goofy', 'toy story', 'lightyear', 'moana', 'simba',
  // Anime / Manga
  'naruto', 'sasuke', 'dragon ball', 'goku', 'one piece', 'luffy',
  'attack on titan', 'demon slayer', 'pokemon', 'pikachu', 'studio ghibli',
  // Games / Entertainment  
  'fortnite', 'minecraft', 'league of legends', 'valorant', 'pubg',
  'call of duty', 'gta', 'harry potter', 'hogwarts', 'hermione',
  // Brands
  'nike', 'adidas', 'coca cola', 'pepsi',
  // Safety
  'celebrity', 'real person', 'politician', 'nude', 'nsfw', 'sexual',
  'violence', 'gore', 'weapon', 'hate'
];

// Check for blocked keywords
const checkBlockedContent = (text) => {
  if (!text) return { blocked: false };
  const lowerText = text.toLowerCase();
  for (const keyword of BLOCKED_KEYWORDS) {
    if (lowerText.includes(keyword)) {
      return { 
        blocked: true, 
        keyword,
        message: `Brand-based or copyrighted characters are not allowed. Detected: "${keyword}". Try using original character names!`
      };
    }
  }
  return { blocked: false };
};

// ============================================
// STORY GENRES
// ============================================
const STORY_GENRES = [
  {
    id: 'kids_adventure',
    name: 'Kids Adventure',
    icon: Smile,
    color: 'from-green-500 to-emerald-500',
    description: 'Fun adventures for young readers',
    placeholder: 'A curious bunny discovers a hidden garden full of talking flowers...'
  },
  {
    id: 'superhero',
    name: 'Superhero',
    icon: Zap,
    color: 'from-red-500 to-orange-500',
    description: 'Original heroes saving the day',
    placeholder: 'A shy teenager discovers they can control wind and must save their city...'
  },
  {
    id: 'fantasy',
    name: 'Fantasy',
    icon: Sparkles,
    color: 'from-purple-500 to-pink-500',
    description: 'Magic, dragons, and enchanted worlds',
    placeholder: 'A young wizard finds a talking book that takes them to magical realms...'
  },
  {
    id: 'comedy',
    name: 'Comedy',
    icon: Smile,
    color: 'from-yellow-500 to-amber-500',
    description: 'Laugh-out-loud funny stories',
    placeholder: 'A clumsy robot tries to become a chef but keeps making hilarious mistakes...'
  },
  {
    id: 'romance',
    name: 'Romance',
    icon: Heart,
    color: 'from-pink-500 to-rose-500',
    description: 'Sweet love stories',
    placeholder: 'Two rival bakers fall in love while competing in a cooking contest...'
  },
  {
    id: 'scifi',
    name: 'Sci-Fi',
    icon: Rocket,
    color: 'from-cyan-500 to-blue-500',
    description: 'Space, robots, and future tech',
    placeholder: 'A space explorer discovers a planet where dinosaurs evolved into scientists...'
  },
  {
    id: 'mystery',
    name: 'Mystery',
    icon: Search,
    color: 'from-slate-500 to-gray-600',
    description: 'Solve puzzles and find clues',
    placeholder: 'A clever cat detective must find who stole the golden fish from the museum...'
  },
  {
    id: 'horror_lite',
    name: 'Spooky Fun',
    icon: Ghost,
    color: 'from-violet-500 to-purple-600',
    description: 'Friendly scares, not too scary',
    placeholder: 'A friendly ghost helps lost kids find their way home on Halloween night...'
  }
];

// ============================================
// PAGE OPTIONS
// ============================================
const PAGE_OPTIONS = [
  {
    pages: 10,
    credits: 25,
    label: 'Short Comic',
    description: 'Quick story, perfect for beginners'
  },
  {
    pages: 20,
    credits: 45,
    label: 'Standard',
    description: 'Complete story arc',
    popular: true
  },
  {
    pages: 30,
    credits: 60,
    label: 'Full Story',
    description: 'Extended adventure',
    bestValue: true
  }
];

// ============================================
// ADD-ONS
// ============================================
const ADD_ONS = [
  {
    id: 'personalized_cover',
    name: 'Personalized Cover',
    description: 'Custom title and author on cover',
    credits: 4,
    icon: BookOpen
  },
  {
    id: 'dedication_page',
    name: 'Dedication Page',
    description: 'Add a personal message page',
    credits: 2,
    icon: Heart
  },
  {
    id: 'activity_pages',
    name: 'Activity Pages',
    description: 'Puzzle + Coloring pages included',
    credits: 5,
    icon: Palette
  },
  {
    id: 'hd_print',
    name: 'HD Print Version',
    description: '300 DPI print-ready PDF',
    credits: 5,
    icon: Download
  },
  {
    id: 'commercial_license',
    name: 'Commercial License',
    description: 'Sell or distribute commercially',
    credits: 15,
    icon: Crown
  }
];

// ============================================
// STORY TEMPLATES LIBRARY
// ============================================
const STORY_TEMPLATES = {
  kids_adventure: [
    {
      id: 'birthday_adventure',
      title: 'Birthday Adventure',
      emoji: '🎂',
      story: 'It\'s Max\'s birthday, and a magical balloon floats down with a treasure map! Max and their best friend go on an exciting adventure through the neighborhood to find the hidden birthday surprise.',
      suggestedTitle: 'Max\'s Birthday Adventure'
    },
    {
      id: 'first_day_school',
      title: 'First Day at School',
      emoji: '🏫',
      story: 'Luna is nervous about her first day at school, but she meets a friendly talking backpack who helps her make new friends and discover that school can be fun!',
      suggestedTitle: 'Luna\'s First Day'
    },
    {
      id: 'lost_puppy',
      title: 'The Lost Puppy',
      emoji: '🐕',
      story: 'When Sam finds a lost puppy in the park, they go on a heartwarming journey through town asking everyone for help to find the puppy\'s home.',
      suggestedTitle: 'Finding Biscuit\'s Home'
    },
    {
      id: 'treehouse_secret',
      title: 'Treehouse Secret',
      emoji: '🌳',
      story: 'Alex discovers a magical treehouse in the backyard that can transport them to different imaginary worlds. Today\'s adventure takes them to a land of friendly dinosaurs!',
      suggestedTitle: 'The Magic Treehouse'
    }
  ],
  superhero: [
    {
      id: 'power_discovery',
      title: 'Power Discovery',
      emoji: '⚡',
      story: 'On their 10th birthday, Jamie wakes up floating above their bed! Now they must learn to control their new flying ability while keeping it secret from everyone except their trusty pet hamster.',
      suggestedTitle: 'The Day I Could Fly'
    },
    {
      id: 'neighborhood_hero',
      title: 'Neighborhood Hero',
      emoji: '🦸',
      story: 'When a big storm knocks out power in the neighborhood, a young hero with the ability to glow in the dark helps guide everyone to safety.',
      suggestedTitle: 'Glow: The Light Hero'
    },
    {
      id: 'sidekick_story',
      title: 'The Sidekick Story',
      emoji: '🤝',
      story: 'Every hero needs a helper! Follow Whiskers the cat as she becomes the unexpected sidekick to the world\'s youngest superhero.',
      suggestedTitle: 'Whiskers the Sidekick'
    }
  ],
  fantasy: [
    {
      id: 'dragon_friend',
      title: 'My Dragon Friend',
      emoji: '🐉',
      story: 'When Lily finds a tiny dragon egg in her garden, she raises it in secret. But as the dragon grows, so do the adventures - and the problems of hiding a fire-breathing friend!',
      suggestedTitle: 'Lily and Spark'
    },
    {
      id: 'magic_paintbrush',
      title: 'The Magic Paintbrush',
      emoji: '🖌️',
      story: 'Everything Oliver paints comes to life! When he accidentally paints a monster, he must quickly paint a solution before his whole art room escapes into the real world.',
      suggestedTitle: 'Oliver\'s Living Art'
    },
    {
      id: 'fairy_garden',
      title: 'The Fairy Garden',
      emoji: '🧚',
      story: 'Emma discovers that the flowers in grandma\'s garden are actually homes for tiny fairies! She becomes their human protector against a pesky garden gnome.',
      suggestedTitle: 'Guardian of the Fairy Garden'
    }
  ],
  comedy: [
    {
      id: 'robot_chef',
      title: 'The Robot Chef',
      emoji: '🤖',
      story: 'Dad builds a robot to help in the kitchen, but it takes cooking instructions way too literally! Chaos ensues when it tries to make "cloud pancakes" and "rainbow soup."',
      suggestedTitle: 'Cooking with Robo-Chef'
    },
    {
      id: 'backwards_day',
      title: 'Backwards Day',
      emoji: '🔄',
      story: 'When Timmy wishes everything was backwards, he wakes up to a world where dessert is for breakfast, homework does itself, and his dog walks him!',
      suggestedTitle: 'The Totally Backwards Day'
    },
    {
      id: 'talking_vegetables',
      title: 'Talking Vegetables',
      emoji: '🥕',
      story: 'Mia refuses to eat her vegetables until they start talking back! Now the carrots, peas, and broccoli are her sassiest friends with the funniest opinions.',
      suggestedTitle: 'Mia\'s Veggie Friends'
    }
  ],
  romance: [
    {
      id: 'pen_pals',
      title: 'Pen Pals',
      emoji: '✉️',
      story: 'Two kids from different countries become pen pals. Through their letters and drawings, they share their worlds and develop a sweet friendship that spans the ocean.',
      suggestedTitle: 'Letters Across the Sea'
    },
    {
      id: 'dance_partners',
      title: 'Dance Partners',
      emoji: '💃',
      story: 'At the school talent show, two shy kids are paired up for a dance. Through practice and patience, they go from stepping on toes to best friends.',
      suggestedTitle: 'Two Left Feet'
    }
  ],
  scifi: [
    {
      id: 'space_pet',
      title: 'My Space Pet',
      emoji: '👽',
      story: 'When a tiny alien spaceship crash-lands in the backyard, Kai adopts the adorable purple creature inside. But keeping an alien pet that floats and glows is harder than it looks!',
      suggestedTitle: 'Kai and Zoob'
    },
    {
      id: 'robot_best_friend',
      title: 'Robot Best Friend',
      emoji: '🤖',
      story: 'In the future, every kid gets a robot companion on their 8th birthday. But Maya\'s robot, Bolt, is different - he wants to learn how to dream.',
      suggestedTitle: 'Bolt\'s Dream'
    },
    {
      id: 'time_machine_toy',
      title: 'The Time Machine Toy',
      emoji: '⏰',
      story: 'Jordan\'s new toy car turns out to be a real time machine! A quick trip to see dinosaurs turns into an adventure to get back home before dinner.',
      suggestedTitle: 'Race Through Time'
    }
  ],
  mystery: [
    {
      id: 'missing_cookies',
      title: 'The Missing Cookies',
      emoji: '🍪',
      story: 'Someone is stealing cookies from the cookie jar every night! Detective Daisy gathers clues, interviews suspects (including the family dog), and solves the tasty mystery.',
      suggestedTitle: 'Detective Daisy\'s First Case'
    },
    {
      id: 'secret_room',
      title: 'The Secret Room',
      emoji: '🚪',
      story: 'While playing hide and seek in grandpa\'s old house, twins discover a hidden room with mysterious objects and a map leading to a family secret.',
      suggestedTitle: 'The Hidden Room Mystery'
    },
    {
      id: 'playground_puzzle',
      title: 'Playground Puzzle',
      emoji: '🔍',
      story: 'When all the swings at the playground mysteriously disappear overnight, a group of kids must follow the clues to solve the case before recess ends forever!',
      suggestedTitle: 'The Great Swing Mystery'
    }
  ],
  horror_lite: [
    {
      id: 'friendly_monster',
      title: 'Friendly Monster',
      emoji: '👻',
      story: 'There\'s a monster under Ben\'s bed! But instead of being scary, it\'s lonely and just wants a friend. Together they have midnight adventures.',
      suggestedTitle: 'My Monster Friend'
    },
    {
      id: 'haunted_house',
      title: 'The Not-So-Haunted House',
      emoji: '🏚️',
      story: 'Everyone says the old house on the hill is haunted. When Sophie investigates, she finds it\'s actually home to the sweetest ghost family who just need help fixing their home.',
      suggestedTitle: 'The Friendly Haunted House'
    },
    {
      id: 'halloween_switch',
      title: 'Halloween Costume Mix-up',
      emoji: '🎃',
      story: 'On Halloween night, costumes in town start coming to life! Now everyone has to work together to reverse the spell before the candy deadline.',
      suggestedTitle: 'The Halloween Switcheroo'
    }
  ]
};

export default function ComicStorybookBuilder() {
  // User state
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');
  
  // Wizard state
  const [step, setStep] = useState(1);
  const maxSteps = 5;
  
  // Step 1: Genre
  const [selectedGenre, setSelectedGenre] = useState(null);
  
  // Step 2: Story idea
  const [storyIdea, setStoryIdea] = useState('');
  const [bookTitle, setBookTitle] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [contentError, setContentError] = useState(null);
  
  // Step 3: Page count
  const [selectedPages, setSelectedPages] = useState(20);
  
  // Step 4: Add-ons
  const [selectedAddOns, setSelectedAddOns] = useState({
    personalized_cover: false,
    dedication_page: false,
    activity_pages: false,
    hd_print: false,
    commercial_license: false
  });
  const [dedicationText, setDedicationText] = useState('');
  
  // Step 5: Preview & Generate
  const [previewPages, setPreviewPages] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Generation state
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [pollingInterval, setPollingIntervalState] = useState(null);
  
  // Modals
  const [showRating, setShowRating] = useState(false);
  const [showUpsell, setShowUpsell] = useState(false);

  useEffect(() => {
    fetchCredits();
    fetchUserPlan();
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, []);

  const fetchCredits = async () => {
    try {
      const res = await api.get('/api/credits/balance');
      setCredits(res.data.credits);
    } catch (e) {
      console.error('Failed to fetch credits');
    }
  };

  const fetchUserPlan = async () => {
    try {
      const res = await api.get('/api/user/profile');
      setUserPlan(res.data.user?.plan || 'free');
    } catch (e) {
      console.error('Failed to fetch user plan');
    }
  };

  // Validate content for blocked keywords
  const validateContent = (text) => {
    const check = checkBlockedContent(text);
    if (check.blocked) {
      setContentError(check);
      return false;
    }
    setContentError(null);
    return true;
  };

  // Calculate total cost
  const calculateCost = () => {
    const pageOption = PAGE_OPTIONS.find(p => p.pages === selectedPages);
    let total = pageOption?.credits || 45;
    
    // Add add-ons
    ADD_ONS.forEach(addon => {
      if (selectedAddOns[addon.id]) {
        total += addon.credits;
      }
    });
    
    // Apply plan discount
    if (userPlan === 'creator') total = Math.floor(total * 0.8);
    else if (userPlan === 'pro') total = Math.floor(total * 0.7);
    else if (userPlan === 'studio') total = Math.floor(total * 0.6);
    
    return total;
  };

  // Generate preview pages
  const generatePreview = async () => {
    if (!storyIdea.trim() || !selectedGenre) {
      toast.error('Please complete previous steps first');
      return;
    }
    
    setPreviewLoading(true);
    setPreviewPages([]);
    
    try {
      const res = await api.post('/api/comic-storybook-v2/preview', {
        genre: selectedGenre,
        storyIdea: storyIdea,
        title: bookTitle || 'My Comic Story',
        pageCount: selectedPages
      });
      
      if (res.data.previewPages) {
        setPreviewPages(res.data.previewPages);
      }
    } catch (e) {
      toast.error('Failed to generate preview');
      // Use placeholder previews
      setPreviewPages([
        { url: 'https://placehold.co/400x600/6b21a8/white?text=Cover+Preview', type: 'cover' },
        { url: 'https://placehold.co/400x600/7c3aed/white?text=Page+1+Preview', type: 'page' }
      ]);
    }
    
    setPreviewLoading(false);
  };

  // Poll job status
  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const res = await api.get(`/api/comic-storybook-v2/job/${jobId}`);
      setJob(res.data);
      
      if (res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
        if (pollingInterval) clearInterval(pollingInterval);
        setPollingIntervalState(null);
        setLoading(false);
        fetchCredits();
        
        if (res.data.status === 'COMPLETED') {
          toast.success('Your comic book is ready!');
          setTimeout(() => setShowRating(true), 2000);
        } else {
          toast.error('Generation failed. Please try again.');
        }
      }
    } catch (e) {
      console.error('Poll error:', e);
    }
  }, [pollingInterval]);

  // Generate full comic book
  const generateComicBook = async () => {
    if (!storyIdea.trim() || !selectedGenre) {
      toast.error('Please complete all steps first');
      return;
    }
    
    // Final validation
    if (!validateContent(storyIdea) || !validateContent(bookTitle)) {
      toast.error('Please remove copyrighted references');
      return;
    }
    
    const cost = calculateCost();
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      setShowUpsell(true);
      return;
    }
    
    setLoading(true);
    setJob(null);
    
    try {
      const res = await api.post('/api/comic-storybook-v2/generate', {
        genre: selectedGenre,
        storyIdea: storyIdea,
        title: bookTitle || 'My Comic Story',
        author: authorName || 'Anonymous',
        pageCount: selectedPages,
        addOns: selectedAddOns,
        dedicationText: selectedAddOns.dedication_page ? dedicationText : null
      });
      
      setJob({ id: res.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Comic book generation started!');
      
      const interval = setInterval(() => pollJobStatus(res.data.jobId), 3000);
      setPollingIntervalState(interval);
      
    } catch (e) {
      setLoading(false);
      const errorMsg = e.response?.data?.detail || 'Generation failed';
      toast.error(errorMsg);
    }
  };

  // Download handler
  const handleDownload = async (type = 'pdf') => {
    if (!job?.id) return;
    
    // Check if user is free and trying to download
    if (userPlan === 'free' && !job.purchased) {
      setShowUpsell(true);
      return;
    }
    
    try {
      const res = await api.post(`/api/comic-storybook-v2/download/${job.id}`, { type });
      if (res.data.success) {
        toast.success('Download started!');
        
        const url = res.data.downloadUrl;
        const fullUrl = url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`;
        const link = document.createElement('a');
        link.href = fullUrl;
        link.download = `comic_${job.id.slice(0, 8)}.${type}`;
        link.click();
        
        fetchCredits();
      }
    } catch (e) {
      toast.error('Download failed');
    }
  };

  // Navigation
  const nextStep = () => {
    if (step === 2 && contentError?.blocked) {
      toast.error('Please fix content issues before proceeding');
      return;
    }
    if (step < maxSteps) setStep(step + 1);
    if (step === 4) generatePreview(); // Auto-generate preview when entering step 5
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  // Reset wizard
  const resetWizard = () => {
    setStep(1);
    setSelectedGenre(null);
    setStoryIdea('');
    setBookTitle('');
    setAuthorName('');
    setSelectedPages(20);
    setSelectedAddOns({
      personalized_cover: false,
      dedication_page: false,
      activity_pages: false,
      hd_print: false,
      commercial_license: false
    });
    setJob(null);
    setPreviewPages([]);
    setContentError(null);
  };

  // Can proceed to next step?
  const canProceed = () => {
    switch (step) {
      case 1: return selectedGenre !== null;
      case 2: return storyIdea.trim().length >= 10 && !contentError?.blocked;
      case 3: return selectedPages > 0;
      case 4: return true;
      case 5: return true;
      default: return false;
    }
  };

  // ============================================
  // RENDER STEP 1: Choose Genre
  // ============================================
  const renderStep1 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 1 of 5</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Choose Your Story Type</h3>
        <p className="text-slate-400">What kind of comic book do you want to create?</p>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STORY_GENRES.map((genre) => {
          const Icon = genre.icon;
          return (
            <div
              key={genre.id}
              onClick={() => setSelectedGenre(genre.id)}
              className={`relative p-5 rounded-2xl border-2 cursor-pointer transition-all hover:scale-[1.02] ${
                selectedGenre === genre.id
                  ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
              }`}
              data-testid={`genre-${genre.id}`}
            >
              {selectedGenre === genre.id && (
                <div className="absolute top-2 right-2">
                  <Check className="w-5 h-5 text-purple-400" />
                </div>
              )}
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${genre.color} flex items-center justify-center mb-3`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <h4 className="font-bold text-white mb-1">{genre.name}</h4>
              <p className="text-xs text-slate-400">{genre.description}</p>
            </div>
          );
        })}
      </div>
      
      <div className="flex justify-center mt-8">
        <Button 
          onClick={nextStep}
          disabled={!canProceed()}
          className="px-8 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          data-testid="next-step-btn"
        >
          Continue <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // ============================================
  // RENDER STEP 2: Story Idea with Template Library
  // ============================================
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showTemplates, setShowTemplates] = useState(true);
  
  const applyTemplate = (template) => {
    setSelectedTemplate(template.id);
    setStoryIdea(template.story);
    setBookTitle(template.suggestedTitle);
    setShowTemplates(false);
    toast.success('Template applied! Feel free to customize it.');
  };
  
  const renderStep2 = () => {
    const genre = STORY_GENRES.find(g => g.id === selectedGenre);
    const templates = STORY_TEMPLATES[selectedGenre] || [];
    
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
            <span className="text-purple-400 font-medium">Step 2 of 5</span>
          </div>
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Describe Your Story</h3>
          <p className="text-slate-400">Choose a template or write your own story idea</p>
        </div>
        
        {/* Template Library Toggle */}
        <div className="flex justify-center mb-6">
          <div className="bg-slate-800/50 rounded-full p-1 flex gap-1">
            <button
              onClick={() => setShowTemplates(true)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                showTemplates ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              📚 Template Library
            </button>
            <button
              onClick={() => setShowTemplates(false)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                !showTemplates ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              ✏️ Write My Own
            </button>
          </div>
        </div>
        
        {showTemplates && templates.length > 0 ? (
          /* Template Library Grid */
          <div className="mb-8">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-400" />
              {genre?.name} Story Templates
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              {templates.map((template) => (
                <div
                  key={template.id}
                  onClick={() => applyTemplate(template)}
                  className={`p-5 rounded-xl border-2 cursor-pointer transition-all hover:scale-[1.02] ${
                    selectedTemplate === template.id
                      ? 'border-purple-500 bg-purple-500/20'
                      : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                  }`}
                  data-testid={`template-${template.id}`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-3xl">{template.emoji}</span>
                    <div className="flex-1">
                      <h5 className="font-bold text-white mb-1">{template.title}</h5>
                      <p className="text-sm text-slate-400 line-clamp-3">{template.story}</p>
                      <p className="text-xs text-purple-400 mt-2">Suggested title: {template.suggestedTitle}</p>
                    </div>
                    {selectedTemplate === template.id && (
                      <Check className="w-5 h-5 text-purple-400 flex-shrink-0" />
                    )}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-center text-sm text-slate-500 mt-4">
              Click a template to use it, then customize as you like!
            </p>
          </div>
        ) : (
          /* Write Your Own Form */
          <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6 space-y-6">
            {/* Story Idea */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Your Story Idea *
              </label>
              <Textarea
                placeholder={genre?.placeholder || 'Describe your story idea...'}
                value={storyIdea}
                onChange={(e) => {
                  setStoryIdea(e.target.value);
                  setSelectedTemplate(null);
                  validateContent(e.target.value);
                }}
                className="bg-slate-700 border-slate-600 text-white min-h-32 text-lg"
                data-testid="story-idea-input"
              />
              <p className="text-xs text-slate-500 mt-2">
                Example: "{genre?.placeholder}"
              </p>
              
              {contentError && (
                <div className="mt-3 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-red-400 text-sm font-medium">Content issue detected</p>
                    <p className="text-red-300/80 text-xs mt-1">{contentError.message}</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Book Title */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Book Title (Optional)
              </label>
              <Input
                placeholder="My Amazing Adventure"
                value={bookTitle}
                onChange={(e) => {
                  setBookTitle(e.target.value);
                  validateContent(e.target.value);
                }}
                className="bg-slate-700 border-slate-600 text-white"
                data-testid="book-title-input"
              />
            </div>
            
            {/* Author Name */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Author Name (Optional)
              </label>
              <Input
                placeholder="Your name"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                className="bg-slate-700 border-slate-600 text-white"
              />
            </div>
          </div>
        )}
        
        {/* Summary of selection */}
        {storyIdea && (
          <div className="mt-6 bg-slate-800/30 rounded-xl border border-slate-700 p-4">
            <h5 className="text-sm font-medium text-slate-400 mb-2">Your Story:</h5>
            <p className="text-white">{storyIdea.slice(0, 200)}{storyIdea.length > 200 ? '...' : ''}</p>
            {bookTitle && <p className="text-purple-400 text-sm mt-2">Title: {bookTitle}</p>}
          </div>
        )}
        
        <div className="flex justify-between mt-8">
          <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          <Button 
            onClick={nextStep}
            disabled={!canProceed()}
            className="px-8 bg-gradient-to-r from-purple-600 to-pink-600"
          >
            Continue <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    );
  };

  // ============================================
  // RENDER STEP 3: Choose Length
  // ============================================
  const renderStep3 = () => (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 3 of 5</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Choose Book Length</h3>
        <p className="text-slate-400">How long should your comic book be?</p>
      </div>
      
      <div className="grid md:grid-cols-3 gap-6">
        {PAGE_OPTIONS.map((option) => (
          <div
            key={option.pages}
            onClick={() => setSelectedPages(option.pages)}
            className={`relative p-6 rounded-2xl border-2 cursor-pointer transition-all hover:scale-[1.02] ${
              selectedPages === option.pages
                ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
                : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
            }`}
            data-testid={`pages-${option.pages}`}
          >
            {option.popular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-orange-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                MOST POPULAR
              </span>
            )}
            {option.bestValue && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                BEST VALUE
              </span>
            )}
            
            <div className="text-center">
              <div className="text-5xl font-bold text-white mb-2">{option.pages}</div>
              <div className="text-lg text-slate-400 mb-1">Pages</div>
              <div className="font-semibold text-slate-300 mb-3">{option.label}</div>
              <p className="text-sm text-slate-500 mb-4">{option.description}</p>
              <div className="text-2xl font-bold text-purple-400">{option.credits} credits</div>
            </div>
            
            {selectedPages === option.pages && (
              <div className="absolute top-3 right-3">
                <Check className="w-6 h-6 text-purple-400" />
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep}
          disabled={!canProceed()}
          className="px-8 bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Continue <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // ============================================
  // RENDER STEP 4: Add-ons
  // ============================================
  const renderStep4 = () => (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 4 of 5</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Customize Your Book</h3>
        <p className="text-slate-400">Add optional extras to make your book special</p>
      </div>
      
      <div className="space-y-4">
        {ADD_ONS.map((addon) => {
          const Icon = addon.icon;
          const isSelected = selectedAddOns[addon.id];
          
          return (
            <div key={addon.id}>
              <div
                onClick={() => setSelectedAddOns({...selectedAddOns, [addon.id]: !isSelected})}
                className={`flex items-center justify-between p-5 rounded-xl border-2 cursor-pointer transition-all ${
                  isSelected
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                }`}
                data-testid={`addon-${addon.id}`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    isSelected ? 'bg-purple-500/30' : 'bg-slate-700'
                  }`}>
                    <Icon className={`w-6 h-6 ${isSelected ? 'text-purple-400' : 'text-slate-400'}`} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white">{addon.name}</h4>
                    <p className="text-sm text-slate-400">{addon.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-lg font-bold text-purple-400">+{addon.credits} credits</span>
                  <div className={`w-6 h-6 rounded-md border-2 flex items-center justify-center ${
                    isSelected ? 'bg-purple-500 border-purple-500' : 'border-slate-600'
                  }`}>
                    {isSelected && <Check className="w-4 h-4 text-white" />}
                  </div>
                </div>
              </div>
              
              {/* Dedication text input */}
              {addon.id === 'dedication_page' && isSelected && (
                <div className="mt-3 ml-16">
                  <Input
                    placeholder="Write your dedication message..."
                    value={dedicationText}
                    onChange={(e) => setDedicationText(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Cost Summary */}
      <div className="mt-8 bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        <div className="flex justify-between items-center">
          <div>
            <p className="text-slate-400 text-sm">Total Cost</p>
            <p className="text-3xl font-bold text-white">{calculateCost()} credits</p>
          </div>
          <div className="text-right">
            <p className="text-slate-400 text-sm">Your Balance</p>
            <p className={`text-xl font-bold ${credits >= calculateCost() ? 'text-green-400' : 'text-red-400'}`}>
              {credits.toLocaleString()} credits
            </p>
          </div>
        </div>
        {userPlan !== 'free' && (
          <p className="text-xs text-green-400 mt-2">
            {userPlan === 'creator' ? '20%' : userPlan === 'pro' ? '30%' : '40%'} subscriber discount applied!
          </p>
        )}
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep}
          className="px-8 bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Preview & Generate <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // ============================================
  // RENDER STEP 5: Preview & Generate
  // ============================================
  const renderStep5 = () => {
    const genre = STORY_GENRES.find(g => g.id === selectedGenre);
    const pageOption = PAGE_OPTIONS.find(p => p.pages === selectedPages);
    
    return (
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
            <span className="text-purple-400 font-medium">Step 5 of 5</span>
          </div>
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Preview & Generate</h3>
          <p className="text-slate-400">Review your comic book and start generation</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          {/* Summary */}
          <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6">
            <h4 className="font-bold text-white text-lg mb-4">Book Summary</h4>
            
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-slate-400">Genre:</span>
                <span className="text-white font-medium">{genre?.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Title:</span>
                <span className="text-white font-medium">{bookTitle || 'My Comic Story'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Author:</span>
                <span className="text-white font-medium">{authorName || 'Anonymous'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Pages:</span>
                <span className="text-white font-medium">{selectedPages} pages</span>
              </div>
              
              {/* Story Preview */}
              <div className="pt-4 border-t border-slate-700">
                <p className="text-slate-400 text-sm mb-2">Story Idea:</p>
                <p className="text-white text-sm bg-slate-700/50 p-3 rounded-lg">
                  {storyIdea.slice(0, 150)}...
                </p>
              </div>
              
              {/* Add-ons */}
              {Object.entries(selectedAddOns).some(([_, v]) => v) && (
                <div className="pt-4 border-t border-slate-700">
                  <p className="text-slate-400 text-sm mb-2">Add-ons:</p>
                  <div className="flex flex-wrap gap-2">
                    {ADD_ONS.filter(a => selectedAddOns[a.id]).map(addon => (
                      <span key={addon.id} className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-full">
                        {addon.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {/* Final Cost */}
            <div className="mt-6 pt-4 border-t border-slate-700">
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold text-white">Total:</span>
                <span className="text-2xl font-bold text-purple-400">{calculateCost()} credits</span>
              </div>
            </div>
            
            <Button 
              onClick={generateComicBook}
              disabled={loading || credits < calculateCost()}
              className="w-full mt-6 py-6 text-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              data-testid="generate-btn"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Generating Your Comic Book...</>
              ) : (
                <><Wand2 className="w-5 h-5 mr-2" /> Generate Full Comic Book</>
              )}
            </Button>
          </div>
          
          {/* Preview / Result */}
          <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6">
            <h4 className="font-bold text-white text-lg mb-4">
              {job ? 'Generation Progress' : 'Preview'}
            </h4>
            
            {job ? (
              <div className="space-y-4">
                {/* Show WaitingWithGames during processing */}
                {(job.status === 'PROCESSING' || job.status === 'QUEUED') ? (
                  <WaitingWithGames 
                    progress={job.progress || 0}
                    status={job.progressMessage || (job.status === 'QUEUED' ? 'In queue...' : 'Creating your comic book...')}
                    estimatedTime="2-5 minutes"
                    onCancel={() => {
                      // Could add cancel logic here
                      toast.info('Generation in progress - please wait');
                    }}
                    currentFeature="/app/comic-storybook"
                    showExploreFeatures={true}
                  />
                ) : (
                  <>
                    {/* Status Badge */}
                    <div className="flex items-center justify-between">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                        job.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {job.status}
                      </span>
                    </div>
                  </>
                )}
                
                {/* Download Buttons */}
                {job.status === 'COMPLETED' && (
                  <div className="space-y-3 mt-6">
                    {/* Smart Download with Watermark Support */}
                    {job.resultUrl && (
                      <DownloadWithExpiry
                        downloadUrl={job.resultUrl.startsWith('http') ? job.resultUrl : `${process.env.REACT_APP_BACKEND_URL}${job.resultUrl}`}
                        downloadId={job.downloadId}
                        filename={`comic_storybook_${job.id}.pdf`}
                        fileType="document"
                        expiresAt={job.expiresAt}
                        contentType="STORYBOOK"
                        enableSmartDownload={true}
                        showWarning={true}
                        onExpired={() => {
                          toast.warning('Your download has expired. Please generate again.');
                        }}
                      />
                    )}
                    
                    {/* Print Version (if HD print add-on selected) */}
                    {selectedAddOns.hd_print && (
                      <Button 
                        onClick={() => handleDownload('print')}
                        variant="outline"
                        className="w-full border-slate-600 text-slate-300"
                      >
                        <Download className="w-4 h-4 mr-2" /> Download Print Version
                      </Button>
                    )}
                    
                    <ShareCreation 
                      contentType="comic_storybook"
                      contentId={job.id}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {previewLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
                  </div>
                ) : previewPages.length > 0 ? (
                  <div className="grid grid-cols-2 gap-4">
                    {previewPages.map((page, idx) => (
                      <div key={idx} className="relative rounded-lg overflow-hidden border border-slate-600 bg-slate-800">
                        <img 
                          src={page.url} 
                          alt={`Preview ${idx + 1}`}
                          className="w-full aspect-[3/4] object-cover"
                          onError={(e) => {
                            // Fallback to gradient placeholder on error
                            e.target.style.display = 'none';
                            e.target.parentElement.querySelector('.fallback-placeholder').style.display = 'flex';
                          }}
                        />
                        <div className="fallback-placeholder hidden w-full aspect-[3/4] items-center justify-center bg-gradient-to-br from-purple-900 to-indigo-900">
                          <div className="text-center">
                            <BookOpen className="w-12 h-12 mx-auto text-purple-400 mb-2" />
                            <span className="text-purple-300 text-sm">{page.type === 'cover' ? 'Cover Preview' : `Page ${idx}`}</span>
                          </div>
                        </div>
                        <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                          <span className="text-white text-xs font-medium">
                            {page.type === 'cover' ? 'Cover' : `Page ${idx}`}
                          </span>
                        </div>
                        <div className="absolute inset-0 flex items-center justify-center bg-black/30 pointer-events-none">
                          <span className="text-white text-xs bg-black/50 px-2 py-1 rounded">PREVIEW</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <BookOpen className="w-16 h-16 mx-auto text-slate-600 mb-4" />
                    <p className="text-slate-400">Preview will appear here</p>
                    <Button 
                      onClick={generatePreview}
                      variant="outline"
                      className="mt-4 border-slate-600 text-slate-300"
                    >
                      <Eye className="w-4 h-4 mr-2" /> Generate Preview
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        <div className="flex justify-between mt-8">
          <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600" disabled={loading}>
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          {job?.status === 'COMPLETED' && (
            <Button onClick={resetWizard} variant="outline" className="text-slate-300 border-slate-600">
              Create Another Book
            </Button>
          )}
        </div>
      </div>
    );
  };

  // ============================================
  // MAIN RENDER
  // ============================================
  const renderCurrentStep = () => {
    switch (step) {
      case 1: return renderStep1();
      case 2: return renderStep2();
      case 3: return renderStep3();
      case 4: return renderStep4();
      case 5: return renderStep5();
      default: return renderStep1();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                <span>Dashboard</span>
              </Link>
              <div className="flex items-center gap-2">
                <BookOpen className="w-6 h-6 text-purple-400" />
                <h1 className="text-xl md:text-2xl font-bold text-white">Comic Story Book Builder</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-full px-4 py-2">
                <span className="text-purple-300 font-medium">{credits.toLocaleString()} Credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Progress Indicator */}
        <div className="max-w-xl mx-auto mb-8">
          <div className="flex items-center justify-between">
            {Array.from({ length: maxSteps }).map((_, i) => (
              <React.Fragment key={i}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                  i + 1 < step ? 'bg-green-500 text-white' :
                  i + 1 === step ? 'bg-purple-600 text-white scale-110' :
                  'bg-slate-700 text-slate-400'
                }`}>
                  {i + 1 < step ? <Check className="w-5 h-5" /> : i + 1}
                </div>
                {i < maxSteps - 1 && (
                  <div className={`flex-1 h-1 mx-2 rounded ${
                    i + 1 < step ? 'bg-green-500' : 'bg-slate-700'
                  }`} />
                )}
              </React.Fragment>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-slate-500">
            <span>Genre</span>
            <span>Story</span>
            <span>Length</span>
            <span>Add-ons</span>
            <span>Generate</span>
          </div>
        </div>

        {renderCurrentStep()}
        
        {/* Legal Disclaimer */}
        <div className="mt-12 bg-slate-800/30 rounded-xl p-4 border border-slate-700 max-w-4xl mx-auto">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-slate-300 font-medium mb-1">Content Policy</p>
              <p className="text-xs text-slate-400">
                Upload or write only original stories. Do not include copyrighted characters or brand references. 
                All generated content must be original.
              </p>
            </div>
          </div>
        </div>
      </main>
      
      {/* Modals */}
      <RatingModal 
        isOpen={showRating}
        onClose={() => setShowRating(false)}
        featureKey="comic_storybook"
        relatedRequestId={job?.id}
        onSubmitSuccess={() => setShowRating(false)}
      />
      
      <UpsellModal
        isOpen={showUpsell}
        onClose={() => setShowUpsell(false)}
        feature="comic_storybook"
        generationId={job?.id}
        onSuccess={() => {
          fetchCredits();
          setShowUpsell(false);
        }}
      />
      
      {/* Help Guide */}
      <HelpGuide pageId="comic-storybook" />
    </div>
  );
}
