import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { generationAPI, creditAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Copy, Download, Loader2, ArrowLeft, Coins, AlertCircle } from 'lucide-react';

import ShareButton from '../components/ShareButton';

// Check if user is on free tier (never purchased)
const isFreeTierUser = () => {
  return localStorage.getItem('has_purchased') !== 'true';
};

export default function ReelGenerator() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [isFreeTier, setIsFreeTier] = useState(true);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    topic: '',
    niche: 'Luxury',
    tone: 'Bold',
    duration: '30s',
    language: 'English',
    goal: 'Followers',
    audience: 'General'
  });

  useEffect(() => {
    fetchCredits();
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await creditAPI.getBalance();
      setCredits(response.data.balance);
    } catch (error) {
      toast.error('Failed to load credits');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (credits < 1) {
      toast.error('Insufficient credits! Please buy more.');
      navigate('/app/billing');
      return;
    }

    setLoading(true);
    try {
      const response = await generationAPI.generateReel(formData);
      setResult(response.data.output);
      setCredits(credits - 1);
      toast.success('Reel script generated successfully!');
    } catch (error) {
      toast.error(error.response?.data?.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reel-script-${Date.now()}.json`;
    a.click();
    toast.success('Downloaded!');
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-500" />
              <span className="text-xl font-bold">Reel Generator</span>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-slate-100 rounded-full px-4 py-2">
            <Coins className="w-4 h-4 text-purple-500" />
            <span className="font-semibold">{credits} Credits</span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input Form */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-2xl font-bold mb-6">Generate Reel Script</h2>
            <form onSubmit={handleSubmit} className="space-y-6" data-testid="reel-form">
              <div>
                <Label htmlFor="topic">Topic *</Label>
                <Textarea
                  id="topic"
                  value={formData.topic}
                  onChange={(e) => setFormData({...formData, topic: e.target.value})}
                  placeholder="E.g., Morning routines of successful entrepreneurs"
                  required
                  rows={3}
                  className="bg-white"
                  data-testid="reel-topic-input"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="niche">Niche</Label>
                  <Select value={formData.niche} onValueChange={(value) => setFormData({...formData, niche: value})}>
                    <SelectTrigger data-testid="reel-niche-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Luxury">Luxury</SelectItem>
                      <SelectItem value="Relationships">Relationships</SelectItem>
                      <SelectItem value="Health">Health & Fitness</SelectItem>
                      <SelectItem value="Finance">Finance</SelectItem>
                      <SelectItem value="Tech">Technology</SelectItem>
                      <SelectItem value="Custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="tone">Tone</Label>
                  <Select value={formData.tone} onValueChange={(value) => setFormData({...formData, tone: value})}>
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

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="duration">Duration</Label>
                  <Select value={formData.duration} onValueChange={(value) => setFormData({...formData, duration: value})}>
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
                  <Label htmlFor="language">Language</Label>
                  <Select value={formData.language} onValueChange={(value) => setFormData({...formData, language: value})}>
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

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="goal">Goal</Label>
                  <Select value={formData.goal} onValueChange={(value) => setFormData({...formData, goal: value})}>
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
                  <Label htmlFor="audience">Audience</Label>
                  <Input
                    id="audience"
                    value={formData.audience}
                    onChange={(e) => setFormData({...formData, audience: e.target.value})}
                    placeholder="E.g., Young professionals"
                  />
                </div>
              </div>

              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-indigo-700">
                  <Coins className="w-4 h-4" />
                  <span className="font-medium">Cost: 1 credit</span>
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-500 hover:bg-indigo-600 text-white"
                data-testid="reel-generate-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Reel Script
                  </>
                )}
              </Button>
            </form>
          </div>

          {/* Result Display */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">Generated Script</h2>
              {result && (
                <div className="flex gap-2">
                  <ShareButton type="REEL" title={result.best_hook} preview={result.caption_short} />
                  <Button variant="outline" size="sm" onClick={() => copyToClipboard(JSON.stringify(result, null, 2))} data-testid="copy-result-btn">
                    <Copy className="w-4 h-4 mr-2" />
                    Copy All
                  </Button>
                  <Button variant="outline" size="sm" onClick={downloadJSON} data-testid="download-result-btn">
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                </div>
              )}
            </div>

            {!result ? (
              <div className="text-center py-12 text-slate-500">
                <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                <p>Your generated reel script will appear here</p>
              </div>
            ) : (
              <div className="space-y-6" data-testid="reel-result">
                {/* Hooks */}
                <div>
                  <h3 className="font-bold text-lg mb-3">🎯 5 Hooks</h3>
                  <div className="space-y-2">
                    {result.hooks?.map((hook, idx) => (
                      <div key={idx} className="bg-slate-50 p-3 rounded-lg flex items-start gap-2">
                        <span className="font-semibold text-indigo-600">{idx + 1}.</span>
                        <span>{hook}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Best Hook */}
                {result.best_hook && (
                  <div className="bg-indigo-50 border-l-4 border-indigo-500 p-4">
                    <h3 className="font-bold text-lg mb-2">⭐ Best Hook</h3>
                    <p className="text-indigo-900">{result.best_hook}</p>
                  </div>
                )}

                {/* Script Scenes */}
                {result.script?.scenes && (
                  <div>
                    <h3 className="font-bold text-lg mb-3">🎬 Script</h3>
                    <div className="space-y-3">
                      {result.script.scenes.map((scene, idx) => (
                        <div key={idx} className="border border-slate-200 rounded-lg p-4">
                          <div className="font-semibold text-purple-600 mb-2">{scene.time}</div>
                          <div className="space-y-2">
                            {scene.on_screen_text && (
                              <div>
                                <span className="text-xs font-semibold text-slate-500">ON-SCREEN:</span>
                                <p className="text-sm">{scene.on_screen_text}</p>
                              </div>
                            )}
                            {scene.voiceover && (
                              <div>
                                <span className="text-xs font-semibold text-slate-500">VOICEOVER:</span>
                                <p className="text-sm">{scene.voiceover}</p>
                              </div>
                            )}
                            {scene.broll && scene.broll.length > 0 && (
                              <div>
                                <span className="text-xs font-semibold text-slate-500">B-ROLL:</span>
                                <p className="text-sm text-slate-600">{scene.broll.join(', ')}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* CTA */}
                {result.script?.cta && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="font-bold mb-2">📢 Call to Action</h3>
                    <p>{result.script.cta}</p>
                  </div>
                )}

                {/* Captions */}
                <div className="space-y-3">
                  {result.caption_short && (
                    <div>
                      <h3 className="font-bold mb-2">📝 Short Caption</h3>
                      <p className="text-sm bg-slate-50 p-3 rounded-lg">{result.caption_short}</p>
                    </div>
                  )}
                  {result.caption_long && (
                    <div>
                      <h3 className="font-bold mb-2">📄 Long Caption</h3>
                      <p className="text-sm bg-slate-50 p-3 rounded-lg whitespace-pre-wrap">{result.caption_long}</p>
                    </div>
                  )}
                </div>

                {/* Hashtags */}
                {result.hashtags && (
                  <div>
                    <h3 className="font-bold mb-2">#️⃣ Hashtags</h3>
                    <div className="flex flex-wrap gap-2">
                      {result.hashtags.map((tag, idx) => (
                        <span key={idx} className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Posting Tips */}
                {result.posting_tips && (
                  <div>
                    <h3 className="font-bold mb-2">💡 Posting Tips</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-slate-600">
                      {result.posting_tips.map((tip, idx) => (
                        <li key={idx}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}