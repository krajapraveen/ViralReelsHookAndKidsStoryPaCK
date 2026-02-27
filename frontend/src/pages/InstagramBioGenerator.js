import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Instagram, 
  Sparkles, 
  ChevronRight, 
  ChevronLeft, 
  Copy, 
  Download, 
  Check, 
  AlertCircle,
  HelpCircle,
  User,
  Target,
  Palette,
  Zap,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Step indicator component
const StepIndicator = ({ currentStep, totalSteps }) => {
  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {[...Array(totalSteps)].map((_, index) => (
        <React.Fragment key={index}>
          <div 
            className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
              index + 1 === currentStep 
                ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white scale-110' 
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
          <HelpCircle className="w-5 h-5 text-purple-400" />
          <span className="font-semibold text-white">How to Use Instagram Bio Generator</span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
      </button>
      
      {isOpen && (
        <div className="p-4 pt-0 space-y-4 text-sm">
          <div className="grid md:grid-cols-2 gap-4">
            {/* Steps */}
            <div className="bg-slate-900/50 rounded-lg p-4">
              <h4 className="font-semibold text-purple-400 mb-3">Steps to Generate</h4>
              <ol className="space-y-2 text-slate-300">
                <li className="flex gap-2"><span className="text-purple-400 font-bold">1.</span> Select your niche from the dropdown</li>
                <li className="flex gap-2"><span className="text-purple-400 font-bold">2.</span> Choose the tone that matches your personality</li>
                <li className="flex gap-2"><span className="text-purple-400 font-bold">3.</span> Select your main goal</li>
                <li className="flex gap-2"><span className="text-purple-400 font-bold">4.</span> Click Generate to receive 5 ready-to-use bios</li>
              </ol>
            </div>
            
            {/* Best Practices */}
            <div className="bg-slate-900/50 rounded-lg p-4">
              <h4 className="font-semibold text-green-400 mb-3">Best Practices</h4>
              <ul className="space-y-2 text-slate-300">
                <li className="flex gap-2"><span className="text-green-400">✔</span> Keep bio under 150 characters</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Choose tone aligned with your brand</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Update bio every 60 days</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Use 2-4 emojis max</li>
              </ul>
            </div>
          </div>
          
          {/* What Not To Do */}
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <h4 className="font-semibold text-red-400 mb-3">What Not To Do</h4>
            <ul className="grid md:grid-cols-2 gap-2 text-slate-300">
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not use copyrighted brand names</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not impersonate celebrities</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not include misleading claims</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Avoid too many emojis</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default function InstagramBioGenerator() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  
  // Form state
  const [selectedNiche, setSelectedNiche] = useState('');
  const [selectedTone, setSelectedTone] = useState('');
  const [selectedGoal, setSelectedGoal] = useState('');
  
  // Results
  const [generatedBios, setGeneratedBios] = useState([]);
  const [creditsUsed, setCreditsUsed] = useState(0);
  const [remainingCredits, setRemainingCredits] = useState(0);
  
  // Fetch config on mount
  useEffect(() => {
    fetchConfig();
  }, []);
  
  const fetchConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/instagram-bio-generator/config`, {
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
    if (!selectedNiche || !selectedTone || !selectedGoal) {
      toast.error('Please complete all selections');
      return;
    }
    
    setGenerating(true);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/instagram-bio-generator/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          niche: selectedNiche,
          tone: selectedTone,
          goal: selectedGoal
        })
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setGeneratedBios(data.bios);
        setCreditsUsed(data.credits_used);
        setRemainingCredits(data.remaining_credits);
        setStep(5); // Show results
        toast.success(`Generated ${data.bios.length} bios!`);
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (error) {
      console.error('Generation error:', error);
      toast.error('Failed to generate bios');
    } finally {
      setGenerating(false);
    }
  };
  
  const copyBio = async (bio, index) => {
    try {
      await navigator.clipboard.writeText(bio);
      setCopiedIndex(index);
      toast.success('Bio copied to clipboard!');
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  };
  
  const copyAllBios = async () => {
    try {
      const allBios = generatedBios.map((b, i) => `Bio ${i + 1}:\n${b.bio}`).join('\n\n');
      await navigator.clipboard.writeText(allBios);
      toast.success('All bios copied!');
    } catch (error) {
      toast.error('Failed to copy');
    }
  };
  
  const downloadBios = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/instagram-bio-generator/download`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(generatedBios.map(b => b.bio))
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        // Create download
        const blob = new Blob([data.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Downloaded! (1 credit used)');
      } else {
        toast.error(data.detail || 'Download failed');
      }
    } catch (error) {
      toast.error('Download failed');
    }
  };
  
  const resetGenerator = () => {
    setStep(1);
    setSelectedNiche('');
    setSelectedTone('');
    setSelectedGoal('');
    setGeneratedBios([]);
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full text-pink-400 text-sm mb-4">
            <Instagram className="w-4 h-4" />
            <span>Instagram Bio Generator</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Create Your Perfect Instagram Bio
          </h1>
          <p className="text-slate-400">
            Generate 5 optimized bios with CTAs and emojis • {config?.creditCost || 5} credits
          </p>
        </div>
        
        {/* User Manual */}
        <UserManual />
        
        {/* Main Card */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 md:p-8">
          {step < 5 && (
            <>
              <StepIndicator currentStep={step} totalSteps={4} />
              
              {/* Step 1: Select Niche */}
              {step === 1 && (
                <div className="space-y-6" data-testid="step-niche">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-purple-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <User className="w-8 h-8 text-purple-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Select Your Niche</h2>
                    <p className="text-slate-400">Choose the category that best describes your content</p>
                  </div>
                  
                  <div className="max-w-md mx-auto">
                    <select
                      value={selectedNiche}
                      onChange={(e) => setSelectedNiche(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                      data-testid="niche-select"
                    >
                      <option value="">Select a niche...</option>
                      {config?.niches?.map((niche) => (
                        <option key={niche} value={niche}>{niche}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="flex justify-center">
                    <button
                      onClick={() => selectedNiche && setStep(2)}
                      disabled={!selectedNiche}
                      className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
                      data-testid="next-step-1"
                    >
                      Continue <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
              
              {/* Step 2: Select Tone */}
              {step === 2 && (
                <div className="space-y-6" data-testid="step-tone">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-pink-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <Palette className="w-8 h-8 text-pink-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Select Your Tone</h2>
                    <p className="text-slate-400">Choose the personality that matches your brand</p>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl mx-auto">
                    {config?.tones?.map((tone) => (
                      <button
                        key={tone}
                        onClick={() => setSelectedTone(tone)}
                        className={`p-4 rounded-xl border transition-all ${
                          selectedTone === tone
                            ? 'bg-pink-500/20 border-pink-500 text-pink-400'
                            : 'bg-slate-800/50 border-slate-700 text-slate-300 hover:border-slate-600'
                        }`}
                        data-testid={`tone-${tone.toLowerCase()}`}
                      >
                        {tone}
                      </button>
                    ))}
                  </div>
                  
                  <div className="flex justify-center gap-4">
                    <button
                      onClick={() => setStep(1)}
                      className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-all"
                    >
                      <ChevronLeft className="w-5 h-5" /> Back
                    </button>
                    <button
                      onClick={() => selectedTone && setStep(3)}
                      disabled={!selectedTone}
                      className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
                      data-testid="next-step-2"
                    >
                      Continue <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
              
              {/* Step 3: Select Goal */}
              {step === 3 && (
                <div className="space-y-6" data-testid="step-goal">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-green-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <Target className="w-8 h-8 text-green-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Select Your Goal</h2>
                    <p className="text-slate-400">What do you want your bio to achieve?</p>
                  </div>
                  
                  <div className="max-w-md mx-auto">
                    <select
                      value={selectedGoal}
                      onChange={(e) => setSelectedGoal(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                      data-testid="goal-select"
                    >
                      <option value="">Select a goal...</option>
                      {config?.goals?.map((goal) => (
                        <option key={goal} value={goal}>{goal}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="flex justify-center gap-4">
                    <button
                      onClick={() => setStep(2)}
                      className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-all"
                    >
                      <ChevronLeft className="w-5 h-5" /> Back
                    </button>
                    <button
                      onClick={() => selectedGoal && setStep(4)}
                      disabled={!selectedGoal}
                      className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
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
                      <Zap className="w-8 h-8 text-yellow-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Ready to Generate!</h2>
                    <p className="text-slate-400">Review your selections and generate your bios</p>
                  </div>
                  
                  {/* Summary */}
                  <div className="max-w-md mx-auto bg-slate-800/50 rounded-xl p-4 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Niche:</span>
                      <span className="text-white font-medium">{selectedNiche}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Tone:</span>
                      <span className="text-white font-medium">{selectedTone}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Goal:</span>
                      <span className="text-white font-medium">{selectedGoal}</span>
                    </div>
                    <div className="border-t border-slate-700 pt-3 flex justify-between items-center">
                      <span className="text-slate-400">Cost:</span>
                      <span className="text-green-400 font-bold">{config?.creditCost || 5} Credits</span>
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
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5" />
                          Generate 5 Bios
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
          
          {/* Step 5: Results */}
          {step === 5 && (
            <div className="space-y-6" data-testid="step-results">
              <div className="text-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-green-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Your Bios Are Ready!</h2>
                <p className="text-slate-400">
                  {creditsUsed} credits used • {remainingCredits} credits remaining
                </p>
              </div>
              
              {/* Action buttons */}
              <div className="flex justify-center gap-3 flex-wrap">
                <button
                  onClick={copyAllBios}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-all"
                  data-testid="copy-all-btn"
                >
                  <Copy className="w-4 h-4" /> Copy All (Free)
                </button>
                <button
                  onClick={downloadBios}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-all"
                  data-testid="download-btn"
                >
                  <Download className="w-4 h-4" /> Download TXT (+1 credit)
                </button>
                <button
                  onClick={resetGenerator}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all"
                  data-testid="generate-more-btn"
                >
                  <Sparkles className="w-4 h-4" /> Generate More
                </button>
              </div>
              
              {/* Bio cards */}
              <div className="space-y-4">
                {generatedBios.map((bioData, index) => (
                  <div 
                    key={index}
                    className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 hover:border-purple-500/50 transition-all"
                    data-testid={`bio-card-${index}`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <span className="text-sm text-purple-400 font-medium">Bio {index + 1}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">{bioData.character_count} chars</span>
                        <button
                          onClick={() => copyBio(bioData.bio, index)}
                          className={`p-2 rounded-lg transition-all ${
                            copiedIndex === index 
                              ? 'bg-green-500/20 text-green-400' 
                              : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                          }`}
                          data-testid={`copy-bio-${index}`}
                        >
                          {copiedIndex === index ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                    <pre className="text-white whitespace-pre-wrap font-sans text-sm leading-relaxed">
                      {bioData.bio}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Disclaimer */}
        <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-200">
              {config?.disclaimer || "This tool generates original generic bio templates. Do not use copyrighted brand names."}
            </p>
          </div>
        </div>
      </div>
      
      <HelpGuide pageId="instagram-bio-generator" />
    </div>
  );
}
