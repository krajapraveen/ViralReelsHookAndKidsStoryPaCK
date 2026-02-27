import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';
import { 
  Book, ArrowLeft, Download, Image, Palette, Settings,
  Wand2, Loader2, CheckCircle, AlertCircle, Upload,
  RefreshCw, Trash2, FileText, Star, Sparkles, Eye,
  Lock, Wallet, ChevronRight, ChevronDown, BookOpen,
  Pencil, Eraser, ZoomIn, ZoomOut, RotateCcw, Printer
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Slider } from '../components/ui/slider';
import api, { walletAPI } from '../utils/api';

// PDF Generation - Client-side using jsPDF
// Will be dynamically imported

export default function ColoringBookGenerator() {
  const [stories, setStories] = useState([]);
  const [selectedStory, setSelectedStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [wallet, setWallet] = useState({ balanceCredits: 0, availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  
  // Mode: 'placeholder' (DIY) or 'photo' (image upload)
  const [mode, setMode] = useState('placeholder');
  
  // Scene editor state
  const [scenes, setScenes] = useState([]);
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);
  const [sceneImages, setSceneImages] = useState({});
  const [processedImages, setProcessedImages] = useState({});
  
  // Processing settings
  const [outlineStrength, setOutlineStrength] = useState(50); // 0-100
  const [invertColors, setInvertColors] = useState(false);
  const [processing, setProcessing] = useState(false);
  
  // Export settings
  const [exportConfig, setExportConfig] = useState({
    pageCount: 10,
    includeActivityPages: false,
    personalizedCover: false,
    childName: '',
    dedication: '',
    paperSize: 'A4'
  });
  
  // Export state
  const [exporting, setExporting] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [previewPage, setPreviewPage] = useState(0);
  
  // Web Worker ref for image processing
  const workerRef = useRef(null);
  const canvasRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchInitialData();
    initializeWorker();
    
    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
      }
    };
  }, []);

  const initializeWorker = () => {
    // Create web worker for image processing
    const workerCode = `
      self.onmessage = function(e) {
        const { imageData, strength, invert, action } = e.data;
        
        if (action === 'processImage') {
          const processed = processToOutline(imageData, strength, invert);
          self.postMessage({ result: processed, action: 'processed' });
        }
      };
      
      function processToOutline(imageData, strength, invert) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        
        // Create output array
        const output = new Uint8ClampedArray(data.length);
        
        // Step 1: Convert to grayscale
        const gray = new Uint8ClampedArray(width * height);
        for (let i = 0; i < data.length; i += 4) {
          const idx = i / 4;
          gray[idx] = Math.round(0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2]);
        }
        
        // Step 2: Apply Gaussian blur (3x3)
        const blurred = new Uint8ClampedArray(width * height);
        const kernel = [1, 2, 1, 2, 4, 2, 1, 2, 1];
        const kernelSum = 16;
        
        for (let y = 1; y < height - 1; y++) {
          for (let x = 1; x < width - 1; x++) {
            let sum = 0;
            let k = 0;
            for (let ky = -1; ky <= 1; ky++) {
              for (let kx = -1; kx <= 1; kx++) {
                sum += gray[(y + ky) * width + (x + kx)] * kernel[k++];
              }
            }
            blurred[y * width + x] = sum / kernelSum;
          }
        }
        
        // Step 3: Sobel edge detection
        const edges = new Uint8ClampedArray(width * height);
        const sobelX = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
        const sobelY = [-1, -2, -1, 0, 0, 0, 1, 2, 1];
        
        for (let y = 1; y < height - 1; y++) {
          for (let x = 1; x < width - 1; x++) {
            let gx = 0, gy = 0;
            let k = 0;
            for (let ky = -1; ky <= 1; ky++) {
              for (let kx = -1; kx <= 1; kx++) {
                const val = blurred[(y + ky) * width + (x + kx)];
                gx += val * sobelX[k];
                gy += val * sobelY[k];
                k++;
              }
            }
            edges[y * width + x] = Math.min(255, Math.sqrt(gx * gx + gy * gy));
          }
        }
        
        // Step 4: Apply threshold based on strength
        const threshold = 255 - (strength * 2.55); // 0-255 range
        
        for (let i = 0; i < edges.length; i++) {
          let val = edges[i] > threshold ? 0 : 255; // Black lines on white
          if (invert) val = 255 - val;
          
          const idx = i * 4;
          output[idx] = val;
          output[idx + 1] = val;
          output[idx + 2] = val;
          output[idx + 3] = 255;
        }
        
        return new ImageData(output, width, height);
      }
    `;
    
    const blob = new Blob([workerCode], { type: 'application/javascript' });
    workerRef.current = new Worker(URL.createObjectURL(blob));
    
    workerRef.current.onmessage = (e) => {
      if (e.data.action === 'processed') {
        handleProcessedImage(e.data.result);
      }
    };
  };

  const fetchInitialData = async () => {
    try {
      const [walletRes, pricingRes, storiesRes] = await Promise.all([
        walletAPI.getWallet(),
        api.get('/api/coloring-book/pricing'),
        api.get('/api/coloring-book/stories')
      ]);
      
      setWallet(walletRes.data);
      setPricing(pricingRes.data.creditPricing || {});
      setStories(storiesRes.data.stories || []);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load coloring book data');
    } finally {
      setLoading(false);
    }
  };

  const handleStorySelect = async (storyId) => {
    try {
      const response = await api.get(`/api/coloring-book/stories/${storyId}`);
      const story = response.data;
      setSelectedStory(story);
      
      // Initialize scenes
      const storyScenes = story.scenes || [];
      setScenes(storyScenes);
      setSceneImages({});
      setProcessedImages({});
      setActiveSceneIndex(0);
      
      toast.success(`Selected: ${story.title}`);
    } catch (error) {
      toast.error('Failed to load story');
    }
  };

  const handleImageUpload = (sceneIndex, file) => {
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file');
      return;
    }
    
    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image too large. Max 10MB allowed.');
      return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.createElement('img');
      img.onload = () => {
        // Resize if too large
        const maxDim = 1200;
        let width = img.width;
        let height = img.height;
        
        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = (height / width) * maxDim;
            width = maxDim;
          } else {
            width = (width / height) * maxDim;
            height = maxDim;
          }
        }
        
        // Store original image
        setSceneImages(prev => ({
          ...prev,
          [sceneIndex]: { src: e.target.result, width, height, originalWidth: img.width, originalHeight: img.height }
        }));
        
        // Auto-process
        processImage(sceneIndex, img, width, height);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  };

  const processImage = (sceneIndex, img, width, height) => {
    setProcessing(true);
    
    // Create canvas to get image data
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, width, height);
    
    const imageData = ctx.getImageData(0, 0, width, height);
    
    // Store current scene index for callback
    workerRef.current.currentSceneIndex = sceneIndex;
    
    // Send to worker
    workerRef.current.postMessage({
      imageData,
      strength: outlineStrength,
      invert: invertColors,
      action: 'processImage'
    });
  };

  const handleProcessedImage = (processedImageData) => {
    const sceneIndex = workerRef.current.currentSceneIndex;
    
    // Create canvas and draw processed image
    const canvas = document.createElement('canvas');
    canvas.width = processedImageData.width;
    canvas.height = processedImageData.height;
    const ctx = canvas.getContext('2d');
    ctx.putImageData(processedImageData, 0, 0);
    
    const dataUrl = canvas.toDataURL('image/png');
    
    setProcessedImages(prev => ({
      ...prev,
      [sceneIndex]: dataUrl
    }));
    
    setProcessing(false);
    toast.success('Image processed!');
  };

  const regenerateOutline = (sceneIndex) => {
    const imgData = sceneImages[sceneIndex];
    if (!imgData) return;
    
    const img = document.createElement('img');
    img.onload = () => {
      processImage(sceneIndex, img, imgData.width, imgData.height);
    };
    img.src = imgData.src;
  };

  const clearSceneImage = (sceneIndex) => {
    setSceneImages(prev => {
      const newState = { ...prev };
      delete newState[sceneIndex];
      return newState;
    });
    setProcessedImages(prev => {
      const newState = { ...prev };
      delete newState[sceneIndex];
      return newState;
    });
  };

  const calculateCost = () => {
    let cost = pricing.BASE_EXPORT || 5;
    if (exportConfig.includeActivityPages) cost += pricing.ACTIVITY_PAGES || 2;
    if (exportConfig.personalizedCover) cost += pricing.PERSONALIZED_COVER || 1;
    if (exportConfig.pageCount > 10) {
      cost += Math.ceil((exportConfig.pageCount - 10) * (pricing.PER_EXTRA_PAGE || 0.5));
    }
    return cost;
  };

  const canAfford = wallet.availableCredits >= calculateCost();

  const handleExport = async () => {
    if (!selectedStory) {
      toast.error('Please select a story first');
      return;
    }
    
    if (!canAfford) {
      toast.error(`Need ${calculateCost()} credits. You have ${wallet.availableCredits}.`);
      navigate('/app/billing');
      return;
    }
    
    setExporting(true);
    
    try {
      // Import jsPDF dynamically
      const { jsPDF } = await import('jspdf');
      
      const isA4 = exportConfig.paperSize === 'A4';
      const pageWidth = isA4 ? 210 : 215.9;
      const pageHeight = isA4 ? 297 : 279.4;
      
      const doc = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: isA4 ? 'a4' : 'letter'
      });
      
      const margin = 15;
      const contentWidth = pageWidth - (margin * 2);
      const contentHeight = pageHeight - (margin * 2);
      
      let currentPage = 1;
      
      // Helper to add footer
      const addFooter = () => {
        doc.setFontSize(8);
        doc.setTextColor(150);
        doc.text(`Page ${currentPage}`, pageWidth / 2, pageHeight - 8, { align: 'center' });
        doc.text('CreatorStudio AI', pageWidth - margin, pageHeight - 8, { align: 'right' });
      };
      
      // COVER PAGE
      doc.setFontSize(32);
      doc.setTextColor(30);
      doc.text(selectedStory.title || 'My Coloring Book', pageWidth / 2, 60, { align: 'center' });
      
      if (exportConfig.personalizedCover && exportConfig.childName) {
        doc.setFontSize(18);
        doc.setTextColor(100);
        doc.text(`A Special Book for ${exportConfig.childName}`, pageWidth / 2, 80, { align: 'center' });
      }
      
      // Draw cover decorations (simple shapes)
      doc.setDrawColor(200);
      doc.setLineWidth(2);
      doc.rect(margin, margin, contentWidth, contentHeight);
      
      // Stars decoration
      doc.setFontSize(24);
      doc.text('', pageWidth / 2 - 40, 120);
      doc.text('', pageWidth / 2, 120);
      doc.text('', pageWidth / 2 + 40, 120);
      
      if (exportConfig.dedication) {
        doc.setFontSize(12);
        doc.setTextColor(100);
        const dedicationLines = doc.splitTextToSize(exportConfig.dedication, contentWidth - 40);
        doc.text(dedicationLines, pageWidth / 2, pageHeight - 60, { align: 'center' });
      }
      
      addFooter();
      
      // SCENE PAGES
      for (let i = 0; i < scenes.length && currentPage < exportConfig.pageCount; i++) {
        doc.addPage();
        currentPage++;
        
        const scene = scenes[i];
        
        // Scene title
        doc.setFontSize(16);
        doc.setTextColor(30);
        doc.text(scene.title || `Scene ${i + 1}`, pageWidth / 2, margin + 10, { align: 'center' });
        
        // Scene description
        doc.setFontSize(10);
        doc.setTextColor(80);
        const descLines = doc.splitTextToSize(scene.description || scene.visualDescription || '', contentWidth);
        doc.text(descLines, margin, margin + 25);
        
        const imageY = margin + 45;
        const imageHeight = contentHeight - 60;
        
        if (mode === 'photo' && processedImages[i]) {
          // Add processed coloring image
          try {
            doc.addImage(processedImages[i], 'PNG', margin, imageY, contentWidth, imageHeight, undefined, 'FAST');
          } catch (e) {
            // Fallback to frame
            doc.setDrawColor(180);
            doc.setLineWidth(1);
            doc.rect(margin, imageY, contentWidth, imageHeight);
            doc.setFontSize(12);
            doc.setTextColor(150);
            doc.text('Draw this scene:', margin + 10, imageY + 20);
          }
        } else {
          // Placeholder mode - empty frame with prompt
          doc.setDrawColor(180);
          doc.setLineWidth(1);
          doc.rect(margin, imageY, contentWidth, imageHeight);
          
          doc.setFontSize(12);
          doc.setTextColor(150);
          doc.text('Draw this scene:', pageWidth / 2, imageY + 30, { align: 'center' });
          
          const promptLines = doc.splitTextToSize(scene.visualDescription || scene.description || 'Illustrate the scene', contentWidth - 20);
          doc.text(promptLines, pageWidth / 2, imageY + 45, { align: 'center' });
        }
        
        addFooter();
      }
      
      // ACTIVITY PAGES
      if (exportConfig.includeActivityPages) {
        // Word Search / Vocabulary page
        doc.addPage();
        currentPage++;
        
        doc.setFontSize(18);
        doc.setTextColor(30);
        doc.text('Story Vocabulary', pageWidth / 2, margin + 15, { align: 'center' });
        
        doc.setFontSize(10);
        doc.setTextColor(80);
        doc.text('Learn these words from the story:', margin, margin + 30);
        
        // Extract unique words from story
        const storyText = `${selectedStory.synopsis || ''} ${selectedStory.moral || ''}`;
        const words = storyText.split(/\s+/).filter(w => w.length > 4).slice(0, 12);
        const uniqueWords = [...new Set(words)];
        
        let wordY = margin + 45;
        uniqueWords.forEach((word, idx) => {
          doc.text(`${idx + 1}. ${word}`, margin + 10, wordY);
          doc.setDrawColor(200);
          doc.line(margin + 60, wordY, margin + contentWidth - 10, wordY);
          wordY += 15;
        });
        
        addFooter();
        
        // Certificate page
        doc.addPage();
        currentPage++;
        
        doc.setDrawColor(200);
        doc.setLineWidth(3);
        doc.rect(margin + 10, margin + 10, contentWidth - 20, contentHeight - 20);
        
        doc.setFontSize(28);
        doc.setTextColor(30);
        doc.text('Certificate of Completion', pageWidth / 2, 60, { align: 'center' });
        
        doc.setFontSize(14);
        doc.setTextColor(80);
        doc.text('This certifies that', pageWidth / 2, 90, { align: 'center' });
        
        doc.setFontSize(22);
        doc.setTextColor(30);
        doc.text(exportConfig.childName || '_______________', pageWidth / 2, 110, { align: 'center' });
        
        doc.setFontSize(14);
        doc.setTextColor(80);
        doc.text('has completed the coloring book', pageWidth / 2, 130, { align: 'center' });
        doc.text(`"${selectedStory.title}"`, pageWidth / 2, 145, { align: 'center' });
        
        doc.setFontSize(12);
        doc.text(`Date: _________________`, pageWidth / 2, 180, { align: 'center' });
        
        addFooter();
      }
      
      // MORAL PAGE
      if (selectedStory.moral) {
        doc.addPage();
        currentPage++;
        
        doc.setFontSize(18);
        doc.setTextColor(30);
        doc.text('The Lesson We Learned', pageWidth / 2, margin + 30, { align: 'center' });
        
        doc.setDrawColor(200);
        doc.setLineWidth(1);
        const moralBox = { x: margin + 20, y: margin + 50, w: contentWidth - 40, h: 80 };
        doc.rect(moralBox.x, moralBox.y, moralBox.w, moralBox.h);
        
        doc.setFontSize(14);
        doc.setTextColor(60);
        const moralLines = doc.splitTextToSize(selectedStory.moral, moralBox.w - 20);
        doc.text(moralLines, pageWidth / 2, moralBox.y + 25, { align: 'center' });
        
        addFooter();
      }
      
      // Save PDF
      const filename = `coloring-book-${selectedStory.title?.replace(/\s+/g, '-') || 'story'}.pdf`;
      doc.save(filename);
      
      // Log export and charge credits (backend)
      try {
        await api.post('/api/coloring-book/export', {
          storyId: selectedStory.id,
          config: exportConfig,
          mode,
          processedSceneCount: Object.keys(processedImages).length
        });
        
        // Refresh wallet
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        
        toast.success('Coloring book exported successfully!');
      } catch (error) {
        console.error('Export logging failed:', error);
        toast.error('PDF saved but credit logging failed');
      }
      
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Failed to generate PDF');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-purple-500 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Coloring Book Creator</h1>
                  <p className="text-xs text-slate-400">Personalized Printable Story Books</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2" data-testid="wallet-balance">
                <Wallet className="w-4 h-4 text-purple-400" />
                <span className="font-bold text-white text-sm">{wallet.availableCredits}</span>
                <span className="text-xs text-slate-500">credits</span>
              </div>
              <Link to="/app/billing">
                <Button size="sm" className="bg-purple-600 hover:bg-purple-700">
                  Buy Credits
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Privacy Notice */}
        <div className="mb-6 bg-green-500/10 border border-green-500/30 rounded-xl p-4 flex items-start gap-3">
          <Lock className="w-5 h-5 text-green-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-green-300">Your Privacy is Protected</p>
            <p className="text-xs text-slate-400">Images are processed locally in your browser. We never upload or store them.</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Panel - Story Selection & Mode */}
          <div className="space-y-6">
            {/* Mode Selection */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Palette className="w-4 h-4 text-purple-400" />
                Creation Mode
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setMode('placeholder')}
                  className={`p-4 rounded-lg border text-left transition-all ${
                    mode === 'placeholder' 
                      ? 'border-purple-500 bg-purple-500/10' 
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                  data-testid="mode-placeholder"
                >
                  <Pencil className="w-6 h-6 text-purple-400 mb-2" />
                  <p className="text-sm font-medium text-white">DIY Mode</p>
                  <p className="text-xs text-slate-500">Empty frames with prompts</p>
                </button>
                <button
                  onClick={() => setMode('photo')}
                  className={`p-4 rounded-lg border text-left transition-all ${
                    mode === 'photo' 
                      ? 'border-pink-500 bg-pink-500/10' 
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                  data-testid="mode-photo"
                >
                  <Image className="w-6 h-6 text-pink-400 mb-2" />
                  <p className="text-sm font-medium text-white">Photo Mode</p>
                  <p className="text-xs text-slate-500">Upload & convert images</p>
                </button>
              </div>
              
              {/* Instructional Text for Selected Mode */}
              <div className="mt-4 p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                {mode === 'placeholder' ? (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-purple-300">DIY Mode Instructions:</p>
                    <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                      <li>Pages include empty frames with scene descriptions</li>
                      <li>Kids draw their own illustrations based on the prompts</li>
                      <li>Perfect for developing creativity and imagination</li>
                      <li>No image upload required - just select story and export</li>
                    </ul>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-pink-300">Photo Mode Instructions:</p>
                    <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                      <li>Upload photos for each scene from your device</li>
                      <li>AI converts photos to black & white outline drawings</li>
                      <li>Adjust outline strength for thicker or thinner lines</li>
                      <li>Great for turning family photos into coloring pages</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Story Selection */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Book className="w-4 h-4 text-blue-400" />
                Select a Story
              </h3>
              
              {stories.length === 0 ? (
                <div className="text-center py-8">
                  <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400 text-sm">No stories found</p>
                  <Link to="/app/stories">
                    <Button size="sm" className="mt-3 bg-purple-600">Generate a Story</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {stories.map((story) => (
                    <button
                      key={story.id}
                      onClick={() => handleStorySelect(story.id)}
                      className={`w-full p-3 rounded-lg border text-left transition-all ${
                        selectedStory?.id === story.id 
                          ? 'border-purple-500 bg-purple-500/10' 
                          : 'border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <p className="text-sm font-medium text-white truncate">{story.title}</p>
                      <p className="text-xs text-slate-500">{story.scenes?.length || 0} scenes</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Export Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4 text-slate-400" />
                Export Settings
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400 mb-2 block">Page Count</label>
                  <Select 
                    value={String(exportConfig.pageCount)} 
                    onValueChange={(v) => setExportConfig(prev => ({ ...prev, pageCount: parseInt(v) }))}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="8">8 pages</SelectItem>
                      <SelectItem value="10">10 pages</SelectItem>
                      <SelectItem value="12">12 pages</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <label className="text-xs text-slate-400 mb-2 block">Paper Size</label>
                  <Select 
                    value={exportConfig.paperSize} 
                    onValueChange={(v) => setExportConfig(prev => ({ ...prev, paperSize: v }))}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="A4">A4</SelectItem>
                      <SelectItem value="Letter">US Letter</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">Activity Pages</p>
                    <p className="text-xs text-slate-500">+{pricing.ACTIVITY_PAGES || 2} credits</p>
                  </div>
                  <button
                    onClick={() => setExportConfig(prev => ({ ...prev, includeActivityPages: !prev.includeActivityPages }))}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      exportConfig.includeActivityPages ? 'bg-purple-500' : 'bg-slate-600'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${
                      exportConfig.includeActivityPages ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">Personalized Cover</p>
                    <p className="text-xs text-slate-500">+{pricing.PERSONALIZED_COVER || 1} credit</p>
                  </div>
                  <button
                    onClick={() => setExportConfig(prev => ({ ...prev, personalizedCover: !prev.personalizedCover }))}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      exportConfig.personalizedCover ? 'bg-purple-500' : 'bg-slate-600'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${
                      exportConfig.personalizedCover ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>
                
                {exportConfig.personalizedCover && (
                  <div>
                    <label className="text-xs text-slate-400 mb-2 block">Child's Name</label>
                    <input
                      type="text"
                      value={exportConfig.childName}
                      onChange={(e) => setExportConfig(prev => ({ ...prev, childName: e.target.value.slice(0, 100) }))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
                      placeholder="Enter name"
                      maxLength={100}
                    />
                    <p className="text-xs text-slate-500 mt-1">{exportConfig.childName.length}/100</p>
                  </div>
                )}
                
                <div>
                  <label className="text-xs text-slate-400 mb-2 block">Dedication (optional)</label>
                  <textarea
                    value={exportConfig.dedication}
                    onChange={(e) => setExportConfig(prev => ({ ...prev, dedication: e.target.value.slice(0, 300) }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm resize-none"
                    placeholder="A special message..."
                    rows={2}
                    maxLength={300}
                  />
                  <p className="text-xs text-slate-500 mt-1">{exportConfig.dedication.length}/300</p>
                </div>
              </div>
            </div>
          </div>

          {/* Center Panel - Scene Editor */}
          <div className="lg:col-span-2 space-y-6">
            {selectedStory ? (
              <>
                {/* Story Info */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <h2 className="text-xl font-bold text-white mb-2">{selectedStory.title}</h2>
                  <p className="text-sm text-slate-400">{selectedStory.synopsis}</p>
                  <div className="flex gap-4 mt-3">
                    <span className="text-xs text-purple-400">{selectedStory.genre}</span>
                    <span className="text-xs text-slate-500">{scenes.length} scenes</span>
                  </div>
                </div>

                {/* Scene Navigation */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                  <div className="flex items-center gap-2 overflow-x-auto pb-2">
                    {scenes.map((scene, idx) => (
                      <button
                        key={idx}
                        onClick={() => setActiveSceneIndex(idx)}
                        className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          activeSceneIndex === idx 
                            ? 'bg-purple-500 text-white' 
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        Scene {idx + 1}
                        {processedImages[idx] && <CheckCircle className="w-3 h-3 ml-1 inline text-green-400" />}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Active Scene Editor */}
                {scenes[activeSceneIndex] && (
                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-white">
                          {scenes[activeSceneIndex].title || `Scene ${activeSceneIndex + 1}`}
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">
                          {scenes[activeSceneIndex].description || scenes[activeSceneIndex].visualDescription}
                        </p>
                      </div>
                    </div>

                    {mode === 'photo' ? (
                      <div className="space-y-4">
                        {/* Image Upload Area */}
                        <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center hover:border-purple-500 transition-colors">
                          {sceneImages[activeSceneIndex] ? (
                            <div className="space-y-4">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <p className="text-xs text-slate-500 mb-2">Original</p>
                                  <img 
                                    src={sceneImages[activeSceneIndex].src} 
                                    alt="Original" 
                                    className="w-full rounded-lg"
                                  />
                                </div>
                                <div>
                                  <p className="text-xs text-slate-500 mb-2">Coloring Page Preview</p>
                                  {processedImages[activeSceneIndex] ? (
                                    <img 
                                      src={processedImages[activeSceneIndex]} 
                                      alt="Processed" 
                                      className="w-full rounded-lg bg-white"
                                    />
                                  ) : processing ? (
                                    <div className="aspect-square bg-slate-800 rounded-lg flex items-center justify-center">
                                      <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
                                    </div>
                                  ) : (
                                    <div className="aspect-square bg-slate-800 rounded-lg flex items-center justify-center">
                                      <p className="text-sm text-slate-500">Processing...</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                              <div className="flex justify-center gap-2">
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={() => regenerateOutline(activeSceneIndex)}
                                  disabled={processing}
                                  className="border-slate-600"
                                >
                                  <RefreshCw className="w-4 h-4 mr-1" />
                                  Regenerate
                                </Button>
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={() => clearSceneImage(activeSceneIndex)}
                                  className="border-red-600 text-red-400 hover:bg-red-500/10"
                                >
                                  <Trash2 className="w-4 h-4 mr-1" />
                                  Clear
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <label className="cursor-pointer block">
                              <input
                                type="file"
                                accept="image/*"
                                onChange={(e) => handleImageUpload(activeSceneIndex, e.target.files[0])}
                                className="hidden"
                              />
                              <Upload className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                              <p className="text-sm text-slate-400">Click to upload an image</p>
                              <p className="text-xs text-slate-500 mt-1">PNG, JPG up to 10MB</p>
                            </label>
                          )}
                        </div>

                        {/* Outline Settings */}
                        {sceneImages[activeSceneIndex] && (
                          <div className="bg-slate-800 rounded-lg p-4 space-y-4">
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <label className="text-sm text-slate-400">Outline Strength</label>
                                <span className="text-xs text-slate-500">{outlineStrength}%</span>
                              </div>
                              <Slider
                                value={[outlineStrength]}
                                onValueChange={(v) => setOutlineStrength(v[0])}
                                onValueCommit={() => regenerateOutline(activeSceneIndex)}
                                max={100}
                                step={5}
                                className="w-full"
                              />
                              <div className="flex justify-between text-xs text-slate-600 mt-1">
                                <span>Light</span>
                                <span>Medium</span>
                                <span>Bold</span>
                              </div>
                            </div>
                            
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-slate-400">Invert Colors</span>
                              <button
                                onClick={() => {
                                  setInvertColors(!invertColors);
                                  setTimeout(() => regenerateOutline(activeSceneIndex), 100);
                                }}
                                className={`w-10 h-5 rounded-full transition-colors ${
                                  invertColors ? 'bg-purple-500' : 'bg-slate-600'
                                }`}
                              >
                                <div className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                                  invertColors ? 'translate-x-5' : 'translate-x-1'
                                }`} />
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Placeholder Mode Preview */
                      <div className="border-2 border-slate-700 rounded-xl p-8 text-center">
                        <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                        <p className="text-slate-400">DIY Mode</p>
                        <p className="text-sm text-slate-500 mt-2">
                          This scene will include an empty frame with the prompt:
                        </p>
                        <p className="text-sm text-purple-400 mt-2 italic">
                          "{scenes[activeSceneIndex].visualDescription || scenes[activeSceneIndex].description || 'Draw this scene'}"
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Export Section */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-white">Export Coloring Book</h3>
                      <p className="text-sm text-slate-400">
                        Cost: <span className="text-purple-400 font-bold">{calculateCost()} credits</span>
                      </p>
                    </div>
                    {!canAfford && (
                      <div className="flex items-center gap-2 text-red-400">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm">Insufficient credits</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-3">
                    <Button
                      onClick={handleExport}
                      disabled={exporting || !canAfford}
                      className="flex-1 bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600"
                      data-testid="export-btn"
                    >
                      {exporting ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Generating PDF...
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <Download className="w-4 h-4" />
                          Export PDF ({calculateCost()} credits)
                        </span>
                      )}
                    </Button>
                    {!canAfford && (
                      <Link to="/app/billing">
                        <Button className="bg-purple-600 hover:bg-purple-700">
                          Buy Credits
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              </>
            ) : (
              /* No Story Selected */
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
                <BookOpen className="w-20 h-20 text-slate-700 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">Select a Story</h3>
                <p className="text-slate-400 mb-6">Choose a story from the list to create your coloring book</p>
                <Link to="/app/stories">
                  <Button className="bg-purple-600 hover:bg-purple-700">
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate New Story
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Legal Disclaimer */}
        <div className="mt-8 bg-slate-900/30 border border-slate-800 rounded-xl p-4">
          <p className="text-xs text-slate-500 text-center">
            <strong>Disclaimer:</strong> Upload only images you own or have permission to use. 
            Do not use copyrighted characters (Disney, Marvel, etc.). 
            All templates are original creations by CreatorStudio AI.
          </p>
        </div>
      </main>
    </div>
  );
}
