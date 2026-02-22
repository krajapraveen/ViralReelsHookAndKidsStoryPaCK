import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Slider } from '../components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  ArrowLeft, Upload, Image as ImageIcon, Sparkles, Download, Trash2,
  Type, MessageSquare, Zap, Palette, Grid, LayoutGrid,
  RefreshCw, Eye, FileText, Loader2, Coins, X, Move,
  Plus, ChevronLeft, ChevronRight, Settings, Wand2, Share2, Layers
} from 'lucide-react';
import api, { creditAPI } from '../utils/api';
import { processImage, createPanelLayout, addWatermark } from '../utils/comicFilters';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { saveAs } from 'file-saver';
import HelpGuide from '../components/HelpGuide';

// Genre icons
const GENRE_ICONS = {
  superhero: '🦸',
  romance: '💕',
  comedy: '😂',
  scifi: '🚀',
  fantasy: '🧙',
  mystery: '🔍',
  horror: '👻',
  kids: '🌈'
};

// Style options
const STYLES = [
  { id: 'comic_color', name: 'Comic Color', description: 'Vibrant comic book colors' },
  { id: 'comic_bw', name: 'Comic B&W', description: 'Classic black & white' },
  { id: 'manga_bw', name: 'Manga B&W', description: 'Japanese manga style with halftone' }
];

// Layout options
const LAYOUTS = [
  { id: '1', name: 'Full Page', icon: '▢', panels: 1 },
  { id: '2h', name: '2 Horizontal', icon: '▯▯', panels: 2 },
  { id: '2v', name: '2 Vertical', icon: '▭', panels: 2 },
  { id: '4', name: '4 Panels', icon: '⊞', panels: 4 },
  { id: '6', name: '6 Panels', icon: '⊟', panels: 6 }
];

// Bubble styles
const BUBBLE_STYLES = [
  { id: 'none', name: 'None' },
  { id: 'speech', name: 'Speech' },
  { id: 'thought', name: 'Thought' },
  { id: 'shout', name: 'Shout' }
];

export default function ComicStudio() {
  // State
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  // Comic settings
  const [genre, setGenre] = useState('superhero');
  const [style, setStyle] = useState('comic_color');
  const [layout, setLayout] = useState('4');
  const [bubbleStyle, setBubbleStyle] = useState('speech');
  const [storyMode, setStoryMode] = useState(false);
  
  // Images & panels
  const [uploadedImages, setUploadedImages] = useState([]);
  const [panels, setPanels] = useState([]);
  const [selectedPanel, setSelectedPanel] = useState(null);
  
  // Story data
  const [storyData, setStoryData] = useState(null);
  const [characterName, setCharacterName] = useState('Me');
  
  // Genre data
  const [genres, setGenres] = useState([]);
  const [genreAssets, setGenreAssets] = useState(null);
  const [sfxList, setSfxList] = useState([]);
  
  // Canvas ref
  const canvasRef = useRef(null);
  const previewRef = useRef(null);

  // Load initial data
  useEffect(() => {
    loadCredits();
    loadGenres();
  }, []);

  // Load genre assets when genre changes
  useEffect(() => {
    if (genre) {
      loadGenreAssets(genre);
    }
  }, [genre]);

  const loadCredits = async () => {
    try {
      const res = await creditAPI.getCredits();
      setCredits(res.data.credits);
    } catch (error) {
      console.error('Failed to load credits:', error);
    }
  };

  const loadGenres = async () => {
    try {
      const res = await api.get('/api/comic/genres');
      setGenres(res.data.genres);
    } catch (error) {
      console.error('Failed to load genres:', error);
    }
  };

  const loadGenreAssets = async (genreId) => {
    try {
      const res = await api.get(`/api/comic/assets/${genreId}`);
      setGenreAssets(res.data);
      setSfxList(res.data.sfx || []);
    } catch (error) {
      console.error('Failed to load genre assets:', error);
    }
  };

  // Handle image upload
  const handleImageUpload = useCallback((e) => {
    const files = Array.from(e.target.files);
    const maxImages = LAYOUTS.find(l => l.id === layout)?.panels || 4;
    
    if (uploadedImages.length + files.length > 6) {
      toast.error('Maximum 6 images allowed');
      return;
    }

    files.forEach(file => {
      if (!file.type.startsWith('image/')) {
        toast.error(`${file.name} is not an image`);
        return;
      }

      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name} is too large (max 10MB)`);
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          setUploadedImages(prev => [...prev, {
            id: Date.now() + Math.random(),
            file,
            src: e.target.result,
            image: img,
            processedImage: null
          }]);
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }, [layout, uploadedImages.length]);

  // Remove image
  const removeImage = (id) => {
    setUploadedImages(prev => prev.filter(img => img.id !== id));
  };

  // Process images with comic filter
  const processImages = async () => {
    if (uploadedImages.length === 0) {
      toast.error('Please upload at least one image');
      return;
    }

    setProcessing(true);
    try {
      const genreConfig = genres.find(g => g.id === genre);
      const colorGrading = genreConfig?.colorGrading || {};

      const processedPanels = await Promise.all(
        uploadedImages.map(async (imgData, index) => {
          const processedCanvas = await processImage(imgData.image, style, colorGrading);
          return {
            id: imgData.id,
            index,
            originalImage: imgData.image,
            processedImage: processedCanvas,
            bubbleText: '',
            caption: '',
            sfx: null,
            bubblePosition: { x: 50, y: 20 },
            sfxPosition: { x: 80, y: 80 }
          };
        })
      );

      setPanels(processedPanels);
      toast.success('Images processed! Click on panels to add text.');
    } catch (error) {
      console.error('Processing error:', error);
      toast.error('Failed to process images');
    } finally {
      setProcessing(false);
    }
  };

  // Generate story from templates
  const generateStory = async () => {
    try {
      setLoading(true);
      const panelCount = LAYOUTS.find(l => l.id === layout)?.panels || 4;
      
      const res = await api.post('/api/comic/generate-story', {
        genre,
        tone: 'normal',
        character_name: characterName,
        panel_count: Math.min(panelCount, panels.length || panelCount)
      });

      setStoryData(res.data);
      
      // Apply story to panels
      if (panels.length > 0) {
        const updatedPanels = panels.map((panel, index) => {
          const storyPanel = res.data.panels[index];
          if (storyPanel) {
            return {
              ...panel,
              bubbleText: storyPanel.bubbleText,
              caption: storyPanel.caption,
              sfx: storyPanel.sfx
            };
          }
          return panel;
        });
        setPanels(updatedPanels);
      }

      toast.success('Story generated!');
    } catch (error) {
      console.error('Story generation error:', error);
      toast.error('Failed to generate story');
    } finally {
      setLoading(false);
    }
  };

  // Update panel text
  const updatePanelText = (panelId, field, value) => {
    setPanels(prev => prev.map(p => 
      p.id === panelId ? { ...p, [field]: value } : p
    ));
  };

  // Add SFX to panel
  const addSfxToPanel = (panelId, sfx) => {
    setPanels(prev => prev.map(p => 
      p.id === panelId ? { ...p, sfx } : p
    ));
  };

  // Calculate export cost
  const getExportCost = () => {
    const panelCount = panels.length;
    let cost = panelCount <= 4 ? 8 : 10;
    if (storyMode) cost += 1;
    return cost;
  };

  // Export to PNG
  const exportToPNG = async (removeWatermark = false) => {
    if (panels.length === 0) {
      toast.error('No panels to export');
      return;
    }

    const totalCost = getExportCost() + (removeWatermark ? 2 : 0);
    if (credits < totalCost) {
      toast.error(`Insufficient credits. Need ${totalCost}, have ${credits}`);
      return;
    }

    setExporting(true);
    try {
      // Log export and debit credits
      await api.post('/api/comic/export', {
        export_type: 'PNG',
        panel_count: panels.length,
        genre,
        has_watermark: !removeWatermark,
        story_mode: storyMode
      });

      // Generate the comic page
      const comicCanvas = await generateComicCanvas(!removeWatermark);
      
      // Download
      comicCanvas.toBlob(blob => {
        saveAs(blob, `comic_${genre}_${Date.now()}.png`);
      });

      await loadCredits();
      toast.success('Comic exported successfully!');
    } catch (error) {
      console.error('Export error:', error);
      toast.error(error.response?.data?.detail?.error || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  // Export to PDF
  const exportToPDF = async (removeWatermark = false) => {
    if (panels.length === 0) {
      toast.error('No panels to export');
      return;
    }

    const totalCost = getExportCost() + (removeWatermark ? 2 : 0);
    if (credits < totalCost) {
      toast.error(`Insufficient credits. Need ${totalCost}, have ${credits}`);
      return;
    }

    setExporting(true);
    try {
      // Log export and debit credits
      await api.post('/api/comic/export', {
        export_type: 'PDF',
        panel_count: panels.length,
        genre,
        has_watermark: !removeWatermark,
        story_mode: storyMode
      });

      // Generate the comic page
      const comicCanvas = await generateComicCanvas(!removeWatermark);
      
      // Create PDF
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: [comicCanvas.width, comicCanvas.height]
      });

      const imgData = comicCanvas.toDataURL('image/png');
      pdf.addImage(imgData, 'PNG', 0, 0, comicCanvas.width, comicCanvas.height);
      pdf.save(`comic_${genre}_${Date.now()}.pdf`);

      await loadCredits();
      toast.success('PDF exported successfully!');
    } catch (error) {
      console.error('Export error:', error);
      toast.error(error.response?.data?.detail?.error || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  // Generate comic canvas with all elements
  const generateComicCanvas = async (withWatermark = true) => {
    const { canvas, panelPositions } = createPanelLayout(panels, layout, {
      width: 800,
      height: 1200,
      gutterSize: 12,
      borderWidth: 4,
      borderColor: '#000',
      backgroundColor: '#fff'
    });

    const ctx = canvas.getContext('2d');

    // Add speech bubbles and text
    panelPositions.forEach((pos, index) => {
      const panel = panels[index];
      if (!panel) return;

      // Draw caption at bottom
      if (panel.caption) {
        ctx.fillStyle = 'rgba(0,0,0,0.8)';
        ctx.fillRect(pos.x, pos.y + pos.height - 40, pos.width, 40);
        ctx.fillStyle = '#fff';
        ctx.font = 'italic 14px Georgia';
        ctx.textAlign = 'center';
        ctx.fillText(
          panel.caption.substring(0, 50),
          pos.x + pos.width / 2,
          pos.y + pos.height - 15
        );
      }

      // Draw speech bubble
      if (panel.bubbleText && bubbleStyle !== 'none') {
        const bx = pos.x + (panel.bubblePosition?.x || 50) * pos.width / 100;
        const by = pos.y + (panel.bubblePosition?.y || 20) * pos.height / 100;
        
        // Bubble shape
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        if (bubbleStyle === 'thought') {
          // Cloud shape
          ctx.ellipse(bx, by, 60, 30, 0, 0, Math.PI * 2);
        } else if (bubbleStyle === 'shout') {
          // Spiky shape
          ctx.moveTo(bx - 60, by);
          for (let i = 0; i < 16; i++) {
            const angle = (i / 16) * Math.PI * 2;
            const r = i % 2 === 0 ? 60 : 45;
            ctx.lineTo(bx + Math.cos(angle) * r, by + Math.sin(angle) * r * 0.5);
          }
          ctx.closePath();
        } else {
          // Regular speech bubble
          ctx.ellipse(bx, by, 60, 30, 0, 0, Math.PI * 2);
        }
        
        ctx.fill();
        ctx.stroke();

        // Tail
        if (bubbleStyle === 'speech' || bubbleStyle === 'shout') {
          ctx.beginPath();
          ctx.moveTo(bx - 10, by + 25);
          ctx.lineTo(bx - 20, by + 50);
          ctx.lineTo(bx + 10, by + 25);
          ctx.fillStyle = '#fff';
          ctx.fill();
          ctx.stroke();
        }

        // Text
        ctx.fillStyle = '#000';
        ctx.font = bubbleStyle === 'shout' ? 'bold 12px Comic Sans MS, cursive' : '12px Comic Sans MS, cursive';
        ctx.textAlign = 'center';
        const words = panel.bubbleText.split(' ');
        let line = '';
        let lineY = by - 10;
        words.forEach(word => {
          const testLine = line + word + ' ';
          if (ctx.measureText(testLine).width > 100) {
            ctx.fillText(line, bx, lineY);
            line = word + ' ';
            lineY += 14;
          } else {
            line = testLine;
          }
        });
        ctx.fillText(line, bx, lineY);
      }

      // Draw SFX
      if (panel.sfx) {
        const sx = pos.x + (panel.sfxPosition?.x || 80) * pos.width / 100;
        const sy = pos.y + (panel.sfxPosition?.y || 80) * pos.height / 100;
        
        ctx.save();
        ctx.translate(sx, sy);
        ctx.rotate(-0.1);
        ctx.font = 'bold 24px Impact, sans-serif';
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 4;
        ctx.strokeText(panel.sfx, 0, 0);
        ctx.fillStyle = '#ff0000';
        ctx.fillText(panel.sfx, 0, 0);
        ctx.restore();
      }
    });

    // Add title if story mode
    if (storyMode && storyData?.title) {
      ctx.fillStyle = '#000';
      ctx.font = 'bold 28px Impact, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(storyData.title.toUpperCase(), canvas.width / 2, 35);
    }

    // Add watermark
    if (withWatermark) {
      addWatermark(canvas);
    }

    return canvas;
  };

  // Preview comic
  const previewComic = async () => {
    if (panels.length === 0) {
      toast.error('Process images first');
      return;
    }

    const comicCanvas = await generateComicCanvas(true);
    
    if (previewRef.current) {
      previewRef.current.innerHTML = '';
      previewRef.current.appendChild(comicCanvas);
    }
  };

  const selectedLayoutPanels = LAYOUTS.find(l => l.id === layout)?.panels || 4;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950" data-testid="comic-studio-page">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-xl border-b border-slate-800 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white" data-testid="back-to-dashboard">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎨</span>
              <span className="text-xl font-bold text-white">Comic Studio</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-purple-500/20 border border-purple-500/30 rounded-full px-4 py-2" data-testid="credits-display">
              <Coins className="w-4 h-4 text-purple-400" />
              <span className="font-semibold text-purple-300">{credits}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Privacy Notice */}
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 mb-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center">
            <Eye className="w-4 h-4 text-green-400" />
          </div>
          <p className="text-sm text-green-300">
            <strong>Privacy First:</strong> Images are processed on your device. We don't upload or store your photos.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Panel - Settings */}
          <div className="lg:col-span-1 space-y-6">
            {/* Genre Selection */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4" data-testid="genre-selection">
              <Label className="text-white font-medium mb-3 block">Genre</Label>
              <div className="grid grid-cols-4 gap-2">
                {genres.map(g => (
                  <button
                    key={g.id}
                    onClick={() => setGenre(g.id)}
                    data-testid={`genre-${g.id}`}
                    className={`p-3 rounded-lg border text-center transition-all ${
                      genre === g.id
                        ? 'bg-purple-600 border-purple-500 text-white'
                        : 'bg-slate-700/50 border-slate-600 text-slate-300 hover:bg-slate-700'
                    }`}
                    title={g.description}
                  >
                    <span className="text-xl">{GENRE_ICONS[g.id]}</span>
                    <p className="text-xs mt-1 truncate">{g.name}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Style Selection */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <Label className="text-white font-medium mb-3 block">Style</Label>
              <Select value={style} onValueChange={setStyle}>
                <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STYLES.map(s => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name} - {s.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Layout Selection */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4" data-testid="layout-selection">
              <Label className="text-white font-medium mb-3 block">Layout</Label>
              <div className="grid grid-cols-5 gap-2">
                {LAYOUTS.map(l => (
                  <button
                    key={l.id}
                    onClick={() => setLayout(l.id)}
                    data-testid={`layout-${l.id}`}
                    className={`p-2 rounded-lg border text-center transition-all ${
                      layout === l.id
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'bg-slate-700/50 border-slate-600 text-slate-300 hover:bg-slate-700'
                    }`}
                    title={l.name}
                  >
                    <span className="text-lg">{l.icon}</span>
                    <p className="text-xs mt-1">{l.panels}P</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Bubble Style */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <Label className="text-white font-medium mb-3 block">Speech Bubbles</Label>
              <Select value={bubbleStyle} onValueChange={setBubbleStyle}>
                <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BUBBLE_STYLES.map(b => (
                    <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Story Mode */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4" data-testid="story-mode-section">
              <div className="flex items-center justify-between mb-3">
                <Label className="text-white font-medium">Story Mode</Label>
                <span className="text-xs text-green-400 bg-green-500/20 px-2 py-1 rounded">+1 credit</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setStoryMode(!storyMode)}
                  data-testid="story-mode-toggle"
                  className={`px-4 py-2 rounded-lg border transition-all ${
                    storyMode
                      ? 'bg-purple-600 border-purple-500 text-white'
                      : 'bg-slate-700 border-slate-600 text-slate-300'
                  }`}
                >
                  {storyMode ? 'ON' : 'OFF'}
                </button>
                {storyMode && (
                  <Input
                    value={characterName}
                    onChange={(e) => setCharacterName(e.target.value)}
                    placeholder="Character name"
                    data-testid="character-name-input"
                    className="bg-slate-700 border-slate-600 text-white flex-1"
                  />
                )}
              </div>
              {storyMode && panels.length > 0 && (
                <Button
                  onClick={generateStory}
                  disabled={loading}
                  data-testid="generate-story-btn"
                  className="w-full mt-3 bg-purple-600 hover:bg-purple-700"
                >
                  {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
                  Generate Story
                </Button>
              )}
            </div>

            {/* Export Cost Info */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <h3 className="text-white font-medium mb-3">Export Cost</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between text-slate-300">
                  <span>Base ({panels.length || selectedLayoutPanels} panels)</span>
                  <span>{panels.length <= 4 ? 8 : 10} credits</span>
                </div>
                {storyMode && (
                  <div className="flex justify-between text-slate-300">
                    <span>Story Mode</span>
                    <span>+1 credit</span>
                  </div>
                )}
                <div className="flex justify-between text-slate-300">
                  <span>Remove Watermark</span>
                  <span>+2 credits</span>
                </div>
                <div className="border-t border-slate-600 pt-2 flex justify-between text-white font-semibold">
                  <span>Total</span>
                  <span>{getExportCost()} credits</span>
                </div>
              </div>
            </div>
          </div>

          {/* Middle Panel - Image Upload & Editor */}
          <div className="lg:col-span-2 space-y-6">
            {/* Image Upload */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4" data-testid="upload-section">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-medium">Upload Images ({uploadedImages.length}/6)</h3>
                <span className="text-xs text-slate-400">Max {selectedLayoutPanels} for selected layout</span>
              </div>
              
              <div className="border-2 border-dashed border-slate-600 rounded-xl p-6 text-center hover:border-purple-500 transition-colors">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  onChange={handleImageUpload}
                  className="hidden"
                  id="image-upload"
                  data-testid="image-upload-input"
                />
                <label htmlFor="image-upload" className="cursor-pointer" data-testid="upload-label">
                  <Upload className="w-10 h-10 mx-auto mb-3 text-slate-400" />
                  <p className="text-slate-300 mb-1">Drag & drop or click to upload</p>
                  <p className="text-xs text-slate-500">JPG, PNG, WebP • Max 10MB each</p>
                </label>
              </div>

              {/* Uploaded Images Preview */}
              {uploadedImages.length > 0 && (
                <div className="grid grid-cols-6 gap-2 mt-4">
                  {uploadedImages.map((img, index) => (
                    <div key={img.id} className="relative aspect-square rounded-lg overflow-hidden border border-slate-600">
                      <img src={img.src} alt={`Upload ${index + 1}`} className="w-full h-full object-cover" />
                      <button
                        onClick={() => removeImage(img.id)}
                        className="absolute top-1 right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white"
                      >
                        <X className="w-3 h-3" />
                      </button>
                      <span className="absolute bottom-1 left-1 text-xs bg-black/50 text-white px-1 rounded">
                        {index + 1}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Process Button */}
              <Button
                onClick={processImages}
                disabled={uploadedImages.length === 0 || processing}
                data-testid="convert-to-comic-btn"
                className="w-full mt-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              >
                {processing ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                {processing ? 'Processing...' : 'Convert to Comic Style'}
              </Button>
            </div>

            {/* Panel Editor */}
            {panels.length > 0 && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white font-medium">Edit Panels</h3>
                  <Button variant="outline" size="sm" onClick={previewComic} className="border-slate-600 text-slate-300">
                    <Eye className="w-4 h-4 mr-2" />
                    Preview
                  </Button>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-4">
                  {panels.map((panel, index) => (
                    <div
                      key={panel.id}
                      onClick={() => setSelectedPanel(panel.id)}
                      className={`relative aspect-square rounded-lg overflow-hidden cursor-pointer border-2 transition-all ${
                        selectedPanel === panel.id ? 'border-purple-500 ring-2 ring-purple-500/50' : 'border-slate-600'
                      }`}
                    >
                      {panel.processedImage && (
                        <img
                          src={panel.processedImage.toDataURL()}
                          alt={`Panel ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                      )}
                      <span className="absolute top-1 left-1 text-xs bg-black/70 text-white px-2 py-0.5 rounded">
                        Panel {index + 1}
                      </span>
                      {panel.bubbleText && (
                        <span className="absolute bottom-1 right-1 text-xs bg-white text-black px-1 rounded">
                          <MessageSquare className="w-3 h-3" />
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {/* Selected Panel Editor */}
                {selectedPanel && (
                  <div className="bg-slate-700/50 rounded-lg p-4 space-y-4">
                    <div>
                      <Label className="text-slate-300 text-sm mb-1 block">Speech Bubble Text</Label>
                      <Textarea
                        value={panels.find(p => p.id === selectedPanel)?.bubbleText || ''}
                        onChange={(e) => updatePanelText(selectedPanel, 'bubbleText', e.target.value)}
                        placeholder="What is the character saying?"
                        className="bg-slate-800 border-slate-600 text-white"
                        rows={2}
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300 text-sm mb-1 block">Caption</Label>
                      <Input
                        value={panels.find(p => p.id === selectedPanel)?.caption || ''}
                        onChange={(e) => updatePanelText(selectedPanel, 'caption', e.target.value)}
                        placeholder="Narration text..."
                        className="bg-slate-800 border-slate-600 text-white"
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300 text-sm mb-2 block">Add SFX</Label>
                      <div className="flex flex-wrap gap-2">
                        {sfxList.map(sfx => (
                          <button
                            key={sfx}
                            onClick={() => addSfxToPanel(selectedPanel, sfx)}
                            className={`px-2 py-1 text-xs rounded border transition-all ${
                              panels.find(p => p.id === selectedPanel)?.sfx === sfx
                                ? 'bg-red-500 border-red-400 text-white'
                                : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'
                            }`}
                          >
                            {sfx}
                          </button>
                        ))}
                        <button
                          onClick={() => addSfxToPanel(selectedPanel, null)}
                          className="px-2 py-1 text-xs rounded border bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600"
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Preview Area */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4" data-testid="preview-section">
              <h3 className="text-white font-medium mb-4">Preview</h3>
              <div
                ref={previewRef}
                data-testid="preview-canvas"
                className="bg-white rounded-lg min-h-[400px] flex items-center justify-center overflow-auto"
              >
                {panels.length === 0 ? (
                  <div className="text-center text-slate-400 p-8">
                    <Image className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p>Upload and process images to see preview</p>
                  </div>
                ) : (
                  <p className="text-slate-500">Click "Preview" to generate</p>
                )}
              </div>
            </div>

            {/* Export Buttons */}
            {panels.length > 0 && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4" data-testid="export-section">
                <h3 className="text-white font-medium mb-4">Export</h3>
                <div className="grid grid-cols-2 gap-3">
                  <Button
                    onClick={() => exportToPNG(false)}
                    disabled={exporting}
                    data-testid="export-png-btn"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {exporting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                    Export PNG ({getExportCost()} cr)
                  </Button>
                  <Button
                    onClick={() => exportToPDF(false)}
                    disabled={exporting}
                    data-testid="export-pdf-btn"
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {exporting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileText className="w-4 h-4 mr-2" />}
                    Export PDF ({getExportCost()} cr)
                  </Button>
                  <Button
                    onClick={() => exportToPNG(true)}
                    disabled={exporting}
                    variant="outline"
                    data-testid="export-png-no-watermark-btn"
                    className="border-purple-500 text-purple-400 hover:bg-purple-500/20"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    PNG No Watermark (+2 cr)
                  </Button>
                  <Button
                    onClick={() => exportToPDF(true)}
                    disabled={exporting}
                    variant="outline"
                    data-testid="export-pdf-no-watermark-btn"
                    className="border-purple-500 text-purple-400 hover:bg-purple-500/20"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    PDF No Watermark (+2 cr)
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Help Guide */}
      <HelpGuide pageId="comic-studio" />
    </div>
  );
}
