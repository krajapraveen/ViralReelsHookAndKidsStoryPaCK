import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Sparkles, Image, ArrowLeft, Coins, Loader2, Download,
  Wand2, Settings, Clock, Check, AlertTriangle, RefreshCw
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api from '../utils/api';

export default function TextToImage() {
  const [searchParams] = useSearchParams();
  const [credits, setCredits] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [addWatermark, setAddWatermark] = useState(true);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState({ step: 0, message: '' });
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
    const templateId = searchParams.get('template');
    if (templateId) {
      setSelectedTemplate(templateId);
    }
  }, [searchParams]);

  const fetchData = async () => {
    try {
      const [creditsRes, templatesRes] = await Promise.all([
        api.get('/api/credits/balance'),
        api.get('/api/genstudio/templates')
      ]);
      setCredits(creditsRes.data.balance);
      setTemplates(templatesRes.data.templates);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleTemplateSelect = (templateId) => {
    setSelectedTemplate(templateId);
    const template = templates.find(t => t.id === templateId);
    if (template) {
      // Extract placeholder for user input
      const match = template.prompt.match(/\{(\w+)\}/);
      if (match) {
        setPrompt(`[Enter your ${match[1]} here]`);
      }
      toast.info(`Template: ${template.name}`, { description: 'Modify the prompt below' });
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    if (!consentConfirmed) {
      toast.error('Please confirm you have rights/consent for this content');
      return;
    }

    if (credits < 10) {
      toast.error('Need 10 credits for image generation');
      return;
    }

    setGenerating(true);
    setProgress({ step: 1, message: 'Preparing your request...' });
    setResult(null);

    try {
      setProgress({ step: 2, message: 'Generating image with AI...' });
      
      const response = await api.post('/api/genstudio/text-to-image', {
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || null,
        aspect_ratio: aspectRatio,
        template_id: selectedTemplate || null,
        add_watermark: addWatermark,
        consent_confirmed: consentConfirmed
      });

      setProgress({ step: 3, message: 'Image generated!' });
      setCredits(response.data.remainingCredits);
      setResult(response.data);
      toast.success('Image generated successfully!');

    } catch (error) {
      console.error('Generation error:', error);
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
    } finally {
      setGenerating(false);
      setProgress({ step: 0, message: '' });
    }
  };

  const handleDownload = async (url, filename) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        if (response.status === 410) {
          toast.error('Download link expired');
          return;
        }
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'generated-image.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      toast.success('Image downloaded!');
    } catch (error) {
      toast.error('Download failed');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/gen-studio" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Image className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Text → Image</h1>
                  <p className="text-xs text-slate-400">Generate images from text</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <span className="font-bold text-white">{credits}</span>
                <span className="text-slate-400 text-sm">credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Input Panel */}
          <div className="space-y-6">
            {/* Template Selection */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Wand2 className="w-4 h-4 text-purple-400" />
                Quick Templates
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => handleTemplateSelect(template.id)}
                    className={`text-left p-3 rounded-lg border transition-all ${
                      selectedTemplate === template.id 
                        ? 'border-purple-500 bg-purple-500/10' 
                        : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                    }`}
                  >
                    <p className="text-sm font-medium text-white">{template.name}</p>
                    <p className="text-xs text-slate-500">{template.category}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Prompt Input */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Prompt</h3>
              <Textarea
                placeholder="Describe the image you want to create... Be specific about style, colors, composition, and mood."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="min-h-[120px] bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
              <p className="text-xs text-slate-500 mt-2">{prompt.length}/2000 characters</p>
            </div>

            {/* Negative Prompt */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Negative Prompt (Optional)</h3>
              <Textarea
                placeholder="Things to avoid: blurry, low quality, text, watermark..."
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                className="min-h-[80px] bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
            </div>

            {/* Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4 text-slate-400" />
                Settings
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-400 mb-2 block">Aspect Ratio</label>
                  <Select value={aspectRatio} onValueChange={setAspectRatio}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1:1">1:1 (Square)</SelectItem>
                      <SelectItem value="16:9">16:9 (Landscape)</SelectItem>
                      <SelectItem value="9:16">9:16 (Portrait/Mobile)</SelectItem>
                      <SelectItem value="4:3">4:3 (Standard)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">Add Watermark</p>
                    <p className="text-xs text-slate-500">Required for free plan</p>
                  </div>
                  <button
                    onClick={() => setAddWatermark(!addWatermark)}
                    className={`w-12 h-6 rounded-full transition-colors ${addWatermark ? 'bg-purple-500' : 'bg-slate-600'}`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${addWatermark ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              </div>
            </div>

            {/* Consent Checkbox */}
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentConfirmed}
                  onChange={(e) => setConsentConfirmed(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-800 text-purple-500"
                />
                <div>
                  <p className="text-sm font-medium text-yellow-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Content Rights Confirmation
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    I confirm that I have the rights/consent for this content and it does not contain any prohibited material (celebrity likenesses, deepfakes, etc.)
                  </p>
                </div>
              </label>
            </div>

            {/* Generate Button */}
            <Button
              onClick={handleGenerate}
              disabled={generating || !consentConfirmed || !prompt.trim()}
              className="w-full h-14 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-lg font-semibold"
            >
              {generating ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {progress.message}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Generate Image (10 credits)
                </span>
              )}
            </Button>

            {/* Progress Bar */}
            {generating && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div className="flex justify-between text-sm text-slate-400 mb-2">
                  <span>{progress.message}</span>
                  <span>{Math.min(progress.step * 33, 100)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(progress.step * 33, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Right: Result Panel */}
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 min-h-[500px] flex flex-col">
              <h3 className="text-sm font-semibold text-white mb-4">Generated Image</h3>
              
              {result ? (
                <div className="flex-1 flex flex-col">
                  <div className="relative flex-1 bg-slate-800 rounded-lg overflow-hidden">
                    <img 
                      src={`${process.env.REACT_APP_BACKEND_URL}${result.outputUrls[0]}`}
                      alt="Generated"
                      className="w-full h-full object-contain"
                    />
                  </div>
                  
                  <div className="mt-4 space-y-3">
                    {/* Expiry Notice */}
                    <div className="flex items-center gap-2 text-yellow-400 text-sm bg-yellow-500/10 rounded-lg px-3 py-2">
                      <Clock className="w-4 h-4" />
                      <span>Download within 15 minutes before it expires!</span>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        onClick={() => handleDownload(result.outputUrls[0], `genstudio-${result.jobId}.png`)}
                        className="flex-1 bg-green-600 hover:bg-green-700"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Image
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => { setResult(null); setPrompt(''); }}
                        className="border-slate-600 text-slate-300"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        New
                      </Button>
                    </div>
                    
                    <p className="text-xs text-slate-500 text-center">
                      Credits used: {result.creditsUsed} • Remaining: {result.remainingCredits}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-center">
                  <div>
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
                      <Image className="w-10 h-10 text-slate-600" />
                    </div>
                    <p className="text-slate-400">Your generated image will appear here</p>
                    <p className="text-xs text-slate-500 mt-2">Enter a prompt and click Generate</p>
                  </div>
                </div>
              )}
            </div>

            {/* Tips */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">💡 Tips for Better Results</h3>
              <ul className="text-xs text-slate-400 space-y-2">
                <li>• Be specific about style, lighting, and composition</li>
                <li>• Include artistic references (e.g., "studio photography", "watercolor style")</li>
                <li>• Use negative prompts to avoid unwanted elements</li>
                <li>• Choose the right aspect ratio for your use case</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
