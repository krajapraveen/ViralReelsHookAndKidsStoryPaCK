import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Sparkles, Image, ArrowLeft, Coins, Loader2, Download,
  Wand2, Settings, Clock, Check, AlertTriangle, RefreshCw,
  Wallet, XCircle, AlertCircle
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api, { walletAPI } from '../utils/api';
import sseManager from '../utils/sse';
import { v4 as uuidv4 } from 'uuid';
import HelpGuide from '../components/HelpGuide';

export default function TextToImage() {
  const [searchParams] = useSearchParams();
  const [wallet, setWallet] = useState({ balanceCredits: 0, reservedCredits: 0, availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [addWatermark, setAddWatermark] = useState(true);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [templates, setTemplates] = useState([]);
  
  // Job state
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
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

  // Poll for job status - Using SSE utility for smarter polling
  useEffect(() => {
    let cleanup;
    if (currentJob && ['QUEUED', 'RUNNING'].includes(jobStatus)) {
      cleanup = sseManager.subscribeToJob(currentJob, (job) => {
        setJobStatus(job.status);
        setProgress({
          step: job.progress || 0,
          message: job.progressMessage || `Status: ${job.status}`
        });
        
        if (job.status === 'SUCCEEDED') {
          setResult({
            jobId: job.jobId,
            outputUrls: job.outputUrls,
            creditsUsed: job.costCredits
          });
          setGenerating(false);
          // Refresh wallet
          walletAPI.getWallet().then(res => setWallet(res.data));
          toast.success('Image generated successfully!');
        } else if (job.status === 'FAILED') {
          setGenerating(false);
          toast.error(job.errorMessage || 'Generation failed');
          walletAPI.getWallet().then(res => setWallet(res.data));
        }
      });
    }
    return () => cleanup && cleanup();
  }, [currentJob, jobStatus]);

  const fetchData = async () => {
    try {
      const [walletRes, pricingRes, templatesRes] = await Promise.all([
        walletAPI.getWallet(),
        walletAPI.getPricing(),
        api.get('/api/genstudio/templates')
      ]);
      setWallet(walletRes.data);
      setPricing(pricingRes.data.pricing);
      setTemplates(templatesRes.data.templates);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const pollJobStatus = useCallback(async () => {
    if (!currentJob) return;
    
    try {
      const response = await walletAPI.getJob(currentJob);
      const job = response.data;
      setJobStatus(job.status);
      setProgress({
        step: job.progress || 0,
        message: job.progressMessage || `Status: ${job.status}`
      });
      
      if (job.status === 'SUCCEEDED') {
        setResult({
          jobId: job.jobId,
          outputUrls: job.outputUrls,
          creditsUsed: job.costCredits
        });
        setGenerating(false);
        // Refresh wallet
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        toast.success('Image generated successfully!');
      } else if (job.status === 'FAILED') {
        setGenerating(false);
        toast.error(job.errorMessage || 'Generation failed');
        // Refresh wallet (credits should be released)
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  }, [currentJob]);

  const handleTemplateSelect = (templateId) => {
    setSelectedTemplate(templateId);
    const template = templates.find(t => t.id === templateId);
    if (template) {
      const match = template.prompt.match(/\{(\w+)\}/);
      if (match) {
        setPrompt(`[Enter your ${match[1]} here]`);
      }
      toast.info(`Template: ${template.name}`, { description: 'Modify the prompt below' });
    }
  };

  const cost = pricing.TEXT_TO_IMAGE?.baseCredits || 10;
  const canAfford = wallet.availableCredits >= cost;

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    if (!consentConfirmed) {
      toast.error('Please confirm you have rights/consent for this content');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${cost} credits. You have ${wallet.availableCredits} available.`);
      navigate('/app/billing');
      return;
    }

    setGenerating(true);
    setProgress({ step: 5, message: 'Creating job...' });
    setResult(null);
    setCurrentJob(null);
    setJobStatus(null);

    try {
      // Create job using the new pipeline
      const idempotencyKey = uuidv4();
      const response = await walletAPI.createJob({
        jobType: 'TEXT_TO_IMAGE',
        inputData: {
          prompt: prompt.trim(),
          negative_prompt: negativePrompt.trim() || null,
          aspect_ratio: aspectRatio,
          template_id: selectedTemplate || null,
          add_watermark: addWatermark
        }
      }, idempotencyKey);

      if (response.data.success) {
        setCurrentJob(response.data.jobId);
        setJobStatus('QUEUED');
        setProgress({ step: 10, message: 'Job queued. Waiting for processing...' });
        
        // Update wallet (credits reserved)
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        
        toast.info('Job created! Processing...', { description: `Cost: ${response.data.costCredits} credits` });
      }
    } catch (error) {
      console.error('Generation error:', error);
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
      setGenerating(false);
      setProgress({ step: 0, message: '' });
    }
  };

  const handleCancelJob = async () => {
    if (!currentJob || !['QUEUED', 'PENDING'].includes(jobStatus)) return;
    
    try {
      await walletAPI.cancelJob(currentJob);
      setGenerating(false);
      setCurrentJob(null);
      setJobStatus(null);
      // Refresh wallet
      const walletRes = await walletAPI.getWallet();
      setWallet(walletRes.data);
      toast.info('Job cancelled. Credits released.');
    } catch (error) {
      toast.error('Failed to cancel job');
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
              {/* Wallet Display */}
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2" data-testid="wallet-balance">
                <Wallet className="w-4 h-4 text-purple-400" />
                <div className="flex flex-col">
                  <span className="font-bold text-white text-sm">{wallet.availableCredits}</span>
                  <span className="text-xs text-slate-500">available</span>
                </div>
                {wallet.reservedCredits > 0 && (
                  <div className="border-l border-slate-600 pl-2 ml-2">
                    <span className="text-xs text-yellow-400">{wallet.reservedCredits} held</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Insufficient Credits Warning */}
        {!canAfford && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div>
              <p className="text-sm font-medium text-red-300">Insufficient Credits</p>
              <p className="text-xs text-red-400">Need {cost} credits, you have {wallet.availableCredits} available.</p>
            </div>
            <Link to="/app/billing" className="ml-auto">
              <Button size="sm" className="bg-red-600 hover:bg-red-700">Buy Credits</Button>
            </Link>
          </div>
        )}

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
                data-testid="prompt-input"
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
                  data-testid="consent-checkbox"
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
              disabled={generating || !consentConfirmed || !prompt.trim() || !canAfford}
              className="w-full h-14 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-lg font-semibold disabled:opacity-50"
              data-testid="generate-btn"
            >
              {generating ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {progress.message || 'Processing...'}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Generate Image ({cost} credits)
                </span>
              )}
            </Button>

            {/* Progress/Job Status */}
            {generating && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div className="flex justify-between text-sm text-slate-400 mb-2">
                  <span className="flex items-center gap-2">
                    {jobStatus === 'QUEUED' && <Clock className="w-4 h-4 text-yellow-400" />}
                    {jobStatus === 'RUNNING' && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                    {progress.message}
                  </span>
                  <span>{progress.step}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
                    style={{ width: `${progress.step}%` }}
                  />
                </div>
                {jobStatus === 'QUEUED' && (
                  <div className="mt-3 flex justify-end">
                    <Button variant="ghost" size="sm" onClick={handleCancelJob} className="text-red-400 hover:text-red-300">
                      <XCircle className="w-4 h-4 mr-1" />
                      Cancel Job
                    </Button>
                  </div>
                )}
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
                      data-testid="generated-image"
                    />
                  </div>
                  
                  <div className="mt-4 space-y-3">
                    {/* Expiry Notice */}
                    <div className="flex items-center gap-2 text-yellow-400 text-sm bg-yellow-500/10 rounded-lg px-3 py-2">
                      <Clock className="w-4 h-4" />
                      <span>⚠️ SECURITY: Download within 3 MINUTES before auto-deletion!</span>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        onClick={() => handleDownload(result.outputUrls[0], `genstudio-${result.jobId}.png`)}
                        className="flex-1 bg-green-600 hover:bg-green-700"
                        data-testid="download-btn"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Image
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => { setResult(null); setPrompt(''); setCurrentJob(null); setJobStatus(null); }}
                        className="border-slate-600 text-slate-300"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        New
                      </Button>
                    </div>
                    
                    <p className="text-xs text-slate-500 text-center">
                      Credits used: {result.creditsUsed} • Available: {wallet.availableCredits}
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
      
      {/* Help Guide */}
      <HelpGuide pageId="genstudio-text-to-image" />
    </div>
  );
}
