import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Upload, Wand2, BookOpen, FileText, Loader2, Download, Eye, Trash2, Sparkles, Settings, ChevronRight, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';

export default function ComicStorybook() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [styles, setStyles] = useState({});
  const [layouts, setLayouts] = useState({});
  const [pricing, setPricing] = useState({});
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [lastGenerationId, setLastGenerationId] = useState(null);
  
  // Input state
  const [inputMethod, setInputMethod] = useState('text');
  const [storyText, setStoryText] = useState('');
  const [storyFile, setStoryFile] = useState(null);
  const [storyFileName, setStoryFileName] = useState('');
  
  // Settings
  const [title, setTitle] = useState('My Comic Story');
  const [author, setAuthor] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('storybook');
  const [pageCount, setPageCount] = useState(20);
  const [panelsPerPage, setPanelsPerPage] = useState('auto');
  
  // Preview
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Job state
  const [currentJob, setCurrentJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [pollingInterval, setPollingInterval] = useState(null);

  useEffect(() => {
    fetchCredits();
    fetchStyles();
    fetchHistory();
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await api.get('/api/credits/balance');
      setCredits(response.data.credits);
    } catch (error) {
      console.error('Failed to fetch credits');
    }
  };

  const fetchStyles = async () => {
    try {
      const response = await api.get('/api/comic-storybook/styles');
      setStyles(response.data.styles || {});
      setLayouts(response.data.layouts || {});
      setPricing(response.data.pricing || {});
    } catch (error) {
      console.error('Failed to fetch styles');
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await api.get('/api/comic-storybook/history?size=10');
      setHistory(response.data.jobs || []);
    } catch (error) {
      console.error('Failed to fetch history');
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) {
        toast.error('Please upload a .txt or .md file');
        e.target.value = '';
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File too large. Max 5MB.');
        e.target.value = '';
        return;
      }
      
      // CRITICAL: Clear previous state when new file uploaded
      setCurrentJob(null);
      setPreview(null);
      stopPolling();
      toastShownRef.current = {};
      
      setStoryFile(file);
      setStoryFileName(file.name);
      
      // Read file content for preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setStoryText(e.target.result);
      };
      reader.readAsText(file);
    }
  };

  // Clear file and reset state
  const clearStoryFile = () => {
    setStoryFile(null);
    setStoryFileName('');
    setStoryText('');
    setCurrentJob(null);
    setPreview(null);
    stopPolling();
    toastShownRef.current = {};
    
    const fileInput = document.getElementById('story-file-input');
    if (fileInput) fileInput.value = '';
  };

  const parseStoryPreview = async () => {
    if (!storyText.trim() && !storyFile) {
      toast.error('Please enter or upload a story');
      return;
    }
    
    setPreviewLoading(true);
    try {
      const formData = new FormData();
      if (inputMethod === 'file' && storyFile) {
        formData.append('story_file', storyFile);
      } else {
        formData.append('story_text', storyText);
      }
      formData.append('target_pages', pageCount.toString());
      
      const response = await api.post('/api/comic-storybook/parse-story', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setPreview(response.data);
      toast.success(`Story parsed: ${response.data.scene_count} scenes detected`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to parse story');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Track toast shown state using ref to prevent infinite loops
  const toastShownRef = React.useRef({});
  const pollingRef = React.useRef(null);
  const isPollingRef = React.useRef(false);

  const stopPolling = useCallback(() => {
    isPollingRef.current = false;
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [pollingInterval]);

  const pollJobStatus = useCallback(async (jobId) => {
    // Prevent polling if already stopped
    if (!isPollingRef.current) return;
    
    try {
      const response = await api.get(`/api/comic-storybook/job/${jobId}`);
      setCurrentJob(response.data);
      
      if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED') {
        // Stop polling immediately
        stopPolling();
        setLoading(false);
        fetchCredits();
        fetchHistory();
        
        // Only show toast once using ref (not state)
        if (!toastShownRef.current[jobId]) {
          toastShownRef.current[jobId] = true;
          if (response.data.status === 'COMPLETED') {
            toast.success('Comic story book generated successfully!');
            // Show rating modal after successful generation
            setLastGenerationId(jobId);
            setTimeout(() => setShowRatingModal(true), 2000);
          } else {
            toast.error('Generation failed. Please try again.');
          }
        }
      }
    } catch (error) {
      console.error('Poll error:', error);
    }
  }, [stopPolling]);

  const generateStorybook = async () => {
    if (!storyText.trim() && !storyFile) {
      toast.error('Please enter or upload a story');
      return;
    }
    
    const cost = preview?.estimated_credits || pricing[`${pageCount}_pages`] || 90;
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      return;
    }
    
    // CRITICAL: Clear previous results
    setCurrentJob(null);
    stopPolling();
    setLoading(true);
    toastShownRef.current = {};
    
    try {
      const formData = new FormData();
      if (inputMethod === 'file' && storyFile) {
        formData.append('story_file', storyFile, storyFile.name);
      } else {
        formData.append('story_text', storyText);
      }
      formData.append('style', selectedStyle);
      formData.append('page_count', pageCount.toString());
      formData.append('panels_per_page', panelsPerPage);
      formData.append('title', title);
      formData.append('author', author);
      formData.append('timestamp', Date.now().toString()); // Prevent caching
      
      const response = await api.post('/api/comic-storybook/generate', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Cache-Control': 'no-cache'
        }
      });
      
      setCurrentJob({ id: response.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Story book generation started!');
      
      // Start fresh polling
      isPollingRef.current = true;
      const interval = setInterval(() => pollJobStatus(response.data.jobId), 3000);
      pollingRef.current = interval;
      setPollingInterval(interval);
      
    } catch (error) {
      setLoading(false);
      toast.error(error.response?.data?.detail || 'Failed to generate story book');
    }
  };

  const deleteJob = async (jobId) => {
    try {
      await api.delete(`/api/comic-storybook/job/${jobId}`);
      toast.success('Deleted');
      fetchHistory();
      if (currentJob?.id === jobId) setCurrentJob(null);
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const calculateCredits = () => {
    if (pageCount <= 10) return 50;
    if (pageCount <= 20) return 90;
    if (pageCount <= 30) return 120;
    if (pageCount <= 40) return 150;
    return 180;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-amber-900/20 to-slate-900">
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
                <BookOpen className="w-6 h-6 text-amber-400" />
                <h1 className="text-2xl font-bold text-white">Comic Story Book</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-full px-4 py-2">
                <span className="text-amber-300 font-medium">{credits.toLocaleString()} Credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Create Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-400">Comic Story Book</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Transform your stories into beautiful 10-50 page comic books. Upload or write your story, choose a style, and download as PDF.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Input & Settings */}
          <div className="space-y-6">
            {/* Story Input */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-amber-400" />
                Your Story
              </h3>
              
              {/* Input Method Toggle */}
              <div className="flex gap-2 mb-4">
                <Button 
                  variant={inputMethod === 'text' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setInputMethod('text')}
                  className={inputMethod === 'text' ? 'bg-amber-600' : ''}
                >
                  Write Story
                </Button>
                <Button 
                  variant={inputMethod === 'file' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setInputMethod('file')}
                  className={inputMethod === 'file' ? 'bg-amber-600' : ''}
                >
                  Upload File
                </Button>
              </div>

              {inputMethod === 'text' ? (
                <Textarea
                  placeholder="Write or paste your story here... Include scene descriptions, dialogues, and action sequences for best results."
                  value={storyText}
                  onChange={(e) => setStoryText(e.target.value)}
                  className="bg-slate-700 border-slate-600 min-h-64"
                  data-testid="story-text-input"
                />
              ) : (
                <div 
                  className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-amber-500 transition-colors cursor-pointer"
                  onClick={() => document.getElementById('story-file-upload').click()}
                >
                  {storyFileName ? (
                    <div className="flex items-center justify-center gap-2">
                      <CheckCircle className="w-6 h-6 text-green-400" />
                      <span className="text-green-400">{storyFileName}</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-12 h-12 mx-auto text-slate-500 mb-4" />
                      <p className="text-slate-400">Click to upload .txt or .md file</p>
                      <p className="text-sm text-slate-500">Max 5MB</p>
                    </>
                  )}
                </div>
              )}
              <input
                id="story-file-upload"
                type="file"
                accept=".txt,.md"
                className="hidden"
                onChange={handleFileChange}
                data-testid="story-file-input"
              />
              
              {storyText && (
                <p className="text-sm text-slate-400 mt-2">
                  Word count: {storyText.split(/\s+/).filter(w => w).length}
                </p>
              )}
            </div>

            {/* Book Settings */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Settings className="w-5 h-5 text-amber-400" />
                Book Settings
              </h3>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Book Title</label>
                    <Input
                      placeholder="My Comic Story"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="bg-slate-700 border-slate-600"
                      data-testid="book-title-input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Author</label>
                    <Input
                      placeholder="Your name"
                      value={author}
                      onChange={(e) => setAuthor(e.target.value)}
                      className="bg-slate-700 border-slate-600"
                      data-testid="book-author-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-2">Comic Style</label>
                  <Select value={selectedStyle} onValueChange={setSelectedStyle}>
                    <SelectTrigger className="bg-slate-700 border-slate-600" data-testid="style-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700 max-h-64">
                      {Object.entries(styles).map(([key, style]) => (
                        <SelectItem key={key} value={key} className="text-white">
                          {style.name} - {style.description}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Page Count: {pageCount}</label>
                    <input
                      type="range"
                      min="10"
                      max="50"
                      step="5"
                      value={pageCount}
                      onChange={(e) => setPageCount(parseInt(e.target.value))}
                      className="w-full accent-amber-500"
                      data-testid="page-count-slider"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>10</span>
                      <span>30</span>
                      <span>50</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Panels per Page</label>
                    <Select value={panelsPerPage} onValueChange={setPanelsPerPage}>
                      <SelectTrigger className="bg-slate-700 border-slate-600">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="auto" className="text-white">Auto-detect</SelectItem>
                        <SelectItem value="2" className="text-white">2 panels</SelectItem>
                        <SelectItem value="4" className="text-white">4 panels</SelectItem>
                        <SelectItem value="6" className="text-white">6 panels</SelectItem>
                        <SelectItem value="9" className="text-white">9 panels</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>

            {/* Preview Button */}
            <Button 
              onClick={parseStoryPreview}
              disabled={previewLoading || (!storyText.trim() && !storyFile)}
              variant="outline"
              className="w-full"
              data-testid="preview-btn"
            >
              {previewLoading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Analyzing Story...</>
              ) : (
                <><Eye className="w-4 h-4 mr-2" /> Preview Story Structure</>
              )}
            </Button>

            {/* Preview Results */}
            {preview && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                <h4 className="text-amber-300 font-medium mb-2">Story Analysis</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">Scenes detected:</span>
                    <span className="text-white ml-2">{preview.scene_count}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Recommended pages:</span>
                    <span className="text-white ml-2">{preview.recommended_pages}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Word count:</span>
                    <span className="text-white ml-2">{preview.word_count}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Estimated credits:</span>
                    <span className="text-amber-300 ml-2">{preview.estimated_credits}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Generate Button */}
            <Button 
              onClick={generateStorybook}
              disabled={loading || (!storyText.trim() && !storyFile)}
              className="w-full py-6 text-lg bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700"
              data-testid="generate-storybook-btn"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Generating Story Book...</>
              ) : (
                <><BookOpen className="w-5 h-5 mr-2" /> Generate {pageCount}-Page Comic Book ({calculateCredits()} credits)</>
              )}
            </Button>
          </div>

          {/* Right: Progress & Results */}
          <div className="space-y-6">
            {/* Current Job Progress */}
            {currentJob && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-xl font-bold text-white mb-4">Generation Progress</h3>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      currentJob.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                      currentJob.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                      currentJob.status === 'QUEUED' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-yellow-500/20 text-yellow-400 animate-pulse'
                    }`}>
                      {currentJob.status === 'PROCESSING' ? 'GENERATING...' : currentJob.status}
                    </span>
                    {currentJob.currentPage && (
                      <span className="text-amber-400 font-medium">Page {currentJob.currentPage} / {currentJob.pageCount || pageCount}</span>
                    )}
                  </div>
                  
                  {/* Enhanced Progress Bar */}
                  {(currentJob.status === 'PROCESSING' || currentJob.status === 'QUEUED') && (
                    <div className="space-y-3 bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-400">Progress</span>
                        <span className="text-amber-400 font-bold">{currentJob.progress || 0}%</span>
                      </div>
                      <div className="relative h-4 bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className="absolute top-0 left-0 h-full bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 rounded-full transition-all duration-500"
                          style={{ width: `${currentJob.progress || 0}%` }}
                        />
                      </div>
                      
                      {/* Step Indicators */}
                      <div className="flex justify-between text-xs text-slate-500 mt-2">
                        <span className={currentJob.progress >= 5 ? 'text-green-400' : ''}>Read</span>
                        <span className={currentJob.progress >= 15 ? 'text-green-400' : ''}>Parse</span>
                        <span className={currentJob.progress >= 50 ? 'text-green-400' : ''}>Illustrate</span>
                        <span className={currentJob.progress >= 90 ? 'text-green-400' : ''}>Layout</span>
                        <span className={currentJob.progress >= 95 ? 'text-green-400' : ''}>PDF</span>
                        <span className={currentJob.progress >= 100 ? 'text-green-400' : ''}>Done</span>
                      </div>
                      
                      <p className="text-sm text-slate-400 text-center mt-2 flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                        {currentJob.progressMessage || 'Processing...'}
                      </p>
                    </div>
                  )}
                  
                  {currentJob.status === 'COMPLETED' && currentJob.pdfUrl && (
                    <div className="space-y-3">
                      <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                        <div className="flex items-center gap-2 text-green-400">
                          <CheckCircle className="w-5 h-5" />
                          <span className="font-medium">Your comic story book is ready!</span>
                        </div>
                      </div>
                      
                      <Button 
                        className="w-full bg-amber-600 hover:bg-amber-700"
                        onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${currentJob.pdfUrl}`, '_blank')}
                        data-testid="download-pdf-btn"
                      >
                        <Download className="w-4 h-4 mr-2" /> Download PDF ({currentJob.pageCount || pageCount} pages)
                      </Button>
                    </div>
                  )}
                  
                  {/* Preview Pages */}
                  {currentJob.pages && currentJob.pages.length > 0 && (
                    <div>
                      <h4 className="text-sm text-slate-400 mb-2">Preview (first 3 pages)</h4>
                      <div className="grid grid-cols-3 gap-2">
                        {currentJob.pages.slice(0, 3).map((page, i) => (
                          <div key={i} className="rounded-lg overflow-hidden border border-slate-600 bg-slate-700">
                            {page.panels?.[0]?.imageUrl && (
                              <img 
                                src={page.panels[0].imageUrl.startsWith('http') ? page.panels[0].imageUrl : `${process.env.REACT_APP_BACKEND_URL}${page.panels[0].imageUrl}`} 
                                alt={`Page ${i+1}`} 
                                className="w-full aspect-[3/4] object-cover"
                              />
                            )}
                            <div className="p-1 text-center text-xs text-slate-400">Page {page.page_number}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!currentJob && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <div className="text-center py-12 text-slate-400">
                  <BookOpen className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                  <p className="text-lg">Your comic story book will appear here</p>
                  <p className="text-sm mt-2">Enter your story and click generate to create a PDF comic book</p>
                </div>
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-lg font-bold text-white mb-4">Recent Story Books</h3>
                <div className="space-y-3">
                  {history.slice(0, 5).map((job) => (
                    <div key={job.id} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <BookOpen className={`w-5 h-5 ${job.status === 'COMPLETED' ? 'text-green-400' : 'text-slate-400'}`} />
                        <div>
                          <p className="text-white font-medium truncate max-w-48">{job.title}</p>
                          <p className="text-xs text-slate-400">{job.pageCount} pages • {job.style}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {job.status === 'COMPLETED' && job.pdfUrl && (
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${job.pdfUrl}`, '_blank')}
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => deleteJob(job.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Info Box */}
            <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700">
              <h4 className="text-white font-medium mb-2">Tips for Best Results</h4>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• Write clear scene descriptions for better panel generation</li>
                <li>• Include dialogue in quotes for speech bubbles</li>
                <li>• Use paragraph breaks to separate scenes</li>
                <li>• Avoid copyrighted characters (Marvel, Disney, etc.)</li>
                <li>• Longer stories work better with more pages</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Copyright Notice */}
        <div className="mt-8 bg-slate-800/30 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400 text-center">
            ⚠️ <strong>Copyright Policy:</strong> All generated content is original and copyright-free. 
            Stories referencing copyrighted characters (Marvel, DC, Disney, etc.) are not allowed.
          </p>
        </div>
      </main>
    </div>
  );
}
