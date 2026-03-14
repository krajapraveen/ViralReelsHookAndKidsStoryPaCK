import React, { useState, useEffect } from 'react';
import { 
  Moon, 
  Sparkles, 
  ChevronRight, 
  ChevronLeft, 
  Copy, 
  Download, 
  Check, 
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Volume2,
  Music,
  Clock,
  Heart
} from 'lucide-react';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';
import CreationActionsBar from '../components/CreationActionsBar';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Step indicator
const StepIndicator = ({ currentStep, totalSteps }) => {
  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {[...Array(totalSteps)].map((_, index) => (
        <React.Fragment key={index}>
          <div 
            className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
              index + 1 === currentStep 
                ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white scale-110' 
                : index + 1 < currentStep
                ? 'bg-green-500 text-white'
                : 'bg-slate-700 text-slate-400'
            }`}
          >
            {index + 1 < currentStep ? <Check className="w-5 h-5" /> : index + 1}
          </div>
          {index < totalSteps - 1 && (
            <div className={`w-12 h-1 rounded ${
              index + 1 < currentStep ? 'bg-green-500' : 'bg-slate-700'
            }`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

// User manual component
const UserManual = () => {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden mb-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-700/30 transition-colors"
        data-testid="user-manual-toggle"
      >
        <div className="flex items-center gap-3">
          <HelpCircle className="w-5 h-5 text-indigo-400" />
          <span className="font-semibold text-white">How to Use Bedtime Story Builder</span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
      </button>
      
      {isOpen && (
        <div className="p-4 pt-0 space-y-4 text-sm">
          <div className="grid md:grid-cols-2 gap-4">
            {/* Steps */}
            <div className="bg-slate-900/50 rounded-lg p-4">
              <h4 className="font-semibold text-indigo-400 mb-3">How to Use</h4>
              <ol className="space-y-2 text-slate-300">
                <li className="flex gap-2"><span className="text-indigo-400 font-bold">1.</span> Select your child's age group</li>
                <li className="flex gap-2"><span className="text-indigo-400 font-bold">2.</span> Choose a theme + moral lesson</li>
                <li className="flex gap-2"><span className="text-indigo-400 font-bold">3.</span> Choose story length + voice style</li>
                <li className="flex gap-2"><span className="text-indigo-400 font-bold">4.</span> Click Generate</li>
                <li className="flex gap-2"><span className="text-indigo-400 font-bold">5.</span> Read aloud using pause markers & SFX cues</li>
              </ol>
            </div>
            
            {/* Best Practices */}
            <div className="bg-slate-900/50 rounded-lg p-4">
              <h4 className="font-semibold text-green-400 mb-3">Best Practices</h4>
              <ul className="space-y-2 text-slate-300">
                <li className="flex gap-2"><span className="text-green-400">✔</span> Read slowly and softly before bedtime</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Use [PAUSE] markers to keep attention</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Add your child's name for personalization</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Create a cozy atmosphere</li>
              </ul>
            </div>
          </div>
          
          {/* What Not To Do */}
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <h4 className="font-semibold text-red-400 mb-3">What Not To Do</h4>
            <ul className="grid md:grid-cols-2 gap-2 text-slate-300">
              <li className="flex gap-2"><span className="text-red-400">✗</span> Don't use copyrighted characters</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Don't request scary or violent stories</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Don't paste adult content</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Don't use brand names</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default function BedtimeStoryBuilder() {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copiedSection, setCopiedSection] = useState(null);
  const [activeTab, setActiveTab] = useState('script');
  
  // Form state
  const [ageGroup, setAgeGroup] = useState('');
  const [theme, setTheme] = useState('');
  const [moral, setMoral] = useState('');
  const [length, setLength] = useState('5');
  const [voiceStyle, setVoiceStyle] = useState('calm_parent');
  const [childName, setChildName] = useState('');
  
  // Results
  const [story, setStory] = useState(null);
  const [creditsUsed, setCreditsUsed] = useState(0);
  const [remainingCredits, setRemainingCredits] = useState(0);
  
  // Fetch config
  useEffect(() => {
    fetchConfig();
  }, []);
  
  const fetchConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/bedtime-story-builder/config`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to fetch config:', error);
      toast.error('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };
  
  const handleGenerate = async () => {
    if (!ageGroup || !theme || !moral || !length || !voiceStyle) {
      toast.error('Please complete all selections');
      return;
    }
    
    setGenerating(true);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/bedtime-story-builder/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          age_group: ageGroup,
          theme,
          moral,
          length,
          voice_style: voiceStyle,
          child_name: childName || null
        })
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setStory(data.story);
        setCreditsUsed(data.credits_used);
        setRemainingCredits(data.remaining_credits);
        setStep(5);
        toast.success('Story generated!');
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (error) {
      console.error('Generation error:', error);
      toast.error('Failed to generate story');
    } finally {
      setGenerating(false);
    }
  };
  
  const copySection = async (content, section) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedSection(section);
      toast.success('Copied!');
      setTimeout(() => setCopiedSection(null), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  };
  
  const downloadStory = async () => {
    if (!story) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/bedtime-story-builder/export`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(story)
      });
      
      const data = await response.json();
      
      if (data.success) {
        const blob = new Blob([data.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Downloaded!');
      }
    } catch (error) {
      toast.error('Download failed');
    }
  };
  
  const resetGenerator = () => {
    setStep(1);
    setAgeGroup('');
    setTheme('');
    setMoral('');
    setLength('5');
    setVoiceStyle('calm_parent');
    setChildName('');
    setStory(null);
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500/20 rounded-full text-indigo-400 text-sm mb-4">
            <Moon className="w-4 h-4" />
            <span>Bedtime Story Audio Script Builder</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Create Magical Bedtime Stories
          </h1>
          <p className="text-slate-400">
            Narration-ready scripts with voice notes & sound effect cues • 10 credits
          </p>
        </div>
        
        {/* User Manual */}
        <UserManual />
        
        {/* Main Card */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 md:p-8">
          {step < 5 && <StepIndicator currentStep={step} totalSteps={4} />}
          
          {/* Step 1: Age Group */}
          {step === 1 && (
            <div className="space-y-6" data-testid="step-age">
              <div className="text-center">
                <div className="w-16 h-16 bg-indigo-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Heart className="w-8 h-8 text-indigo-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Choose Child's Age</h2>
                <p className="text-slate-400">Stories are tailored for each age group</p>
              </div>
              
              <div className="grid grid-cols-3 gap-4 max-w-xl mx-auto">
                {config?.ageGroups?.map((age) => (
                  <button
                    key={age.id}
                    onClick={() => setAgeGroup(age.id)}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      ageGroup === age.id
                        ? 'border-indigo-500 bg-indigo-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                    data-testid={`age-${age.id}`}
                  >
                    <div className="text-2xl font-bold text-white">{age.name}</div>
                    <div className="text-xs text-slate-400 mt-1">{age.description}</div>
                  </button>
                ))}
              </div>
              
              <div className="flex justify-center">
                <button
                  onClick={() => ageGroup && setStep(2)}
                  disabled={!ageGroup}
                  className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
                  data-testid="next-step-1"
                >
                  Continue <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 2: Theme & Moral */}
          {step === 2 && (
            <div className="space-y-6" data-testid="step-theme">
              <div className="text-center">
                <div className="w-16 h-16 bg-purple-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <BookOpen className="w-8 h-8 text-purple-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Choose Theme & Moral</h2>
                <p className="text-slate-400">Select the story's theme and lesson</p>
              </div>
              
              <div className="max-w-md mx-auto space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Theme</label>
                  <select
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    data-testid="theme-select"
                  >
                    <option value="">Select a theme...</option>
                    {config?.themes?.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Moral Lesson</label>
                  <select
                    value={moral}
                    onChange={(e) => setMoral(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    data-testid="moral-select"
                  >
                    <option value="">Select a moral...</option>
                    {config?.morals?.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-all"
                >
                  <ChevronLeft className="w-5 h-5" /> Back
                </button>
                <button
                  onClick={() => theme && moral && setStep(3)}
                  disabled={!theme || !moral}
                  className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
                  data-testid="next-step-2"
                >
                  Continue <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 3: Length & Voice Style */}
          {step === 3 && (
            <div className="space-y-6" data-testid="step-voice">
              <div className="text-center">
                <div className="w-16 h-16 bg-pink-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Volume2 className="w-8 h-8 text-pink-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Length & Voice Style</h2>
                <p className="text-slate-400">Customize the narration experience</p>
              </div>
              
              <div className="max-w-xl mx-auto space-y-6">
                {/* Length */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-3">Story Length</label>
                  <div className="grid grid-cols-3 gap-3">
                    {config?.lengths?.map((l) => (
                      <button
                        key={l.id}
                        onClick={() => setLength(l.id)}
                        className={`p-3 rounded-xl border transition-all ${
                          length === l.id
                            ? 'border-pink-500 bg-pink-500/10'
                            : 'border-slate-700 hover:border-slate-600'
                        }`}
                        data-testid={`length-${l.id}`}
                      >
                        <Clock className={`w-5 h-5 mx-auto mb-1 ${length === l.id ? 'text-pink-400' : 'text-slate-400'}`} />
                        <div className="text-white font-medium">{l.name}</div>
                        {l.default && <span className="text-xs text-pink-400">Recommended</span>}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Voice Style */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-3">Voice Style</label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {config?.voiceStyles?.map((v) => (
                      <button
                        key={v.id}
                        onClick={() => setVoiceStyle(v.id)}
                        className={`p-4 rounded-xl border transition-all text-left ${
                          voiceStyle === v.id
                            ? 'border-indigo-500 bg-indigo-500/10'
                            : 'border-slate-700 hover:border-slate-600'
                        }`}
                        data-testid={`voice-${v.id}`}
                      >
                        <div className="text-white font-medium">{v.name}</div>
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Optional Child Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Child's Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={childName}
                    onChange={(e) => setChildName(e.target.value)}
                    placeholder="Enter name for personalization"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    data-testid="child-name-input"
                  />
                </div>
              </div>
              
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setStep(2)}
                  className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-all"
                >
                  <ChevronLeft className="w-5 h-5" /> Back
                </button>
                <button
                  onClick={() => setStep(4)}
                  className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold rounded-xl transition-all"
                  data-testid="next-step-3"
                >
                  Continue <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 4: Generate */}
          {step === 4 && (
            <div className="space-y-6" data-testid="step-generate">
              <div className="text-center">
                <div className="w-16 h-16 bg-yellow-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-8 h-8 text-yellow-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Ready to Generate!</h2>
                <p className="text-slate-400">Review your selections</p>
              </div>
              
              {/* Summary */}
              <div className="max-w-md mx-auto bg-slate-800/50 rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Age Group:</span>
                  <span className="text-white font-medium">{ageGroup}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Theme:</span>
                  <span className="text-white font-medium">{theme}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Moral:</span>
                  <span className="text-white font-medium">{moral}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Length:</span>
                  <span className="text-white font-medium">{length} min</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Voice Style:</span>
                  <span className="text-white font-medium">
                    {config?.voiceStyles?.find(v => v.id === voiceStyle)?.name}
                  </span>
                </div>
                {childName && (
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">For:</span>
                    <span className="text-white font-medium">{childName}</span>
                  </div>
                )}
                <div className="border-t border-slate-700 pt-3 flex justify-between items-center">
                  <span className="text-slate-400">Cost:</span>
                  <span className="text-green-400 font-bold">10 Credits</span>
                </div>
              </div>
              
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setStep(3)}
                  className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-all"
                >
                  <ChevronLeft className="w-5 h-5" /> Back
                </button>
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-all"
                  data-testid="generate-btn"
                >
                  {generating ? (
                    <>
                      <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                      Creating Story...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Generate Audio Script
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
          
          {/* Step 5: Results */}
          {step === 5 && story && (
            <div className="space-y-6" data-testid="step-results">
              {/* Header */}
              <div className="text-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-green-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Your Story Is Ready!</h2>
                <p className="text-slate-400">
                  {creditsUsed} credits used • Character: {story.metadata.character}
                </p>
              </div>
              
              {/* Action buttons */}
              <div className="flex justify-center gap-3 flex-wrap">
                <button
                  onClick={downloadStory}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-all"
                  data-testid="download-btn"
                >
                  <Download className="w-4 h-4" /> Download TXT
                </button>
                <button
                  onClick={resetGenerator}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all"
                  data-testid="new-story-btn"
                >
                  <Moon className="w-4 h-4" /> New Story
                </button>
              </div>
              
              {/* Tabs */}
              <div className="flex gap-2 justify-center">
                <button
                  onClick={() => setActiveTab('script')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                    activeTab === 'script' ? 'bg-indigo-500 text-white' : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  <BookOpen className="w-4 h-4" /> Story Script
                </button>
                <button
                  onClick={() => setActiveTab('voice')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                    activeTab === 'voice' ? 'bg-indigo-500 text-white' : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  <Volume2 className="w-4 h-4" /> Voice Notes
                </button>
                <button
                  onClick={() => setActiveTab('sfx')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                    activeTab === 'sfx' ? 'bg-indigo-500 text-white' : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  <Music className="w-4 h-4" /> SFX Cues
                </button>
              </div>
              
              {/* Content */}
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                {activeTab === 'script' && (
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="font-semibold text-white">Narration Script</h3>
                      <button
                        onClick={() => copySection(story.script, 'script')}
                        className={`p-2 rounded-lg transition-all ${
                          copiedSection === 'script' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                        }`}
                      >
                        {copiedSection === 'script' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                    <pre className="text-slate-300 whitespace-pre-wrap font-sans text-sm leading-relaxed">
                      {story.script}
                    </pre>
                  </div>
                )}
                
                {activeTab === 'voice' && (
                  <div>
                    <h3 className="font-semibold text-white mb-4">Voice Pacing Notes</h3>
                    <div className="space-y-4">
                      {story.voice_notes.map((note, idx) => (
                        <div key={idx} className="bg-slate-900/50 rounded-lg p-4">
                          <div className="text-indigo-400 font-semibold mb-1">{note.scene}</div>
                          <div className="text-xs text-slate-500 mb-2">Pacing: {note.pacing}</div>
                          <div className="text-slate-300 text-sm">{note.note}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {activeTab === 'sfx' && (
                  <div>
                    <h3 className="font-semibold text-white mb-4">Sound Effect Cues</h3>
                    <div className="grid md:grid-cols-2 gap-3">
                      {story.sfx_cues.map((cue, idx) => (
                        <div key={idx} className="bg-slate-900/50 rounded-lg p-3">
                          <div className="text-pink-400 font-semibold text-sm">{cue.scene}</div>
                          <div className="text-slate-300 text-sm mt-1">{cue.cue}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Disclaimer */}
        <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-200">
              No copyrighted characters, brands, or music references are used. All stories are original and family-friendly.
            </p>
          </div>
        </div>

        {/* Remix & Variations Engine */}
        {story && step === 5 && (
          <CreationActionsBar
            toolType="bedtime-story-builder"
            originalPrompt={`${theme || ''} bedtime story`}
            originalSettings={{ ageGroup, theme, moral }}
            remixSourceTitle={story?.title || 'Bedtime Story'}
          />
        )}
      </div>
      
      <HelpGuide pageId="bedtime-story-builder" />
    </div>
  );
}
