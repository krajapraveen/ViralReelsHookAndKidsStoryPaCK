import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Sparkles, Copy, Download, Loader2, Lock, X } from 'lucide-react';
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
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/demo-reel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        throw new Error('Generation failed');
      }

      const data = await response.json();
      setResult(data.output);
      
      // Mark demo as used
      localStorage.setItem(DEMO_KEY, 'true');
      setDemoUsed(true);
      
      toast.success('Reel script generated! Sign up for more.');
    } catch (error) {
      toast.error('Generation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const downloadJSON = () => {
    // Add watermark to downloaded content
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
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl text-slate-900">
            <Sparkles className="w-6 h-6 text-indigo-500" />
            Try Demo - Generate 1 Free Reel Script
          </DialogTitle>
        </DialogHeader>

        {demoUsed && !result ? (
          <div className="text-center py-12">
            <Lock className="w-16 h-16 mx-auto mb-4 text-slate-300" />
            <h3 className="text-xl font-bold mb-2">Demo Already Used</h3>
            <p className="text-slate-600 mb-6">
              You've already used your free demo. Sign up to generate unlimited reel scripts!
            </p>
            <Link to="/signup">
              <Button className="bg-indigo-500 hover:bg-indigo-600 text-white" data-testid="demo-signup-btn">
                Sign Up for Free (5 Credits)
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Form */}
            <div className="space-y-4">
              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 text-sm text-indigo-700">
                <Sparkles className="w-4 h-4 inline mr-1" />
                Free demo - No signup required! Get 1 reel script to try.
              </div>

              <form onSubmit={handleSubmit} className="space-y-4" data-testid="demo-reel-form">
                <div>
                  <Label htmlFor="demo-topic" className="text-slate-700">Topic *</Label>
                  <Textarea
                    id="demo-topic"
                    value={formData.topic}
                    onChange={(e) => setFormData({...formData, topic: e.target.value})}
                    placeholder="E.g., Morning routines of successful entrepreneurs"
                    required
                    rows={2}
                    className="bg-white border-slate-300 text-slate-900"
                    disabled={loading || demoUsed}
                    data-testid="demo-topic-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Niche</Label>
                    <Select 
                      value={formData.niche} 
                      onValueChange={(value) => setFormData({...formData, niche: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger data-testid="demo-niche-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Luxury">Luxury</SelectItem>
                        <SelectItem value="Relationships">Relationships</SelectItem>
                        <SelectItem value="Health">Health & Fitness</SelectItem>
                        <SelectItem value="Finance">Finance</SelectItem>
                        <SelectItem value="Tech">Technology</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Tone</Label>
                    <Select 
                      value={formData.tone} 
                      onValueChange={(value) => setFormData({...formData, tone: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Bold">Bold</SelectItem>
                        <SelectItem value="Calm">Calm</SelectItem>
                        <SelectItem value="Funny">Funny</SelectItem>
                        <SelectItem value="Emotional">Emotional</SelectItem>
                        <SelectItem value="Authority">Authority</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Duration</Label>
                    <Select 
                      value={formData.duration} 
                      onValueChange={(value) => setFormData({...formData, duration: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15s">15 seconds</SelectItem>
                        <SelectItem value="30s">30 seconds</SelectItem>
                        <SelectItem value="60s">60 seconds</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Language</Label>
                    <Select 
                      value={formData.language} 
                      onValueChange={(value) => setFormData({...formData, language: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="English">English</SelectItem>
                        <SelectItem value="Telugu">Telugu</SelectItem>
                        <SelectItem value="Hinglish">Hinglish</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Goal</Label>
                    <Select 
                      value={formData.goal} 
                      onValueChange={(value) => setFormData({...formData, goal: value})}
                      disabled={loading || demoUsed}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Followers">Gain Followers</SelectItem>
                        <SelectItem value="Leads">Generate Leads</SelectItem>
                        <SelectItem value="Sales">Drive Sales</SelectItem>
                        <SelectItem value="Awareness">Brand Awareness</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Audience</Label>
                    <Input
                      value={formData.audience}
                      onChange={(e) => setFormData({...formData, audience: e.target.value})}
                      placeholder="E.g., Young professionals"
                      disabled={loading || demoUsed}
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading || demoUsed}
                  className="w-full bg-indigo-500 hover:bg-indigo-600 text-white"
                  data-testid="demo-generate-btn"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Generate Free Reel Script
                    </>
                  )}
                </Button>
              </form>
            </div>

            {/* Result */}
            <div className="bg-slate-50 rounded-lg p-4 max-h-[500px] overflow-y-auto">
              {!result ? (
                <div className="text-center py-12 text-slate-500">
                  <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                  <p>Your reel script will appear here</p>
                </div>
              ) : (
                <div className="space-y-4" data-testid="demo-result">
                  {/* Watermark Banner */}
                  <div className="bg-purple-100 border border-purple-300 rounded-lg p-3 text-center">
                    <p className="text-purple-700 text-sm font-medium">
                      ⚡ Made with CreatorStudio AI - Demo Version
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => copyToClipboard(JSON.stringify(result, null, 2))} data-testid="demo-copy-btn">
                      <Copy className="w-4 h-4 mr-1" />
                      Copy
                    </Button>
                    <Button variant="outline" size="sm" onClick={downloadJSON} data-testid="demo-download-btn">
                      <Download className="w-4 h-4 mr-1" />
                      Download
                    </Button>
                  </div>

                  {/* Best Hook */}
                  {result.best_hook && (
                    <div className="bg-indigo-50 border-l-4 border-indigo-500 p-3">
                      <h4 className="font-bold text-sm mb-1">⭐ Best Hook</h4>
                      <p className="text-indigo-900 text-sm">{result.best_hook}</p>
                    </div>
                  )}

                  {/* Hooks */}
                  {result.hooks && (
                    <div>
                      <h4 className="font-bold text-sm mb-2">🎯 5 Hooks</h4>
                      <div className="space-y-1">
                        {result.hooks.slice(0, 3).map((hook, idx) => (
                          <p key={idx} className="text-sm bg-white p-2 rounded">{idx + 1}. {hook}</p>
                        ))}
                        <p className="text-xs text-slate-500 italic">+ 2 more hooks in full version</p>
                      </div>
                    </div>
                  )}

                  {/* Short Caption */}
                  {result.caption_short && (
                    <div>
                      <h4 className="font-bold text-sm mb-1">📝 Caption Preview</h4>
                      <p className="text-sm bg-white p-2 rounded">{result.caption_short.substring(0, 150)}...</p>
                    </div>
                  )}

                  {/* CTA to Sign Up */}
                  <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg p-4 text-white text-center">
                    <h4 className="font-bold mb-2">🚀 Like what you see?</h4>
                    <p className="text-sm mb-3 opacity-90">Sign up to unlock full scripts, hashtags, posting tips & more!</p>
                    <Link to="/signup">
                      <Button className="bg-white text-indigo-600 hover:bg-slate-100" data-testid="demo-cta-signup-btn">
                        Get 5 Free Credits
                      </Button>
                    </Link>
                  </div>

                  {/* Watermark Footer */}
                  <p className="text-xs text-center text-slate-400">
                    Demo content includes watermark. Remove by signing up.
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
