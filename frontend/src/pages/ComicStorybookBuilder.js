import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, ArrowRight, Wand2, BookOpen, Loader2, Download, 
  Check, CheckCircle, AlertTriangle, Shield, Sparkles, Crown, Eye,
  Palette, FileText, Star, Zap, Heart, Ghost, Rocket, Search, Smile,
  Globe, Users, BookMarked, Image, Package, Printer, FileArchive,
  Lightbulb, Save, RotateCcw, Layers, Clock,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';
import UpsellModal from '../components/UpsellModal';
import { SafeImage } from '../components/SafeImage';
import ShareCreation from '../components/ShareCreation';
import HelpGuide from '../components/HelpGuide';
import WaitingWithGames from '../components/WaitingWithGames';
import DownloadWithExpiry from '../components/DownloadWithExpiry';
import NextActionHooks from '../components/NextActionHooks';
import RemixBanner from '../components/RemixBanner';
import { useRemixData, mapRemixToFields } from '../hooks/useRemixData';

// ============================================
// COPYRIGHT BLOCKED KEYWORDS
// ============================================
const BLOCKED_KEYWORDS = [
  // Superhero / Comic IP
  'marvel', 'dc', 'avengers', 'spiderman', 'spider-man', 'batman', 'superman',
  'ironman', 'iron man', 'captain america', 'thor', 'hulk', 'joker',
  'wonder woman', 'flash', 'deadpool', 'x-men', 'wolverine', 'venom',
  // Disney / Animation (blocked characters)
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
const QUICK_PRESETS = [
  { id: 'kids_adventure_preset', label: 'Kids Adventure', genre: 'kids_adventure', language: 'English', ageGroup: '4-7', readingLevel: 'beginner', icon: Smile, color: 'emerald' },
  { id: 'bedtime_story', label: 'Bedtime Story', genre: 'kids_adventure', language: 'English', ageGroup: '3-6', readingLevel: 'beginner', icon: Star, color: 'indigo' },
  { id: 'superhero_origin', label: 'Superhero Origin', genre: 'superhero', language: 'English', ageGroup: '6-10', readingLevel: 'intermediate', icon: Zap, color: 'rose' },
  { id: 'fantasy_quest', label: 'Fantasy Quest', genre: 'fantasy', language: 'English', ageGroup: '8-12', readingLevel: 'intermediate', icon: Sparkles, color: 'violet' },
  { id: 'school_story', label: 'School Story', genre: 'comedy', language: 'English', ageGroup: '6-10', readingLevel: 'intermediate', icon: BookOpen, color: 'amber' },
  { id: 'animal_friendship', label: 'Animal Friendship', genre: 'kids_adventure', language: 'English', ageGroup: '3-6', readingLevel: 'beginner', icon: Heart, color: 'pink' },
  { id: 'mystery_puzzle', label: 'Mystery Puzzle', genre: 'mystery', language: 'English', ageGroup: '8-12', readingLevel: 'advanced', icon: Search, color: 'slate' },
  { id: 'funny_comic', label: 'Funny Comic', genre: 'comedy', language: 'English', ageGroup: '6-10', readingLevel: 'intermediate', icon: Smile, color: 'yellow' },
  { id: 'educational_comic', label: 'Educational Comic', genre: 'scifi', language: 'English', ageGroup: '8-12', readingLevel: 'advanced', icon: Lightbulb, color: 'cyan' },
  { id: 'bilingual_kids', label: 'Bilingual Kids', genre: 'kids_adventure', language: 'English', ageGroup: '4-7', readingLevel: 'beginner', icon: Globe, color: 'teal', bilingual: true },
];

const LANGUAGES = ['English', 'Hindi', 'Telugu', 'Spanish', 'French', 'Arabic', 'German', 'Portuguese', 'Japanese', 'Korean', 'Chinese', 'Italian'];
const AGE_GROUPS = [
  { value: '3-6', label: '3-6 years', desc: 'Pre-school' },
  { value: '4-7', label: '4-7 years', desc: 'Early readers' },
  { value: '6-10', label: '6-10 years', desc: 'Kids' },
  { value: '8-12', label: '8-12 years', desc: 'Tweens' },
  { value: '12+', label: '12+ years', desc: 'Young adults' },
];
const READING_LEVELS = [
  { value: 'beginner', label: 'Beginner', desc: 'Simple words, short sentences' },
  { value: 'intermediate', label: 'Intermediate', desc: 'Full sentences, some complexity' },
  { value: 'advanced', label: 'Advanced', desc: 'Rich vocabulary, complex plots' },
];

const GENERATION_STAGES = [
  { key: 'planning', label: 'Planning Story', icon: Lightbulb, range: [0, 10] },
  { key: 'cover', label: 'Generating Cover', icon: Image, range: [10, 25] },
  { key: 'pages', label: 'Creating Pages', icon: Layers, range: [25, 70] },
  { key: 'layout', label: 'Layout & Design', icon: Palette, range: [70, 85] },
  { key: 'packaging', label: 'Packaging Files', icon: Package, range: [85, 95] },
  { key: 'ready', label: 'Ready!', icon: CheckCircle, range: [95, 100] },
];

const STORY_HELPER_CHIPS = [
  { category: 'Hero', options: ['Brave child', 'Talking animal', 'Robot friend', 'Magic creature', 'Shy teenager'] },
  { category: 'Setting', options: ['Enchanted forest', 'Outer space', 'Underwater city', 'School', 'Ancient kingdom'] },
  { category: 'Conflict', options: ['Lost item quest', 'Save a friend', 'Overcome fear', 'Stop a villain', 'Win a contest'] },
  { category: 'Style', options: ['Funny', 'Heartwarming', 'Adventurous', 'Mysterious', 'Educational'] },
  { category: 'Moral', options: ['Courage', 'Friendship', 'Honesty', 'Kindness', 'Teamwork'] },
];

const AUTOSAVE_KEY = 'comic_builder_autosave';

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
  const [credits, setCredits] = useState(null);
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
  const [generationStartTime, setGenerationStartTime] = useState(null);
  const pollingRef = useRef(null);

  // Localization & targeting
  const [language, setLanguage] = useState('English');
  const [ageGroup, setAgeGroup] = useState('6-10');
  const [readingLevel, setReadingLevel] = useState('intermediate');
  const [bilingual, setBilingual] = useState(false);
  const [bilingualLang, setBilingualLang] = useState('Spanish');

  // Quick presets
  const [activePreset, setActivePreset] = useState(null);

  // AI helper
  const [improvingIdea, setImprovingIdea] = useState(false);
  const [storyScore, setStoryScore] = useState(null);
  const [analyzingStory, setAnalyzingStory] = useState(false);
  
  // Modals
  const [showRating, setShowRating] = useState(false);
  const [showUpsell, setShowUpsell] = useState(false);
  const { remixData: incomingRemix, sourceTool: remixSource, sourceTitle: remixTitle, consumed: hasRemix, dismiss: dismissRemix } = useRemixData('comic-storybook-builder');

  // ── Auto-save logic ──
  const saveProgress = useCallback(() => {
    const state = {
      step, selectedGenre, storyIdea, bookTitle, authorName, selectedPages,
      selectedAddOns, dedicationText, language, ageGroup, readingLevel,
      bilingual, bilingualLang, activePreset, timestamp: Date.now(),
    };
    try { localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(state)); } catch {}
  }, [step, selectedGenre, storyIdea, bookTitle, authorName, selectedPages, selectedAddOns, dedicationText, language, ageGroup, readingLevel, bilingual, bilingualLang, activePreset]);

  const restoreProgress = useCallback(() => {
    try {
      const saved = localStorage.getItem(AUTOSAVE_KEY);
      if (!saved) return false;
      const state = JSON.parse(saved);
      // Only restore if saved within last 24 hours
      if (Date.now() - state.timestamp > 24 * 60 * 60 * 1000) {
        localStorage.removeItem(AUTOSAVE_KEY);
        return false;
      }
      if (state.selectedGenre) setSelectedGenre(state.selectedGenre);
      if (state.storyIdea) setStoryIdea(state.storyIdea);
      if (state.bookTitle) setBookTitle(state.bookTitle);
      if (state.authorName) setAuthorName(state.authorName);
      if (state.selectedPages) setSelectedPages(state.selectedPages);
      if (state.selectedAddOns) setSelectedAddOns(state.selectedAddOns);
      if (state.dedicationText) setDedicationText(state.dedicationText);
      if (state.language) setLanguage(state.language);
      if (state.ageGroup) setAgeGroup(state.ageGroup);
      if (state.readingLevel) setReadingLevel(state.readingLevel);
      if (state.bilingual !== undefined) setBilingual(state.bilingual);
      if (state.bilingualLang) setBilingualLang(state.bilingualLang);
      if (state.activePreset) setActivePreset(state.activePreset);
      if (state.step > 1 && state.selectedGenre) setStep(state.step);
      return true;
    } catch { return false; }
  }, []);

  // Auto-save on every meaningful state change
  useEffect(() => {
    if (selectedGenre || storyIdea) saveProgress();
  }, [step, selectedGenre, storyIdea, bookTitle, authorName, selectedPages, selectedAddOns, dedicationText, language, ageGroup, readingLevel, bilingual, bilingualLang, saveProgress]);

  useEffect(() => {
    fetchCredits();
    fetchUserPlan();
    const restored = restoreProgress();
    if (restored) toast.info('Previous progress restored', { duration: 2000 });
    // Cross-tool auto-prefill
    if (hasRemix && incomingRemix) {
      const fields = mapRemixToFields(incomingRemix, 'comic-storybook-builder');
      if (fields.storyIdea) setStoryIdea(fields.storyIdea);
      if (fields.genre) setSelectedGenre(fields.genre);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
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

  // Improve story idea using AI
  const improveStoryIdea = async () => {
    if (!storyIdea.trim() || storyIdea.length < 5) {
      toast.error('Please write at least a short idea first');
      return;
    }
    setImprovingIdea(true);
    try {
      const res = await api.post('/api/comic-storybook-v2/improve-idea', {
        storyIdea,
        genre: selectedGenre,
        ageGroup,
        language,
        readingLevel,
      });
      if (res.data.success && res.data.improved) {
        setStoryIdea(res.data.improved);
        if (res.data.suggestedTitle && !bookTitle) setBookTitle(res.data.suggestedTitle);
        toast.success('Story idea improved!');
      } else {
        toast.info('Could not improve — your idea is already strong!');
      }
    } catch {
      toast.error('Improvement unavailable right now');
    }
    setImprovingIdea(false);
  };

  // Analyze story quality
  const analyzeStory = async () => {
    if (!storyIdea.trim() || storyIdea.length < 10) {
      toast.error('Write at least a short idea before analyzing');
      return;
    }
    setAnalyzingStory(true);
    try {
      const res = await api.post('/api/comic-storybook-v2/analyze-story', {
        storyIdea,
        genre: selectedGenre,
        ageGroup,
        readingLevel,
      });
      if (res.data.success) {
        setStoryScore(res.data);
      } else {
        toast.info(res.data.message || 'Analysis unavailable right now');
      }
    } catch {
      toast.error('Story analysis unavailable');
    }
    setAnalyzingStory(false);
  };

  // Apply a quick fix suggestion
  const applyQuickFix = async (fix) => {
    if (improvingIdea) return;
    setImprovingIdea(true);
    try {
      const res = await api.post('/api/comic-storybook-v2/improve-idea', {
        storyIdea: storyIdea + '. ' + fix.instruction,
        genre: selectedGenre,
        ageGroup,
        language,
        readingLevel,
      });
      if (res.data.success && res.data.improved) {
        setStoryIdea(res.data.improved);
        if (res.data.suggestedTitle && !bookTitle) setBookTitle(res.data.suggestedTitle);
        setStoryScore(null); // Clear score so user can re-analyze
        toast.success(`Applied: ${fix.label}`);
      } else {
        toast.info('Could not apply fix — try Improve My Idea instead');
      }
    } catch {
      toast.error('Fix unavailable');
    }
    setImprovingIdea(false);
  };

  // Handle quick preset selection
  const handlePresetSelect = (preset) => {
    if (activePreset === preset.id) { setActivePreset(null); return; }
    setActivePreset(preset.id);
    setSelectedGenre(preset.genre);
    setLanguage(preset.language);
    setAgeGroup(preset.ageGroup);
    setReadingLevel(preset.readingLevel);
    if (preset.bilingual) { setBilingual(true); }
    toast.success(`${preset.label} preset applied`);
  };

  // Get current generation stage from progress %
  const getCurrentStage = (progress) => {
    for (let i = GENERATION_STAGES.length - 1; i >= 0; i--) {
      if (progress >= GENERATION_STAGES[i].range[0]) return GENERATION_STAGES[i];
    }
    return GENERATION_STAGES[0];
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
      
      if (res.data.success && res.data.previewPages?.length > 0) {
        setPreviewPages(res.data.previewPages);
      }
      // If preview generation failed, previewPages stays empty — honest UI will handle it
    } catch (e) {
      // Preview failed — leave previewPages empty, UI shows honest "unavailable" state
      console.warn('Preview generation unavailable:', e.message);
    }
    
    setPreviewLoading(false);
  };

  // Poll job status
  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const res = await api.get(`/api/comic-storybook-v2/job/${jobId}`);
      setJob(res.data);
      
      if (res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
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
  }, []);

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
    setGenerationStartTime(Date.now());
    
    try {
      const res = await api.post('/api/comic-storybook-v2/generate', {
        genre: selectedGenre,
        storyIdea: storyIdea,
        title: bookTitle || 'My Comic Story',
        author: authorName || 'Anonymous',
        pageCount: selectedPages,
        addOns: selectedAddOns,
        dedicationText: selectedAddOns.dedication_page ? dedicationText : null,
        language,
        ageGroup,
        readingLevel,
        bilingual: bilingual ? bilingualLang : null,
      });
      
      setJob({ id: res.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Comic book generation started!');
      
      const interval = setInterval(() => pollJobStatus(res.data.jobId), 3000);
      pollingRef.current = interval;
      
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
      if (res.data.success && res.data.downloadUrls) {
        toast.success('Download started!');
        
        const urls = res.data.downloadUrls;
        const url = type === 'pdf' ? urls.pdf : (urls.cover || urls.pdf);
        if (url) {
          try {
            const resp = await fetch(url);
            const blob = await resp.blob();
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = `comic_${job.id.slice(0, 8)}.${type === 'pdf' ? 'pdf' : 'png'}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(blobUrl);
          } catch {
            const link = document.createElement('a');
            link.href = url;
            link.download = `comic_${job.id.slice(0, 8)}.${type === 'pdf' ? 'pdf' : 'png'}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
        } else {
          toast.error('Download URL not available');
        }
        
        fetchCredits();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Download failed');
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
    setLanguage('English');
    setAgeGroup('6-10');
    setReadingLevel('intermediate');
    setBilingual(false);
    setActivePreset(null);
    localStorage.removeItem(AUTOSAVE_KEY);
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
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 1 of 5</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Choose Your Story Type</h3>
        <p className="text-slate-400">Pick a genre or start with a quick preset</p>
      </div>

      {/* Quick Presets */}
      <div className="mb-6" data-testid="comic-presets">
        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Quick Presets</p>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_PRESETS.map(preset => {
            const Icon = preset.icon;
            const isActive = activePreset === preset.id;
            return (
              <button key={preset.id} type="button" onClick={() => handlePresetSelect(preset)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all ${
                  isActive ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 ring-1 ring-purple-500/30' : 'bg-slate-800/50 text-slate-400 border-slate-700/50 hover:text-white hover:border-slate-600'
                }`}
                data-testid={`comic-preset-${preset.id}`}>
                <Icon className="w-3 h-3" /> {preset.label}
              </button>
            );
          })}
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STORY_GENRES.map((genre) => {
          const Icon = genre.icon;
          return (
            <div
              key={genre.id}
              onClick={() => { setSelectedGenre(genre.id); setActivePreset(null); }}
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
        <div className="text-center mb-6">
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
              <BookMarked className="w-3.5 h-3.5 inline mr-1.5" /> Template Library
            </button>
            <button
              onClick={() => setShowTemplates(false)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                !showTemplates ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileText className="w-3.5 h-3.5 inline mr-1.5" /> Write My Own
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
          <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6 space-y-5">
            {/* AI Helper Chips */}
            <div data-testid="story-helper-chips">
              <label className="block text-sm font-medium text-slate-300 mb-2">Story Builder Assist</label>
              <div className="space-y-2">
                {STORY_HELPER_CHIPS.map(group => (
                  <div key={group.category} className="flex items-start gap-2">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider w-14 pt-1.5 flex-shrink-0">{group.category}</span>
                    <div className="flex flex-wrap gap-1">
                      {group.options.map(opt => (
                        <button key={opt} type="button"
                          onClick={() => {
                            const prefix = storyIdea ? storyIdea.trimEnd() + '. ' : '';
                            setStoryIdea(prefix + opt);
                            setSelectedTemplate(null);
                          }}
                          className="px-2 py-1 rounded-md text-[11px] bg-slate-700/50 text-slate-300 border border-slate-600/50 hover:bg-purple-500/20 hover:text-purple-300 hover:border-purple-500/30 transition-all"
                          data-testid={`chip-${opt.replace(/\s/g, '-').toLowerCase()}`}>
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

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
                  setStoryScore(null);
                  validateContent(e.target.value);
                }}
                className="bg-slate-700 border-slate-600 text-white min-h-32 text-lg"
                data-testid="story-idea-input"
              />
              <div className="flex items-center justify-between mt-2">
                <p className="text-xs text-slate-500">
                  Example: "{genre?.placeholder}"
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={improveStoryIdea}
                  disabled={improvingIdea || !storyIdea.trim()}
                  className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10 text-xs"
                  data-testid="improve-idea-btn"
                >
                  {improvingIdea ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Wand2 className="w-3 h-3 mr-1" />}
                  Improve My Idea
                </Button>
              </div>
              
              {contentError && (
                <div className="mt-3 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-red-400 text-sm font-medium">Content issue detected</p>
                    <p className="text-red-300/80 text-xs mt-1">{contentError.message}</p>
                  </div>
                </div>
              )}

              {/* Story Quality Score — Analyze button + Score Card */}
              {storyIdea.length >= 10 && (
                <div className="mt-3" data-testid="story-quality-section">
                  {!storyScore && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={analyzeStory}
                      disabled={analyzingStory}
                      className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 text-xs"
                      data-testid="analyze-story-btn"
                    >
                      {analyzingStory ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <Search className="w-3 h-3 mr-1.5" />}
                      {analyzingStory ? 'Analyzing...' : 'Analyze Story Quality'}
                    </Button>
                  )}

                  {storyScore && (
                    <div className="bg-slate-800/80 rounded-xl border border-slate-700 overflow-hidden" data-testid="story-score-card">
                      {/* Score Header */}
                      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
                        <div className="flex items-center gap-2.5">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                            storyScore.overall_score >= 85 ? 'bg-emerald-500/20 text-emerald-400' :
                            storyScore.overall_score >= 70 ? 'bg-sky-500/20 text-sky-400' :
                            storyScore.overall_score >= 50 ? 'bg-amber-500/20 text-amber-400' :
                            'bg-orange-500/20 text-orange-400'
                          }`} data-testid="story-score-value">
                            {storyScore.overall_score}
                          </div>
                          <div>
                            <p className="text-white text-xs font-bold">Story Quality Score</p>
                            <p className={`text-[10px] font-medium ${
                              storyScore.overall_score >= 85 ? 'text-emerald-400' :
                              storyScore.overall_score >= 70 ? 'text-sky-400' :
                              storyScore.overall_score >= 50 ? 'text-amber-400' :
                              'text-orange-400'
                            }`}>
                              {storyScore.overall_score >= 85 ? 'Strong story foundation' :
                               storyScore.overall_score >= 70 ? 'Good, could be stronger' :
                               storyScore.overall_score >= 50 ? 'Usable, needs improvement' :
                               'Too vague for best results'}
                            </p>
                          </div>
                        </div>
                        <button onClick={() => setStoryScore(null)} className="text-slate-500 hover:text-white text-xs">Dismiss</button>
                      </div>

                      {/* Dimension Bars */}
                      <div className="px-4 py-3 grid grid-cols-2 gap-x-4 gap-y-2" data-testid="score-dimensions">
                        {storyScore.dimensions && Object.entries(storyScore.dimensions).map(([key, val]) => (
                          <div key={key} className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-500 w-20 capitalize flex-shrink-0">{key.replace(/_/g, ' ')}</span>
                            <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full transition-all duration-500 ${
                                val >= 80 ? 'bg-emerald-500' : val >= 60 ? 'bg-sky-500' : val >= 40 ? 'bg-amber-500' : 'bg-orange-500'
                              }`} style={{ width: `${val}%` }} />
                            </div>
                            <span className="text-[10px] text-slate-400 w-6 text-right">{val}</span>
                          </div>
                        ))}
                      </div>

                      {/* Strengths + Opportunities */}
                      <div className="px-4 py-3 border-t border-slate-700/50 grid sm:grid-cols-2 gap-3">
                        {storyScore.strengths?.length > 0 && (
                          <div>
                            <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider mb-1.5">Strengths</p>
                            {storyScore.strengths.map((s, i) => (
                              <p key={i} className="text-[11px] text-slate-300 leading-relaxed flex items-start gap-1 mb-1">
                                <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" /> {s}
                              </p>
                            ))}
                          </div>
                        )}
                        {storyScore.opportunities?.length > 0 && (
                          <div>
                            <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider mb-1.5">Opportunities</p>
                            {storyScore.opportunities.map((o, i) => (
                              <p key={i} className="text-[11px] text-slate-300 leading-relaxed flex items-start gap-1 mb-1">
                                <Lightbulb className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" /> {o}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Quick Fix Chips */}
                      {storyScore.quick_fixes?.length > 0 && (
                        <div className="px-4 py-3 border-t border-slate-700/50" data-testid="quick-fix-chips">
                          <p className="text-[10px] font-bold text-purple-400 uppercase tracking-wider mb-2">One-Click Improvements</p>
                          <div className="flex flex-wrap gap-1.5">
                            {storyScore.quick_fixes.map((fix, i) => (
                              <button
                                key={i}
                                onClick={() => applyQuickFix(fix)}
                                disabled={improvingIdea}
                                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/25 hover:bg-purple-500/20 transition-all disabled:opacity-50"
                                data-testid={`quick-fix-${i}`}
                              >
                                {improvingIdea ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                                {fix.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Re-analyze button */}
                      <div className="px-4 py-2.5 border-t border-slate-700/50 flex items-center justify-between">
                        <span className="text-[10px] text-slate-600">Score updates after edits — re-analyze anytime</span>
                        <Button type="button" variant="ghost" size="sm" onClick={analyzeStory} disabled={analyzingStory} className="text-xs text-cyan-400 hover:text-cyan-300 h-7" data-testid="re-analyze-btn">
                          {analyzingStory ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <RotateCcw className="w-3 h-3 mr-1" />}
                          Re-analyze
                        </Button>
                      </div>
                    </div>
                  )}
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

            {/* Language & Localization Controls */}
            <div className="border-t border-slate-700 pt-5" data-testid="localization-controls">
              <p className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-1.5"><Globe className="w-4 h-4 text-purple-400" /> Language & Audience</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {/* Language */}
                <div>
                  <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1 block">Language</label>
                  <select value={language} onChange={(e) => setLanguage(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                    data-testid="language-select">
                    {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
                {/* Age Group */}
                <div>
                  <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1 block">Age Group</label>
                  <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                    data-testid="age-group-select">
                    {AGE_GROUPS.map(a => <option key={a.value} value={a.value}>{a.label} ({a.desc})</option>)}
                  </select>
                </div>
                {/* Reading Level */}
                <div>
                  <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1 block">Reading Level</label>
                  <select value={readingLevel} onChange={(e) => setReadingLevel(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                    data-testid="reading-level-select">
                    {READING_LEVELS.map(r => <option key={r.value} value={r.value}>{r.label} — {r.desc}</option>)}
                  </select>
                </div>
              </div>
              {/* Bilingual toggle */}
              <div className="mt-3 flex items-center gap-3">
                <button type="button" onClick={() => setBilingual(!bilingual)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    bilingual ? 'bg-teal-500/20 text-teal-300 border-teal-500/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'
                  }`} data-testid="bilingual-toggle">
                  <Globe className="w-3 h-3" /> Bilingual Book
                </button>
                {bilingual && (
                  <select value={bilingualLang} onChange={(e) => setBilingualLang(e.target.value)}
                    className="bg-slate-700 border border-slate-600 rounded-lg px-2 py-1.5 text-xs text-white focus:border-teal-500 outline-none"
                    data-testid="bilingual-lang-select">
                    {LANGUAGES.filter(l => l !== language).map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                )}
              </div>
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
            <p className={`text-xl font-bold ${(credits || 0) >= calculateCost() ? 'text-green-400' : credits === null ? 'text-slate-400' : 'text-red-400'}`} data-testid="storybook-balance-display">
              {credits === null ? <span className="inline-block w-16 h-6 bg-slate-700 rounded animate-pulse" /> : credits >= 999999 ? '∞ Unlimited' : `${credits.toLocaleString()} credits`}
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
    const activeAddOns = ADD_ONS.filter(a => selectedAddOns[a.id]);
    const currentStage = job ? getCurrentStage(job.progress || 0) : null;
    
    return (
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
            <span className="text-purple-400 font-medium">Step 5 of 5</span>
          </div>
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Preview & Generate</h3>
          <p className="text-slate-400">Review your comic book and start generation</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          {/* LEFT: Summary + Generate */}
          <div className="space-y-4">
            {/* Book Summary Card */}
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-5" data-testid="book-summary">
              <h4 className="font-bold text-white text-lg mb-4 flex items-center gap-2"><BookOpen className="w-5 h-5 text-purple-400" /> Book Summary</h4>
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Genre:</span><span className="text-white font-medium text-sm">{genre?.name}</span></div>
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Title:</span><span className="text-white font-medium text-sm">{bookTitle || 'My Comic Story'}</span></div>
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Author:</span><span className="text-white font-medium text-sm">{authorName || 'Anonymous'}</span></div>
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Pages:</span><span className="text-white font-medium text-sm">{selectedPages} pages ({pageOption?.label})</span></div>
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Language:</span><span className="text-white font-medium text-sm">{language}{bilingual ? ` + ${bilingualLang}` : ''}</span></div>
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Audience:</span><span className="text-white font-medium text-sm">{ageGroup} years ({readingLevel})</span></div>
                <div className="pt-3 border-t border-slate-700">
                  <p className="text-slate-400 text-xs mb-1.5 font-medium">Story Idea:</p>
                  <p className="text-white text-xs bg-slate-700/50 p-2.5 rounded-lg leading-relaxed">{storyIdea.slice(0, 150)}{storyIdea.length > 150 ? '...' : ''}</p>
                </div>
                {activeAddOns.length > 0 && (
                  <div className="pt-3 border-t border-slate-700">
                    <p className="text-slate-400 text-xs mb-1.5 font-medium">Add-ons:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {activeAddOns.map(addon => (
                        <span key={addon.id} className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full">{addon.name}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* What You'll Receive — Deliverables Summary */}
            <div className="bg-gradient-to-br from-emerald-500/5 to-teal-500/5 rounded-2xl border border-emerald-500/15 p-5" data-testid="deliverables-summary">
              <h4 className="font-bold text-white text-sm mb-3 flex items-center gap-2"><Package className="w-4 h-4 text-emerald-400" /> What You'll Receive</h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0"><FileText className="w-3.5 h-3.5 text-emerald-400" /></div><div><p className="text-xs text-white font-medium">Comic Book PDF</p><p className="text-[10px] text-slate-500">{selectedPages}-page full-color digital comic</p></div></div>
                <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0"><Image className="w-3.5 h-3.5 text-emerald-400" /></div><div><p className="text-xs text-white font-medium">Cover Image</p><p className="text-[10px] text-slate-500">High-quality standalone cover (PNG)</p></div></div>
                <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0"><FileArchive className="w-3.5 h-3.5 text-emerald-400" /></div><div><p className="text-xs text-white font-medium">Page Images</p><p className="text-[10px] text-slate-500">{selectedPages} individual page images</p></div></div>
                {selectedAddOns.hd_print && (
                  <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0"><Printer className="w-3.5 h-3.5 text-amber-400" /></div><div><p className="text-xs text-white font-medium">Print-Ready PDF</p><p className="text-[10px] text-slate-500">300 DPI for professional printing</p></div></div>
                )}
                {selectedAddOns.activity_pages && (
                  <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0"><Palette className="w-3.5 h-3.5 text-amber-400" /></div><div><p className="text-xs text-white font-medium">Activity Pages</p><p className="text-[10px] text-slate-500">Puzzle & coloring pages included</p></div></div>
                )}
                {selectedAddOns.dedication_page && (
                  <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0"><Heart className="w-3.5 h-3.5 text-amber-400" /></div><div><p className="text-xs text-white font-medium">Dedication Page</p><p className="text-[10px] text-slate-500">Personal message page</p></div></div>
                )}
                {selectedAddOns.commercial_license && (
                  <div className="flex items-center gap-2.5"><div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0"><Crown className="w-3.5 h-3.5 text-amber-400" /></div><div><p className="text-xs text-white font-medium">Commercial License</p><p className="text-[10px] text-slate-500">Rights to sell or distribute</p></div></div>
                )}
              </div>
            </div>
            
            {/* Final Cost + Generate */}
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-5">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <p className="text-slate-400 text-xs">Total Cost</p>
                  <p className="text-2xl font-bold text-white">{calculateCost()} credits</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-400 text-xs">Your Balance</p>
                  <p className={`text-lg font-bold ${(credits || 0) >= calculateCost() ? 'text-green-400' : credits === null ? 'text-slate-400' : 'text-red-400'}`} data-testid="storybook-balance-display">
                    {credits === null ? <span className="inline-block w-16 h-6 bg-slate-700 rounded animate-pulse" /> : credits >= 999999 ? 'Unlimited' : `${credits.toLocaleString()} credits`}
                  </p>
                </div>
              </div>
              {userPlan !== 'free' && (
                <p className="text-xs text-green-400 mb-3">
                  {userPlan === 'creator' ? '20%' : userPlan === 'pro' ? '30%' : '40%'} subscriber discount applied!
                </p>
              )}
              {/* Estimated time */}
              <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-4">
                <Clock className="w-3 h-3" />
                <span>Estimated generation time: {selectedPages <= 10 ? '2-4' : selectedPages <= 20 ? '4-7' : '6-10'} minutes</span>
              </div>
              <Button 
                onClick={generateComicBook}
                disabled={loading || credits < calculateCost()}
                className="w-full py-5 text-base bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                data-testid="generate-btn"
              >
                {loading ? (
                  <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Generating...</>
                ) : (
                  <><Wand2 className="w-5 h-5 mr-2" /> Generate Full Comic Book</>
                )}
              </Button>
            </div>
          </div>
          
          {/* RIGHT: Preview / Generation Progress / Result */}
          <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6">
            <h4 className="font-bold text-white text-lg mb-4">
              {job ? 'Generation Progress' : 'Preview'}
            </h4>
            
            {job ? (
              <div className="space-y-4">
                {/* Show WaitingWithGames during processing */}
                {(job.status === 'PROCESSING' || job.status === 'QUEUED') ? (
                  <>
                    {/* Generation Stage Indicators */}
                    <div className="space-y-1.5 mb-4" data-testid="generation-stages">
                      {GENERATION_STAGES.map((stage, idx) => {
                        const StageIcon = stage.icon;
                        const progress = job.progress || 0;
                        const isActive = progress >= stage.range[0] && progress < stage.range[1];
                        const isComplete = progress >= stage.range[1];
                        const isPending = progress < stage.range[0];
                        return (
                          <div key={stage.key} className={`flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all ${
                            isActive ? 'bg-purple-500/15 border border-purple-500/30' : isComplete ? 'bg-emerald-500/5' : 'opacity-40'
                          }`} data-testid={`stage-${stage.key}`}>
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                              isComplete ? 'bg-emerald-500/20' : isActive ? 'bg-purple-500/20' : 'bg-slate-700/50'
                            }`}>
                              {isComplete ? <Check className="w-3 h-3 text-emerald-400" /> : isActive ? <Loader2 className="w-3 h-3 text-purple-400 animate-spin" /> : <StageIcon className="w-3 h-3 text-slate-500" />}
                            </div>
                            <span className={`text-xs font-medium ${isComplete ? 'text-emerald-400' : isActive ? 'text-purple-300' : 'text-slate-600'}`}>{stage.label}</span>
                          </div>
                        );
                      })}
                    </div>
                    <WaitingWithGames 
                      progress={job.progress || 0}
                      status={currentStage?.label || job.progressMessage || (job.status === 'QUEUED' ? 'In queue...' : 'Creating your comic book...')}
                      estimatedTime={selectedPages <= 10 ? '2-4 minutes' : selectedPages <= 20 ? '4-7 minutes' : '6-10 minutes'}
                      onCancel={() => {
                        toast.info('Generation in progress - please wait');
                      }}
                      currentFeature="/app/comic-storybook"
                      showExploreFeatures={true}
                    />
                  </>
                ) : (
                  <>
                    {/* Status Badge + Generation Time */}
                    <div className="flex items-center justify-between">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                        job.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {job.status}
                      </span>
                      {job.status === 'COMPLETED' && generationStartTime && (
                        <span className="text-xs text-slate-400" data-testid="generation-time">
                          Generated in {Math.floor((Date.now() - generationStartTime) / 60000)}m {Math.floor(((Date.now() - generationStartTime) / 1000) % 60)}s
                        </span>
                      )}
                    </div>
                  </>
                )}
                
                {/* Download Buttons */}
                {job.status === 'COMPLETED' && (
                  <div className="space-y-3 mt-6">
                    {/* Generated Page Gallery */}
                    {(job.page_urls?.length > 0 || job.coverUrl) && (
                      <div className="mb-4" data-testid="generated-pages-gallery">
                        <p className="text-xs text-slate-400 mb-2 font-medium">Your Generated Pages</p>
                        <div className="grid grid-cols-3 gap-2 max-h-[300px] overflow-y-auto pr-1">
                          {job.coverUrl && (
                            <div className="relative rounded-lg overflow-hidden border border-slate-700 bg-slate-800" data-testid="generated-cover">
                              <img 
                                src={job.coverUrl} 
                                alt="Cover" 
                                className="w-full aspect-[3/4] object-cover"
                                loading="lazy"
                              />
                              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-1.5">
                                <span className="text-[10px] text-white font-medium">Cover</span>
                              </div>
                            </div>
                          )}
                          {(job.page_urls || []).map((p, i) => (
                            <div key={i} className="relative rounded-lg overflow-hidden border border-slate-700 bg-slate-800" data-testid={`generated-page-${p.page}`}>
                              <img 
                                src={p.url} 
                                alt={`Page ${p.page}`} 
                                className="w-full aspect-[3/4] object-cover"
                                loading="lazy"
                              />
                              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-1.5">
                                <span className="text-[10px] text-white font-medium">Page {p.page}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {/* PDF Download */}
                    {job.pdfUrl && (
                      <DownloadWithExpiry
                        downloadUrl={job.pdfUrl}
                        filename={`comic_storybook_${job.id.slice(0, 8)}.pdf`}
                        fileType="application/pdf"
                        isPremium={userPlan !== 'free'}
                        contentType="STORYBOOK"
                      />
                    )}

                    {/* Cover Image Download */}
                    {job.coverUrl && (
                      <Button
                        onClick={async () => {
                          try {
                            const resp = await fetch(job.coverUrl);
                            const blob = await resp.blob();
                            const blobUrl = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = blobUrl;
                            a.download = `cover_${job.id.slice(0, 8)}.png`;
                            a.click();
                            URL.revokeObjectURL(blobUrl);
                          } catch {
                            const a = document.createElement('a');
                            a.href = job.coverUrl;
                            a.download = `cover_${job.id.slice(0, 8)}.png`;
                            a.click();
                          }
                          toast.success('Cover download started!');
                        }}
                        variant="outline"
                        className="w-full border-slate-600 text-slate-300"
                      >
                        <Download className="w-4 h-4 mr-2" /> Download Cover Image
                      </Button>
                    )}

                    {/* Print Version */}
                    {selectedAddOns.hd_print && (
                      <Button 
                        onClick={() => handleDownload('pdf')}
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

                    <NextActionHooks
                      toolType="comic-storybook"
                      prompt={storyIdea || `${selectedGenre || ''} comic story`}
                      settings={{ genre: selectedGenre }}
                      generationId={job?.id}
                      title={`Comic Storybook`}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {previewLoading ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
                    <p className="text-sm text-slate-400">Generating cover preview...</p>
                  </div>
                ) : previewPages.length > 0 ? (
                  <div className="grid grid-cols-2 gap-4">
                    {previewPages.map((page, idx) => (
                      <div key={idx} className="relative rounded-lg overflow-hidden border border-slate-600 bg-slate-800" data-testid={`preview-card-${idx}`}>
                        <SafeImage
                          src={page.url}
                          alt={page.type === 'cover' ? 'Cover Preview' : `Page ${idx}`}
                          aspectRatio="3/4"
                          titleOverlay={page.type === 'cover' ? 'Cover' : `Page ${idx}`}
                          fallbackType="gradient"
                        />
                        <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                          <span className="text-white text-xs font-medium">
                            {page.type === 'cover' ? 'Cover' : `Page ${idx}`}
                          </span>
                        </div>
                        <div className="absolute top-2 right-2">
                          <span className="text-[9px] text-white/60 bg-black/40 px-1.5 py-0.5 rounded">AI Preview</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Enhanced Preview Unavailable State */
                  <div className="space-y-4" data-testid="preview-unavailable">
                    {/* Visual placeholder */}
                    <div className="relative aspect-[3/4] bg-gradient-to-br from-purple-500/5 via-slate-800 to-pink-500/5 rounded-xl border border-slate-700 overflow-hidden flex items-center justify-center">
                      <div className="text-center p-6">
                        <BookOpen className="w-12 h-12 mx-auto text-purple-500/30 mb-3" />
                        <p className="text-white font-bold text-sm mb-0.5">{bookTitle || 'My Comic Story'}</p>
                        <p className="text-slate-500 text-xs mb-1">by {authorName || 'Anonymous'}</p>
                        <p className="text-[10px] text-slate-600 mt-2">{genre?.name} &middot; {selectedPages} pages &middot; {language}</p>
                      </div>
                      <div className="absolute top-2 right-2">
                        <span className="text-[9px] text-white/40 bg-black/30 px-1.5 py-0.5 rounded">Cover Preview</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
                      <CheckCircle className="w-3 h-3 text-emerald-500" />
                      <span>All settings confirmed — ready to generate</span>
                    </div>
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
                <span className="text-purple-300 font-medium" data-testid="storybook-credits">{credits === null ? <span className="inline-block w-12 h-4 bg-purple-500/20 rounded animate-pulse" /> : credits >= 999999 ? '∞ Unlimited' : `${credits.toLocaleString()} Credits`}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Remix Banner */}
        {hasRemix && <div className="max-w-xl mx-auto mb-4"><RemixBanner sourceTool={remixSource} sourceTitle={remixTitle} onDismiss={dismissRemix} /></div>}
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
      
      {showUpsell && (
        <UpsellModal
          isOpen={showUpsell}
          credits={0}
          onClose={() => setShowUpsell(false)}
        />
      )}
      
      {/* Help Guide */}
      <HelpGuide pageId="comic-storybook" />
    </div>
  );
}
