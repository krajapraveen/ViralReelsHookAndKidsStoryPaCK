import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Sparkles, Copy, Download, Loader2, Lock, X, LogIn, ArrowRight } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';

const DEMO_KEY = 'creatorstudio_demo_used';

export default function DemoReelGenerator({ isOpen, onClose }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [demoUsed, setDemoUsed] = useState(() => localStorage.getItem(DEMO_KEY) === 'true');

  const [formData, setFormData] = useState({
    topic: '',
    niche: 'Luxury',
    tone: 'Bold',
    duration: '30s',
    language: 'English',
    goal: 'Followers',
    audience: 'General'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (demoUsed) {
      toast.error('You have already used your free demo. Sign up for more!');
      return;
    }

    if (!formData.topic.trim()) {
      toast.error('Please enter a topic');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/demo/reel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Generation failed');
      }

      const data = await response.json();
      setResult(data.result);
      
      // Mark demo as used
      localStorage.setItem(DEMO_KEY, 'true');
      setDemoUsed(true);
      
      toast.success('Reel script generated! Sign up for full access.');
    } catch (error) {
      toast.error(error.message || 'Generation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const downloadJSON = () => {
    const watermarkedResult = {
      ...result,
      watermark: '⚡ Generated with CreatorStudio AI - Get full access at creatorstudio.ai',
      demo_version: true
    };
    const blob = new Blob([JSON.stringify(watermarkedResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `demo-reel-script-${Date.now()}.json`;
    a.click();
    toast.success('Downloaded with watermark!');
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 border border-indigo-500/30 shadow-2xl">
        <DialogHeader className="border-b border-indigo-500/20 pb-4">
          <DialogTitle className="flex items-center gap-3 text-2xl text-white">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="block">Try Free Demo</span>
              <span className="text-sm font-normal text-indigo-300">Generate 1 Free Reel Script</span>
            </div>
          </DialogTitle>
        </DialogHeader>

        {demoUsed && !result ? (
          <div className="text-center py-12">
            <div className="w-20 h-20 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-6">
              <Lock className="w-10 h-10 text-indigo-400" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-3">Demo Already Used</h3>
            <p className="text-slate-400 mb-8 max-w-md mx-auto">
              You've already used your free demo. Sign up now to generate unlimited reel scripts and get 100 free credits!
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/signup">
                <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white px-8 py-6 text-lg rounded-xl" data-testid="demo-signup-btn">
                  <Sparkles className="w-5 h-5 mr-2" />
                  Sign Up Free (100 Credits)
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="outline" className="border-indigo-500/50 text-indigo-300 hover:bg-indigo-500/10 px-8 py-6 text-lg rounded-xl" data-testid="demo-login-btn">
                  <LogIn className="w-5 h-5 mr-2" />
                  Login to Account
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid lg:grid-cols-2 gap-6 pt-4">
            {/* Form */}
            <div className="space-y-5">
              <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-4 text-sm text-indigo-200 flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-indigo-100">Free Demo - No Signup Required!</p>
                  <p className="text-indigo-300 mt-1">Generate 1 reel script to experience our AI-powered content creation.</p>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5" data-testid="demo-reel-form">
                <div>
                  <Label htmlFor="demo-topic" className="text-white text-sm font-medium mb-2 block">
                    Topic <span className="text-red-400">*</span>
                  </Label>
                  <Textarea
                    id="demo-topic"
                    value={formData.topic}
                    onChange={(e) => setFormData({...formData, topic: e.target.value})}
                    placeholder="E.g., Morning routines of successful entrepreneurs"
                    required
                    rows={3}
                    className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-indigo-500/20 rounded-xl resize-none"
                    disabled={loading || demoUsed}
                    data-testid="demo-topic-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-white text-sm font-medium mb-2 block">Niche</Label>
                    <Select 
                      value={formData.niche} 
                      onValueChange={(value) => setFormData({...formData, niche: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white focus:ring-indigo-500/20 rounded-xl h-11" data-testid="demo-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="Luxury" className="text-white hover:bg-indigo-500/20">Luxury</SelectItem>
                        <SelectItem value="Relationships" className="text-white hover:bg-indigo-500/20">Relationships</SelectItem>
                        <SelectItem value="Health" className="text-white hover:bg-indigo-500/20">Health & Fitness</SelectItem>
                        <SelectItem value="Finance" className="text-white hover:bg-indigo-500/20">Finance</SelectItem>
                        <SelectItem value="Tech" className="text-white hover:bg-indigo-500/20">Technology</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-white text-sm font-medium mb-2 block">Tone</Label>
                    <Select 
                      value={formData.tone} 
                      onValueChange={(value) => setFormData({...formData, tone: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white focus:ring-indigo-500/20 rounded-xl h-11">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="Bold" className="text-white hover:bg-indigo-500/20">Bold</SelectItem>
                        <SelectItem value="Calm" className="text-white hover:bg-indigo-500/20">Calm</SelectItem>
                        <SelectItem value="Funny" className="text-white hover:bg-indigo-500/20">Funny</SelectItem>
                        <SelectItem value="Emotional" className="text-white hover:bg-indigo-500/20">Emotional</SelectItem>
                        <SelectItem value="Authority" className="text-white hover:bg-indigo-500/20">Authority</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-white text-sm font-medium mb-2 block">Duration</Label>
                    <Select 
                      value={formData.duration} 
                      onValueChange={(value) => setFormData({...formData, duration: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white focus:ring-indigo-500/20 rounded-xl h-11">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="15s" className="text-white hover:bg-indigo-500/20">15 seconds</SelectItem>
                        <SelectItem value="30s" className="text-white hover:bg-indigo-500/20">30 seconds</SelectItem>
                        <SelectItem value="60s" className="text-white hover:bg-indigo-500/20">60 seconds</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-white text-sm font-medium mb-2 block">Language</Label>
                    <Select 
                      value={formData.language} 
                      onValueChange={(value) => setFormData({...formData, language: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white focus:ring-indigo-500/20 rounded-xl h-11">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="English" className="text-white hover:bg-indigo-500/20">English</SelectItem>
                        <SelectItem value="Telugu" className="text-white hover:bg-indigo-500/20">Telugu</SelectItem>
                        <SelectItem value="Hinglish" className="text-white hover:bg-indigo-500/20">Hinglish</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-white text-sm font-medium mb-2 block">Goal</Label>
                    <Select 
                      value={formData.goal} 
                      onValueChange={(value) => setFormData({...formData, goal: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white focus:ring-indigo-500/20 rounded-xl h-11">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="Followers" className="text-white hover:bg-indigo-500/20">Gain Followers</SelectItem>
                        <SelectItem value="Leads" className="text-white hover:bg-indigo-500/20">Generate Leads</SelectItem>
                        <SelectItem value="Sales" className="text-white hover:bg-indigo-500/20">Drive Sales</SelectItem>
                        <SelectItem value="Awareness" className="text-white hover:bg-indigo-500/20">Brand Awareness</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-white text-sm font-medium mb-2 block">Target Audience</Label>
                    <Input
                      value={formData.audience}
                      onChange={(e) => setFormData({...formData, audience: e.target.value})}
                      placeholder="E.g., Young professionals"
                      className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-indigo-500/20 rounded-xl h-11"
                      disabled={loading || demoUsed}
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading || demoUsed}
                  className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white py-6 text-lg rounded-xl shadow-lg shadow-indigo-500/25 transition-all hover:scale-[1.02]"
                  data-testid="demo-generate-btn"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Generating Your Script...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 mr-2" />
                      Generate Free Reel Script
                    </>
                  )}
                </Button>

                {/* Login Link */}
                <div className="text-center pt-2">
                  <p className="text-slate-400 text-sm">
                    Already have an account?{' '}
                    <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1">
                      Login here <ArrowRight className="w-3 h-3" />
                    </Link>
                  </p>
                </div>
              </form>
            </div>

            {/* Result */}
            <div className="bg-slate-800/30 rounded-2xl p-5 max-h-[550px] overflow-y-auto border border-slate-700/50">
              {!result ? (
                <div className="text-center py-16 text-slate-400">
                  <div className="w-16 h-16 bg-slate-700/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="w-8 h-8 text-slate-500" />
                  </div>
                  <p className="text-lg font-medium text-slate-300">Your Script Preview</p>
                  <p className="text-sm text-slate-500 mt-2">Enter a topic and click generate to see your reel script</p>
                </div>
              ) : (
                <div className="space-y-4" data-testid="demo-result">
                  {/* Watermark Banner */}
                  <div className="bg-gradient-to-r from-purple-500/20 to-indigo-500/20 border border-purple-500/30 rounded-xl p-3 text-center">
                    <p className="text-purple-200 text-sm font-medium">
                      ⚡ Made with CreatorStudio AI - Demo Version
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => copyToClipboard(JSON.stringify(result, null, 2))} className="border-slate-600 text-slate-300 hover:bg-slate-700" data-testid="demo-copy-btn">
                      <Copy className="w-4 h-4 mr-1" />
                      Copy
                    </Button>
                    <Button variant="outline" size="sm" onClick={downloadJSON} className="border-slate-600 text-slate-300 hover:bg-slate-700" data-testid="demo-download-btn">
                      <Download className="w-4 h-4 mr-1" />
                      Download
                    </Button>
                  </div>

                  {/* Best Hook */}
                  {result.best_hook && (
                    <div className="bg-indigo-500/10 border-l-4 border-indigo-500 rounded-r-xl p-4">
                      <h4 className="font-bold text-sm mb-2 text-indigo-300">⭐ Best Hook</h4>
                      <p className="text-white text-sm">{result.best_hook}</p>
                    </div>
                  )}

                  {/* Hooks */}
                  {result.hooks && (
                    <div>
                      <h4 className="font-bold text-sm mb-3 text-white">🎯 5 Hooks</h4>
                      <div className="space-y-2">
                        {result.hooks.slice(0, 3).map((hook, idx) => (
                          <p key={idx} className="text-sm bg-slate-700/30 p-3 rounded-lg text-slate-200">{idx + 1}. {hook}</p>
                        ))}
                        <p className="text-xs text-slate-500 italic px-1">+ 2 more hooks in full version</p>
                      </div>
                    </div>
                  )}

                  {/* Short Caption */}
                  {result.caption_short && (
                    <div>
                      <h4 className="font-bold text-sm mb-2 text-white">📝 Caption Preview</h4>
                      <p className="text-sm bg-slate-700/30 p-3 rounded-lg text-slate-200">{result.caption_short.substring(0, 150)}...</p>
                    </div>
                  )}

                  {/* CTA to Sign Up */}
                  <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-5 text-white text-center">
                    <h4 className="font-bold text-lg mb-2">🚀 Love This Result?</h4>
                    <p className="text-sm mb-4 text-indigo-100">Sign up to unlock full scripts, hashtags, posting tips & unlimited generations!</p>
                    <div className="flex flex-col sm:flex-row gap-3 justify-center">
                      <Link to="/signup">
                        <Button className="bg-white text-indigo-600 hover:bg-indigo-50 w-full sm:w-auto" data-testid="demo-cta-signup-btn">
                          <Sparkles className="w-4 h-4 mr-2" />
                          Get 100 Free Credits
                        </Button>
                      </Link>
                      <Link to="/login">
                        <Button variant="outline" className="border-white/50 text-white hover:bg-white/10 w-full sm:w-auto">
                          <LogIn className="w-4 h-4 mr-2" />
                          Login
                        </Button>
                      </Link>
                    </div>
                  </div>

                  {/* Watermark Footer */}
                  <p className="text-xs text-center text-slate-500">
                    Demo content includes watermark. Sign up to remove.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
