import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
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
  Zap,
  Package
} from 'lucide-react';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';

const API_URL = process.env.REACT_APP_BACKEND_URL;

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
          <span className="font-semibold text-white">How to Use AI Comment Reply Bank</span>
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
                <li className="flex gap-2"><span className="text-purple-400 font-bold">1.</span> Paste the comment you received</li>
                <li className="flex gap-2"><span className="text-purple-400 font-bold">2.</span> Choose reply mode (Single or Full Pack)</li>
                <li className="flex gap-2"><span className="text-purple-400 font-bold">3.</span> Click Generate</li>
                <li className="flex gap-2"><span className="text-purple-400 font-bold">4.</span> Copy & post your favorite reply</li>
              </ol>
            </div>
            
            {/* Best Practices */}
            <div className="bg-slate-900/50 rounded-lg p-4">
              <h4 className="font-semibold text-green-400 mb-3">Best Practices</h4>
              <ul className="space-y-2 text-slate-300">
                <li className="flex gap-2"><span className="text-green-400">✔</span> Match reply tone to your brand</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Avoid overusing sales replies</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Keep engagement natural</li>
                <li className="flex gap-2"><span className="text-green-400">✔</span> Use emojis moderately</li>
              </ul>
            </div>
          </div>
          
          {/* What Not To Do */}
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <h4 className="font-semibold text-red-400 mb-3">What Not To Do</h4>
            <ul className="grid md:grid-cols-2 gap-2 text-slate-300">
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not paste copyrighted slogans</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not impersonate celebrities</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not generate misleading claims</li>
              <li className="flex gap-2"><span className="text-red-400">✗</span> Do not reply aggressively</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default function CommentReplyBank() {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  
  // Form state
  const [comment, setComment] = useState('');
  const [mode, setMode] = useState('single');
  
  // Results
  const [intentDetected, setIntentDetected] = useState('');
  const [replies, setReplies] = useState([]);
  const [creditsUsed, setCreditsUsed] = useState(0);
  const [remainingCredits, setRemainingCredits] = useState(0);
  
  // Fetch config on mount
  useEffect(() => {
    fetchConfig();
  }, []);
  
  const fetchConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/comment-reply-bank/config`, {
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
    if (!comment.trim()) {
      toast.error('Please paste a comment first');
      return;
    }
    
    setGenerating(true);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/comment-reply-bank/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ comment, mode })
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setIntentDetected(data.intent_detected);
        setReplies(data.replies);
        setCreditsUsed(data.credits_used);
        setRemainingCredits(data.remaining_credits);
        setStep(3);
        toast.success(`Generated ${data.replies.length} replies!`);
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (error) {
      console.error('Generation error:', error);
      toast.error('Failed to generate replies');
    } finally {
      setGenerating(false);
    }
  };
  
  const copyReply = async (reply, index) => {
    try {
      await navigator.clipboard.writeText(reply);
      setCopiedIndex(index);
      toast.success('Reply copied!');
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  };
  
  const copyAllReplies = async () => {
    try {
      const all = replies.map(r => `[${r.type.toUpperCase()}]\n${r.reply}`).join('\n\n');
      await navigator.clipboard.writeText(all);
      toast.success('All replies copied!');
    } catch (error) {
      toast.error('Failed to copy');
    }
  };
  
  const resetGenerator = () => {
    setStep(1);
    setComment('');
    setMode('single');
    setReplies([]);
    setIntentDetected('');
  };
  
  const getIntentColor = (intent) => {
    const colors = {
      praise: 'text-green-400 bg-green-500/20',
      question: 'text-blue-400 bg-blue-500/20',
      objection: 'text-amber-400 bg-amber-500/20',
      negative: 'text-red-400 bg-red-500/20',
      pricing: 'text-emerald-400 bg-emerald-500/20',
      collaboration: 'text-purple-400 bg-purple-500/20',
      generic: 'text-slate-400 bg-slate-500/20'
    };
    return colors[intent] || colors.generic;
  };
  
  const getTypeColor = (type) => {
    const colors = {
      funny: 'border-yellow-500 bg-yellow-500/10',
      smart: 'border-blue-500 bg-blue-500/10',
      sales: 'border-green-500 bg-green-500/10',
      short: 'border-purple-500 bg-purple-500/10'
    };
    return colors[type] || 'border-slate-500 bg-slate-500/10';
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
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/20 rounded-full text-blue-400 text-sm mb-4">
            <MessageSquare className="w-4 h-4" />
            <span>AI Comment Reply Bank</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Reply to Comments Instantly
          </h1>
          <p className="text-slate-400">
            High-engagement responses for any comment type
          </p>
        </div>
        
        {/* User Manual */}
        <UserManual />
        
        {/* Main Card */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 md:p-8">
          
          {/* Step 1 & 2: Input Comment and Choose Mode */}
          {step < 3 && (
            <div className="space-y-6">
              {/* Comment Input */}
              <div data-testid="comment-input-section">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Paste the comment you received
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value.slice(0, 500))}
                  placeholder="Your content is amazing! How did you learn this?"
                  className="w-full h-32 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  data-testid="comment-textarea"
                />
                <div className="flex justify-between mt-1">
                  <span className="text-xs text-slate-500">Max 500 characters</span>
                  <span className={`text-xs ${comment.length > 450 ? 'text-amber-400' : 'text-slate-500'}`}>
                    {comment.length}/500
                  </span>
                </div>
              </div>
              
              {/* Mode Selection */}
              <div data-testid="mode-selection">
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Choose Reply Mode
                </label>
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Single Mode */}
                  <button
                    onClick={() => setMode('single')}
                    className={`p-5 rounded-xl border-2 transition-all text-left ${
                      mode === 'single'
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                    data-testid="mode-single"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Zap className={`w-6 h-6 ${mode === 'single' ? 'text-blue-400' : 'text-slate-400'}`} />
                      <h3 className="font-bold text-white">Single Reply Set</h3>
                    </div>
                    <p className="text-slate-400 text-sm mb-2">4 replies (Funny, Smart, Sales, Short)</p>
                    <span className="inline-block text-sm font-semibold text-blue-400">5 Credits</span>
                  </button>
                  
                  {/* Full Pack Mode */}
                  <button
                    onClick={() => setMode('full_pack')}
                    className={`p-5 rounded-xl border-2 transition-all text-left ${
                      mode === 'full_pack'
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                    data-testid="mode-full-pack"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Package className={`w-6 h-6 ${mode === 'full_pack' ? 'text-purple-400' : 'text-slate-400'}`} />
                      <h3 className="font-bold text-white">Full Reply Pack</h3>
                    </div>
                    <p className="text-slate-400 text-sm mb-2">12 replies (3 of each type)</p>
                    <span className="inline-block text-sm font-semibold text-purple-400">15 Credits</span>
                  </button>
                </div>
              </div>
              
              {/* Generate Button */}
              <div className="flex justify-center">
                <button
                  onClick={handleGenerate}
                  disabled={generating || !comment.trim()}
                  className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all"
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
                      Generate Replies
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
          
          {/* Step 3: Results */}
          {step === 3 && (
            <div className="space-y-6" data-testid="results-section">
              {/* Header */}
              <div className="text-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-green-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Your Replies Are Ready!</h2>
                <p className="text-slate-400">
                  {creditsUsed} credits used • {remainingCredits} remaining
                </p>
                
                {/* Intent Badge */}
                <div className="mt-4">
                  <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${getIntentColor(intentDetected)}`}>
                    Intent Detected: {intentDetected.charAt(0).toUpperCase() + intentDetected.slice(1)}
                  </span>
                </div>
              </div>
              
              {/* Original Comment */}
              <div className="bg-slate-800/50 rounded-lg p-4">
                <p className="text-xs text-slate-500 mb-1">Original Comment:</p>
                <p className="text-slate-300 text-sm italic">"{comment}"</p>
              </div>
              
              {/* Action Buttons */}
              <div className="flex justify-center gap-3 flex-wrap">
                <button
                  onClick={copyAllReplies}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-all"
                  data-testid="copy-all-btn"
                >
                  <Copy className="w-4 h-4" /> Copy All
                </button>
                <button
                  onClick={resetGenerator}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all"
                  data-testid="new-comment-btn"
                >
                  <MessageSquare className="w-4 h-4" /> New Comment
                </button>
              </div>
              
              {/* Reply Cards */}
              <div className="grid md:grid-cols-2 gap-4">
                {replies.map((reply, index) => (
                  <div 
                    key={index}
                    className={`border rounded-xl p-4 hover:shadow-lg transition-all ${getTypeColor(reply.type)}`}
                    data-testid={`reply-card-${index}`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <span className="text-sm font-semibold text-white uppercase tracking-wide">
                        {reply.type} Reply
                      </span>
                      <button
                        onClick={() => copyReply(reply.reply, index)}
                        className={`p-2 rounded-lg transition-all ${
                          copiedIndex === index 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                        }`}
                        data-testid={`copy-reply-${index}`}
                      >
                        {copiedIndex === index ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-white text-sm leading-relaxed">{reply.reply}</p>
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
              These replies are generated as templates. Always personalize before posting and ensure they match your brand voice.
            </p>
          </div>
        </div>
      </div>
      
      <HelpGuide pageId="comment-reply-bank" />
    </div>
  );
}
