import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, ArrowRight, Download, Image, Palette,
  Wand2, Loader2, CheckCircle, Upload, FileText, Sparkles,
  Coins, BookOpen, Printer, Heart, Crown, Briefcase,
  Puzzle, User, HelpCircle, Check, Camera, Flame, Star,
  ChevronDown, Share2, Wallet
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api, { walletAPI } from '../utils/api';
import ShareCreation from '../components/ShareCreation';

// =============================================================================
// STEP 1: CHOOSE MODE
// =============================================================================
const StepChooseMode = ({ mode, setMode, onNext, trackAnalytics }) => {
  const handleSelect = (selectedMode) => {
    setMode(selectedMode);
    trackAnalytics(1, 'mode_selected', { mode: selectedMode });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">Choose Your Creation Mode</h2>
        <p className="text-slate-400">How would you like to create your coloring book?</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
        {/* Story Mode Card */}
        <button
          onClick={() => handleSelect('story')}
          data-testid="mode-story-btn"
          className={`relative p-6 rounded-2xl border-2 text-left transition-all duration-300 transform hover:scale-[1.02] ${
            mode === 'story'
              ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
              : 'border-slate-700 hover:border-purple-500/50 bg-slate-800/50'
          }`}
        >
          <div className="absolute top-3 right-3 bg-emerald-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1 animate-pulse">
            <Star className="w-3 h-3" />
            Recommended
          </div>
          
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
              <Wand2 className="w-8 h-8 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Generate From Story</h3>
              <p className="text-purple-400 text-sm">AI-powered illustrations</p>
            </div>
          </div>
          
          <div className="space-y-2 mb-4">
            <div className="flex items-center gap-2 text-slate-300 text-sm">
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Write or paste your story</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300 text-sm">
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>AI creates coloring page illustrations</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300 text-sm">
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Get 5-30 page printable PDF</span>
            </div>
          </div>
          
          <div className="bg-slate-900/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-sm">
              <Coins className="w-4 h-4 text-yellow-400" />
              <span className="text-slate-300">Starting from</span>
              <span className="font-bold text-white">10 credits</span>
            </div>
          </div>
          
          {mode === 'story' && (
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
              <div className="bg-purple-500 rounded-full p-1 shadow-lg">
                <Check className="w-4 h-4 text-white" />
              </div>
            </div>
          )}
        </button>

        {/* Photo Mode Card */}
        <button
          onClick={() => handleSelect('photo')}
          data-testid="mode-photo-btn"
          className={`relative p-6 rounded-2xl border-2 text-left transition-all duration-300 transform hover:scale-[1.02] ${
            mode === 'photo'
              ? 'border-cyan-500 bg-cyan-500/20 shadow-lg shadow-cyan-500/20'
              : 'border-slate-700 hover:border-cyan-500/50 bg-slate-800/50'
          }`}
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-xl flex items-center justify-center shadow-lg">
              <Camera className="w-8 h-8 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Convert Photos</h3>
              <p className="text-cyan-400 text-sm">Turn photos into outlines</p>
            </div>
          </div>
          
          <div className="space-y-2 mb-4">
            <div className="flex items-center gap-2 text-slate-300 text-sm">
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Upload your own photos</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300 text-sm">
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Converts to clean line art</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300 text-sm">
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Perfect for personal photos</span>
            </div>
          </div>
          
          <div className="bg-slate-900/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-sm">
              <Coins className="w-4 h-4 text-yellow-400" />
              <span className="text-slate-300">Starting from</span>
              <span className="font-bold text-white">5 credits</span>
            </div>
          </div>
          
          {mode === 'photo' && (
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
              <div className="bg-cyan-500 rounded-full p-1 shadow-lg">
                <Check className="w-4 h-4 text-white" />
              </div>
            </div>
          )}
        </button>
      </div>

      {/* How this works */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 mt-8 max-w-2xl mx-auto">
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-white text-sm">How this works</h4>
            <p className="text-slate-400 text-sm">
              We turn your content into black-and-white printable line art pages that kids can color in.
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-center pt-4">
        <Button
          onClick={onNext}
          disabled={!mode}
          data-testid="step1-continue-btn"
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8 py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
        >
          Continue
          <ArrowRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </div>
  );
};

// =============================================================================
// STEP 2: PROVIDE CONTENT
// =============================================================================
const StepProvideContent = ({ mode, storyData, setStoryData, photoData, setPhotoData, uploadedImages, setUploadedImages, onNext, onBack, trackAnalytics }) => {
  
  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    if (uploadedImages.length + files.length > 10) {
      toast.error('Maximum 10 images allowed');
      return;
    }
    const newImages = files.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      name: file.name
    }));
    setUploadedImages([...uploadedImages, ...newImages]);
    trackAnalytics(2, 'images_uploaded', { count: files.length });
  };

  const removeImage = (index) => {
    const newImages = [...uploadedImages];
    URL.revokeObjectURL(newImages[index].preview);
    newImages.splice(index, 1);
    setUploadedImages(newImages);
  };

  const canProceed = mode === 'story' 
    ? storyData.title.trim() && storyData.description.trim().length >= 10
    : uploadedImages.length > 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
          {mode === 'story' ? 'Tell Us Your Story' : 'Upload Your Photos'}
        </h2>
        <p className="text-slate-400">
          {mode === 'story' 
            ? "Provide the details and we'll create beautiful illustrations" 
            : 'Upload photos to convert into coloring pages'}
        </p>
      </div>

      {mode === 'story' ? (
        <div className="space-y-6 max-w-2xl mx-auto">
          {/* Story Title */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Story Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={storyData.title}
              onChange={(e) => setStoryData({ ...storyData, title: e.target.value })}
              placeholder="e.g., The Adventures of Luna"
              data-testid="story-title-input"
              className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition-all"
            />
          </div>

          {/* Age Group & Style */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Age Group</label>
              <Select
                value={storyData.ageGroup}
                onValueChange={(value) => setStoryData({ ...storyData, ageGroup: value })}
              >
                <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white h-12 rounded-xl" data-testid="age-group-select">
                  <SelectValue placeholder="Select age group" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="2-4" className="text-white hover:bg-slate-700">2-4 years (Toddler)</SelectItem>
                  <SelectItem value="4-6" className="text-white hover:bg-slate-700">4-6 years (Preschool)</SelectItem>
                  <SelectItem value="6-8" className="text-white hover:bg-slate-700">6-8 years (Early Reader)</SelectItem>
                  <SelectItem value="8-12" className="text-white hover:bg-slate-700">8-12 years (Kids)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Illustration Style</label>
              <Select
                value={storyData.illustrationStyle}
                onValueChange={(value) => setStoryData({ ...storyData, illustrationStyle: value })}
              >
                <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white h-12 rounded-xl" data-testid="style-select">
                  <SelectValue placeholder="Select style" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="cartoon" className="text-white hover:bg-slate-700">Cartoon</SelectItem>
                  <SelectItem value="realistic" className="text-white hover:bg-slate-700">Realistic</SelectItem>
                  <SelectItem value="whimsical" className="text-white hover:bg-slate-700">Whimsical</SelectItem>
                  <SelectItem value="simple" className="text-white hover:bg-slate-700">Simple Lines</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Number of Pages */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Number of Pages</label>
            <Select
              value={storyData.pageCount}
              onValueChange={(value) => setStoryData({ ...storyData, pageCount: value })}
            >
              <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white h-12 rounded-xl" data-testid="pages-select">
                <SelectValue placeholder="Select pages" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="5" className="text-white hover:bg-slate-700">5 pages - 10 credits</SelectItem>
                <SelectItem value="10" className="text-white hover:bg-slate-700">10 pages - 18 credits (Save 10%)</SelectItem>
                <SelectItem value="20" className="text-white hover:bg-slate-700">20 pages - 32 credits (Most Popular)</SelectItem>
                <SelectItem value="30" className="text-white hover:bg-slate-700">30 pages - 45 credits (Best Value)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Story Description */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Story Description <span className="text-red-400">*</span>
            </label>
            <textarea
              value={storyData.description}
              onChange={(e) => setStoryData({ ...storyData, description: e.target.value.slice(0, 2000) })}
              placeholder="Describe your story in detail. Include characters, setting, and key scenes you'd like illustrated..."
              rows={6}
              data-testid="story-description-input"
              className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
            />
            <p className="text-xs text-slate-500 mt-1">{storyData.description.length}/2000 characters</p>
          </div>
        </div>
      ) : (
        <div className="space-y-6 max-w-2xl mx-auto">
          {/* Photo Settings */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Outline Thickness</label>
              <Select
                value={photoData.outlineStrength.toString()}
                onValueChange={(value) => setPhotoData({ ...photoData, outlineStrength: parseInt(value) })}
              >
                <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white h-12 rounded-xl">
                  <SelectValue placeholder="Select thickness" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="25" className="text-white hover:bg-slate-700">Light (Simple)</SelectItem>
                  <SelectItem value="50" className="text-white hover:bg-slate-700">Medium (Recommended)</SelectItem>
                  <SelectItem value="75" className="text-white hover:bg-slate-700">Strong (Detailed)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 h-12">
              <span className="text-slate-300 text-sm">Remove Background</span>
              <button
                onClick={() => setPhotoData({ ...photoData, removeBackground: !photoData.removeBackground })}
                data-testid="remove-bg-toggle"
                className={`w-12 h-6 rounded-full transition-all duration-300 ${
                  photoData.removeBackground ? 'bg-purple-500' : 'bg-slate-600'
                }`}
              >
                <div className={`w-5 h-5 bg-white rounded-full transform transition-transform shadow-md ${
                  photoData.removeBackground ? 'translate-x-6' : 'translate-x-0.5'
                }`} />
              </button>
            </div>
          </div>

          {/* Upload Area */}
          <div
            className="border-2 border-dashed border-slate-600 rounded-2xl p-8 text-center hover:border-cyan-500 transition-all duration-300 cursor-pointer bg-slate-800/30"
            onClick={() => document.getElementById('photo-upload').click()}
            data-testid="photo-upload-area"
          >
            <input
              id="photo-upload"
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleImageUpload}
            />
            <div className="w-16 h-16 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Upload className="w-8 h-8 text-cyan-400" />
            </div>
            <p className="text-white font-medium mb-1">Click to upload photos</p>
            <p className="text-slate-400 text-sm">PNG, JPG up to 10MB each (max 10 photos)</p>
          </div>

          {/* Uploaded Images Preview */}
          {uploadedImages.length > 0 && (
            <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
              {uploadedImages.map((img, index) => (
                <div key={index} className="relative group aspect-square">
                  <img
                    src={img.preview}
                    alt={img.name}
                    className="w-full h-full object-cover rounded-xl border border-slate-700"
                  />
                  <button
                    onClick={(e) => { e.stopPropagation(); removeImage(index); }}
                    className="absolute top-1 right-1 bg-red-500 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-all duration-200 hover:bg-red-600"
                  >
                    <span className="text-white text-xs font-bold">✕</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* How this works */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 max-w-2xl mx-auto">
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-white text-sm">How this works</h4>
            <p className="text-slate-400 text-sm">
              {mode === 'story'
                ? 'Our AI reads your story and creates scene-by-scene coloring page illustrations.'
                : 'We convert your photos into clean line art perfect for coloring.'}
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between max-w-2xl mx-auto pt-4">
        <Button variant="outline" onClick={onBack} className="border-slate-600 text-white hover:bg-slate-800" data-testid="step2-back-btn">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={onNext}
          disabled={!canProceed}
          data-testid="step2-continue-btn"
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
};

// =============================================================================
// STEP 3: CUSTOMIZE BOOK
// =============================================================================
const StepCustomize = ({ mode, storyData, customize, setCustomize, pricing, userPlan, costBreakdown, onNext, onBack, trackAnalytics }) => {
  
  const toggleAddon = (addonId) => {
    const addon = pricing?.addons?.[addonId];
    if (addon?.locked) {
      toast.error(`Upgrade to Pro to unlock ${addon.name}`);
      return;
    }

    const newAddons = customize.addons.includes(addonId)
      ? customize.addons.filter(a => a !== addonId)
      : [...customize.addons, addonId];
    
    setCustomize({ ...customize, addons: newAddons });
    trackAnalytics(3, 'addon_toggled', { addon: addonId, enabled: !customize.addons.includes(addonId) });
  };

  const getAddonIcon = (iconName) => {
    const icons = {
      puzzle: Puzzle,
      user: User,
      heart: Heart,
      crown: Crown,
      printer: Printer,
      briefcase: Briefcase
    };
    return icons[iconName] || Sparkles;
  };

  const addons = pricing?.addons || {};

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">Customize Your Book</h2>
        <p className="text-slate-400">Choose your options and add extras</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
        {/* Options Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Paper Size */}
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-400" />
              Paper Size
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {['A4', 'US Letter'].map((size) => (
                <button
                  key={size}
                  onClick={() => setCustomize({ ...customize, paperSize: size })}
                  data-testid={`paper-size-${size.toLowerCase().replace(' ', '-')}`}
                  className={`p-4 rounded-xl border-2 text-center transition-all duration-300 ${
                    customize.paperSize === size
                      ? 'border-purple-500 bg-purple-500/20'
                      : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                  }`}
                >
                  <div className="font-semibold text-white">{size}</div>
                  <div className="text-xs text-slate-400">
                    {size === 'A4' ? '210 × 297 mm' : '8.5 × 11 in'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Add-ons */}
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              Add-ons (High Profit Options)
            </h3>
            <div className="grid md:grid-cols-2 gap-3">
              {Object.entries(addons).map(([key, addon]) => {
                const Icon = getAddonIcon(addon.icon);
                const isSelected = customize.addons.includes(key);
                const isLocked = addon.locked;

                return (
                  <button
                    key={key}
                    onClick={() => toggleAddon(key)}
                    data-testid={`addon-${key}`}
                    className={`relative p-4 rounded-xl border-2 text-left transition-all duration-300 ${
                      isSelected
                        ? 'border-purple-500 bg-purple-500/20'
                        : isLocked
                        ? 'border-slate-700 bg-slate-800/30 opacity-60 cursor-not-allowed'
                        : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                    }`}
                  >
                    {isLocked && (
                      <div className="absolute top-2 right-2 bg-yellow-500/20 rounded-full p-1">
                        <Crown className="w-3 h-3 text-yellow-500" />
                      </div>
                    )}
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-purple-500' : 'bg-slate-700'
                      }`}>
                        <Icon className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-white truncate">{addon.name}</div>
                        <div className="text-xs text-slate-400 truncate">{addon.description}</div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="font-semibold text-purple-400">+{addon.credits}</div>
                        <div className="text-xs text-slate-500">credits</div>
                      </div>
                    </div>
                    {isSelected && !isLocked && (
                      <div className="absolute top-2 right-2 bg-purple-500 rounded-full p-0.5">
                        <Check className="w-3 h-3 text-white" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Personalization Fields */}
          {customize.addons.includes('personalized_cover') && (
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <User className="w-5 h-5 text-purple-400" />
                Personalization
              </h3>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Child's Name (for cover)</label>
                <input
                  type="text"
                  value={customize.childName}
                  onChange={(e) => setCustomize({ ...customize, childName: e.target.value.slice(0, 50) })}
                  placeholder="e.g., Emma"
                  data-testid="child-name-input"
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none transition-all"
                />
              </div>
            </div>
          )}

          {customize.addons.includes('dedication_page') && (
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Heart className="w-5 h-5 text-pink-400" />
                Dedication Message
              </h3>
              <textarea
                value={customize.dedication}
                onChange={(e) => setCustomize({ ...customize, dedication: e.target.value.slice(0, 300) })}
                placeholder="Write a special message for your little one..."
                rows={3}
                data-testid="dedication-input"
                className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none transition-all resize-none"
              />
              <p className="text-xs text-slate-500 mt-1">{customize.dedication.length}/300</p>
            </div>
          )}
        </div>

        {/* Cost Summary Column - Sticky */}
        <div className="lg:col-span-1">
          <div className="bg-gradient-to-b from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-5 lg:sticky lg:top-24">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Coins className="w-5 h-5 text-yellow-400" />
              Live Credit Calculator
            </h3>

            {costBreakdown ? (
              <div className="space-y-3">
                <div className="flex justify-between text-slate-300">
                  <span>{costBreakdown.base?.label || 'Base cost'}</span>
                  <span>{costBreakdown.base?.credits || 0} credits</span>
                </div>

                {costBreakdown.addons?.map((addon) => (
                  <div key={addon.id} className="flex justify-between text-slate-400 text-sm">
                    <span>+ {addon.name}</span>
                    <span>+{addon.credits}</span>
                  </div>
                ))}

                <div className="border-t border-slate-700 pt-3">
                  <div className="flex justify-between text-slate-300">
                    <span>Subtotal</span>
                    <span>{costBreakdown.subtotal || 0} credits</span>
                  </div>

                  {costBreakdown.discount?.percent > 0 && (
                    <div className="flex justify-between text-emerald-400 text-sm mt-1">
                      <span>{costBreakdown.discount.plan} discount ({costBreakdown.discount.percent}%)</span>
                      <span>-{costBreakdown.discount.amount}</span>
                    </div>
                  )}
                </div>

                <div className="border-t border-slate-700 pt-3">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-bold text-white">Total</span>
                    <span className="text-2xl font-bold text-purple-400">{costBreakdown.total || 0} credits</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-purple-400 mx-auto" />
              </div>
            )}

            {/* Best Value Tip */}
            <div className="mt-4 p-3 bg-gradient-to-r from-orange-500/10 to-pink-500/10 border border-orange-500/20 rounded-xl">
              <div className="flex items-center gap-2 text-orange-300 text-sm">
                <Flame className="w-4 h-4" />
                <span>Best Value: 20 pages + Cover saves 15%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* How this works */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 max-w-2xl mx-auto">
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-white text-sm">How this works</h4>
            <p className="text-slate-400 text-sm">
              Choose your book size and add extras to make it special. Credits are only charged after successful generation.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between max-w-6xl mx-auto pt-4">
        <Button variant="outline" onClick={onBack} className="border-slate-600 text-white hover:bg-slate-800" data-testid="step3-back-btn">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={onNext}
          data-testid="step3-continue-btn"
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8"
        >
          Preview Book
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
};

// =============================================================================
// STEP 4: PREVIEW
// =============================================================================
const StepPreview = ({ mode, storyData, costBreakdown, userPlan, onGenerate, onBack, generating }) => {
  const isWatermarked = userPlan === 'free';

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">Preview Your Book</h2>
        <p className="text-slate-400">See a sample of what your coloring book will look like</p>
      </div>

      {/* Preview Area */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6 max-w-4xl mx-auto">
        <div className="grid md:grid-cols-2 gap-6">
          {/* Sample Pages */}
          <div className="space-y-4">
            <h3 className="font-semibold text-white">Sample Preview Pages</h3>
            <div className="grid grid-cols-2 gap-4">
              {[1, 2].map((page) => (
                <div 
                  key={page}
                  className="aspect-[3/4] bg-white rounded-xl flex items-center justify-center relative overflow-hidden shadow-lg"
                >
                  <div className="text-center text-slate-400 p-4">
                    <BookOpen className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                    <p className="text-sm font-medium text-slate-500">Page {page}</p>
                    {mode === 'story' && storyData.title && (
                      <p className="text-xs text-slate-400 mt-1">{storyData.title}</p>
                    )}
                  </div>
                  {isWatermarked && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/5">
                      <span className="text-3xl font-bold text-black/10 rotate-[-30deg] select-none">PREVIEW</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <p className="text-sm text-slate-400">
              {isWatermarked 
                ? '* Preview has watermark. Final PDF will be clean for paid plans.'
                : '* This is a preview. Final PDF will include all pages.'}
            </p>
          </div>

          {/* Summary */}
          <div className="space-y-4">
            <h3 className="font-semibold text-white">Your Order Summary</h3>
            <div className="bg-slate-900/50 rounded-xl p-4 space-y-3 border border-slate-700/50">
              {costBreakdown && (
                <>
                  <div className="flex justify-between text-slate-300">
                    <span>{costBreakdown.base?.label || 'Base'}</span>
                    <span>{costBreakdown.base?.credits || 0} credits</span>
                  </div>
                  {costBreakdown.addons?.map((addon) => (
                    <div key={addon.id} className="flex justify-between text-slate-400 text-sm">
                      <span>+ {addon.name}</span>
                      <span>+{addon.credits}</span>
                    </div>
                  ))}
                  {costBreakdown.discount?.percent > 0 && (
                    <div className="flex justify-between text-emerald-400 text-sm">
                      <span>Discount ({costBreakdown.discount.percent}%)</span>
                      <span>-{costBreakdown.discount.amount}</span>
                    </div>
                  )}
                  <div className="border-t border-slate-700 pt-3 flex justify-between">
                    <span className="font-bold text-white">Total</span>
                    <span className="font-bold text-purple-400 text-lg">{costBreakdown.total} credits</span>
                  </div>
                </>
              )}
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
              <p className="text-amber-300 text-sm flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                This is a preview. Click below to generate your full coloring book.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* How this works */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 max-w-2xl mx-auto">
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-white text-sm">How this works</h4>
            <p className="text-slate-400 text-sm">
              Preview shows sample pages. Your credits will only be charged when you generate the full book.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between max-w-4xl mx-auto pt-4">
        <Button variant="outline" onClick={onBack} className="border-slate-600 text-white hover:bg-slate-800" data-testid="step4-back-btn">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={onGenerate}
          disabled={generating}
          data-testid="generate-book-btn"
          className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 px-8 py-3 text-lg disabled:opacity-50"
        >
          {generating ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5 mr-2" />
              Generate Full Book ({costBreakdown?.total || 0} credits)
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

// =============================================================================
// STEP 5: DOWNLOAD
// =============================================================================
const StepDownload = ({ generationResult, storyTitle, onStartNew, onUpgradeHD }) => {
  const [showShare, setShowShare] = useState(false);
  
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center mb-8">
        <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
          <CheckCircle className="w-10 h-10 text-emerald-400" />
        </div>
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">Your Coloring Book is Ready!</h2>
        <p className="text-slate-400">Download your creation and start coloring</p>
      </div>

      {/* Download Options */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6 max-w-3xl mx-auto">
        <div className="grid md:grid-cols-3 gap-4">
          <button 
            data-testid="download-pdf-btn"
            className="p-6 bg-gradient-to-br from-purple-600 to-pink-600 rounded-2xl text-white hover:scale-105 transition-all duration-300 shadow-lg shadow-purple-500/20"
          >
            <Download className="w-10 h-10 mx-auto mb-3" />
            <div className="font-semibold text-lg">Download PDF</div>
            <div className="text-sm text-white/70">Standard Quality</div>
          </button>

          <button 
            onClick={onUpgradeHD}
            data-testid="download-hd-btn"
            className="p-6 bg-slate-700/50 border-2 border-slate-600 rounded-2xl text-white hover:border-purple-500 hover:bg-slate-700 transition-all duration-300"
          >
            <Printer className="w-10 h-10 mx-auto mb-3 text-purple-400" />
            <div className="font-semibold">HD Print PDF</div>
            <div className="text-sm text-slate-400">+5 credits</div>
          </button>

          {/* Share Button - Opens ShareCreation Modal */}
          <ShareCreation
            type="COLORING_BOOK"
            title={storyTitle || "My Coloring Book"}
            preview="A beautiful AI-generated coloring book with unique illustrations perfect for kids!"
            generationId={generationResult?.generationId}
            contentType="coloring_book"
          />
        </div>
      </div>

      {/* Generation Details */}
      <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5 max-w-3xl mx-auto">
        <h3 className="font-semibold text-white mb-3">Generation Details</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="bg-slate-900/50 rounded-xl p-3">
            <span className="text-slate-400">Credits Used:</span>
            <span className="text-white ml-2 font-semibold">{generationResult?.creditsCharged || 0}</span>
          </div>
          <div className="bg-slate-900/50 rounded-xl p-3">
            <span className="text-slate-400">New Balance:</span>
            <span className="text-emerald-400 ml-2 font-semibold">{generationResult?.newBalance || 0}</span>
          </div>
        </div>
      </div>

      {/* Commercial License Upsell */}
      <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-2xl p-5 max-w-3xl mx-auto">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-purple-400" />
              Want to sell your creations?
            </h3>
            <p className="text-slate-400 text-sm">Add commercial license for just 10 credits</p>
          </div>
          <Button variant="outline" className="border-purple-500 text-purple-400 hover:bg-purple-500/20" data-testid="add-license-btn">
            Add License
          </Button>
        </div>
      </div>

      {/* Create Another */}
      <div className="flex justify-center pt-4">
        <Button
          onClick={onStartNew}
          variant="outline"
          className="border-slate-600 text-white hover:bg-slate-800"
          data-testid="create-another-btn"
        >
          <BookOpen className="w-4 h-4 mr-2" />
          Create Another Book
        </Button>
      </div>
    </div>
  );
};

// =============================================================================
// MAIN WIZARD COMPONENT
// =============================================================================
export default function ColoringBookWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pricing, setPricing] = useState(null);
  const [userPlan, setUserPlan] = useState('free');
  const [generating, setGenerating] = useState(false);
  const [generationResult, setGenerationResult] = useState(null);
  const [costBreakdown, setCostBreakdown] = useState(null);
  const [wallet, setWallet] = useState({ credits: 0 });

  // Form state
  const [mode, setMode] = useState(null);
  const [storyData, setStoryData] = useState({
    title: '',
    ageGroup: '4-6',
    description: '',
    illustrationStyle: 'cartoon',
    pageCount: '20'
  });
  const [photoData, setPhotoData] = useState({
    outlineStrength: 50,
    removeBackground: false
  });
  const [uploadedImages, setUploadedImages] = useState([]);
  const [customize, setCustomize] = useState({
    paperSize: 'A4',
    addons: ['personalized_cover'],  // Pre-selected for revenue optimization
    childName: '',
    dedication: ''
  });

  const navigate = useNavigate();

  // Initialize wizard on mount
  useEffect(() => {
    initializeWizard();
  }, []);

  // Recalculate cost when customize options change
  useEffect(() => {
    if (currentStep >= 3 && mode) {
      calculateCost();
    }
  }, [customize, currentStep, mode, storyData.pageCount]);

  const initializeWizard = async () => {
    try {
      const [pricingRes, walletRes, sessionRes] = await Promise.all([
        api.get('/api/coloring-book/pricing'),
        walletAPI.getWallet().catch(() => ({ data: { credits: 0 } })),
        api.post('/api/coloring-book/session/start')
      ]);

      if (pricingRes.data.success !== false) {
        setPricing(pricingRes.data);
        setUserPlan(pricingRes.data.subscription?.plan || 'free');
      }

      setWallet(walletRes.data);

      if (sessionRes.data.success) {
        setSessionId(sessionRes.data.sessionId);
      }
    } catch (error) {
      console.error('Failed to initialize:', error);
      toast.error('Failed to load. Please refresh.');
    } finally {
      setLoading(false);
    }
  };

  const calculateCost = async () => {
    try {
      // Determine the option based on mode
      const pageOption = mode === 'story' ? `${storyData.pageCount}_pages` : '5_images';
      const imageOption = mode === 'photo' ? `${uploadedImages.length || 1}_image${uploadedImages.length !== 1 ? 's' : ''}` : null;
      const option = mode === 'story' ? pageOption : (imageOption || '1_image');
      
      const params = new URLSearchParams();
      customize.addons.forEach(addon => params.append('addons', addon));
      
      const res = await api.post(
        `/api/coloring-book/calculate?mode=${mode}&option=${option}&${params.toString()}`
      );
      
      if (res.data.success) {
        setCostBreakdown(res.data.breakdown);
      }
    } catch (error) {
      console.error('Failed to calculate cost:', error);
    }
  };

  const trackAnalytics = async (step, action, data = {}) => {
    try {
      await api.post('/api/coloring-book/analytics/track', {
        sessionId,
        step,
        action,
        data
      });
    } catch (error) {
      console.error('Analytics tracking failed:', error);
    }
  };

  const handleGenerate = async () => {
    if (!costBreakdown) {
      toast.error('Please wait for cost calculation');
      return;
    }

    if (wallet.credits < costBreakdown.total) {
      toast.error(`Insufficient credits. Need ${costBreakdown.total}, have ${wallet.credits}`);
      navigate('/app/billing');
      return;
    }

    setGenerating(true);
    try {
      const pageOption = `${storyData.pageCount}_pages`;
      const imageCount = uploadedImages.length || 1;
      const imageOption = imageCount === 1 ? '1_image' : imageCount <= 5 ? '5_images' : '10_images';

      const res = await api.post('/api/coloring-book/generate/full', {
        sessionId,
        mode,
        storyData: mode === 'story' ? storyData : null,
        photoData: mode === 'photo' ? photoData : null,
        customize: {
          ...customize,
          mode,
          pageOption: mode === 'story' ? pageOption : null,
          imageOption: mode === 'photo' ? imageOption : null
        }
      });

      if (res.data.success) {
        setGenerationResult(res.data);
        setCurrentStep(5);
        toast.success('Coloring book generated successfully!');
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail?.error === 'insufficient_credits') {
        toast.error(`Need ${detail.required} credits. You have ${detail.available}.`);
        navigate('/app/billing');
      } else {
        toast.error('Generation failed. Please try again.');
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleStartNew = () => {
    setCurrentStep(1);
    setMode(null);
    setStoryData({ title: '', ageGroup: '4-6', description: '', illustrationStyle: 'cartoon', pageCount: '20' });
    setPhotoData({ outlineStrength: 50, removeBackground: false });
    setUploadedImages([]);
    setCustomize({ paperSize: 'A4', addons: ['personalized_cover'], childName: '', dedication: '' });
    setGenerationResult(null);
    setCostBreakdown(null);
    initializeWizard();
  };

  const goToStep = (step) => {
    trackAnalytics(currentStep, 'step_completed', { next_step: step });
    setCurrentStep(step);
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/20 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading Coloring Book Creator...</p>
        </div>
      </div>
    );
  }

  const steps = [
    { num: 1, label: 'Mode' },
    { num: 2, label: 'Content' },
    { num: 3, label: 'Customize' },
    { num: 4, label: 'Preview' },
    { num: 5, label: 'Download' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white hover:bg-slate-800" data-testid="back-to-dashboard">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
                <Palette className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Coloring Book Creator</h1>
                <p className="text-xs text-slate-400 hidden sm:block">Create beautiful printable coloring books</p>
              </div>
            </div>
          </div>
          
          {/* Wallet Display */}
          <div className="flex items-center gap-2 bg-slate-800/50 rounded-full px-4 py-2 border border-slate-700" data-testid="wallet-balance">
            <Wallet className="w-4 h-4 text-purple-400" />
            <span className="font-bold text-white">{wallet.credits || 0}</span>
            <span className="text-xs text-slate-400 hidden sm:inline">credits</span>
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="bg-slate-900/50 border-b border-slate-800/50">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <React.Fragment key={step.num}>
                <div className="flex flex-col items-center">
                  <div 
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all duration-500 ${
                      currentStep > step.num
                        ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                        : currentStep === step.num
                        ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/30'
                        : 'bg-slate-700 text-slate-400'
                    }`}
                    data-testid={`step-indicator-${step.num}`}
                  >
                    {currentStep > step.num ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      step.num
                    )}
                  </div>
                  <span className={`text-xs mt-2 font-medium hidden sm:block ${
                    currentStep >= step.num ? 'text-white' : 'text-slate-500'
                  }`}>
                    {step.label}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div className={`flex-1 h-1 mx-2 rounded-full transition-all duration-500 ${
                    currentStep > step.num ? 'bg-emerald-500' : 'bg-slate-700'
                  }`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {currentStep === 1 && (
          <StepChooseMode
            mode={mode}
            setMode={setMode}
            onNext={() => goToStep(2)}
            trackAnalytics={trackAnalytics}
          />
        )}

        {currentStep === 2 && (
          <StepProvideContent
            mode={mode}
            storyData={storyData}
            setStoryData={setStoryData}
            photoData={photoData}
            setPhotoData={setPhotoData}
            uploadedImages={uploadedImages}
            setUploadedImages={setUploadedImages}
            onNext={() => goToStep(3)}
            onBack={() => goToStep(1)}
            trackAnalytics={trackAnalytics}
          />
        )}

        {currentStep === 3 && (
          <StepCustomize
            mode={mode}
            storyData={storyData}
            customize={customize}
            setCustomize={setCustomize}
            pricing={pricing}
            userPlan={userPlan}
            costBreakdown={costBreakdown}
            onNext={() => goToStep(4)}
            onBack={() => goToStep(2)}
            trackAnalytics={trackAnalytics}
          />
        )}

        {currentStep === 4 && (
          <StepPreview
            mode={mode}
            storyData={storyData}
            costBreakdown={costBreakdown}
            userPlan={userPlan}
            onGenerate={handleGenerate}
            onBack={() => goToStep(3)}
            generating={generating}
          />
        )}

        {currentStep === 5 && (
          <StepDownload
            generationResult={generationResult}
            onStartNew={handleStartNew}
            onUpgradeHD={() => toast.info('HD upgrade coming soon!')}
          />
        )}
      </main>

      {/* Footer Disclaimer */}
      <footer className="border-t border-slate-800/50 py-4 mt-8">
        <div className="max-w-4xl mx-auto px-4">
          <p className="text-xs text-slate-500 text-center">
            <strong>100% Original Content:</strong> All illustrations are AI-generated and copyright-free. 
            Upload only images you own or have permission to use. Safe and family-friendly content guaranteed.
          </p>
        </div>
      </footer>
    </div>
  );
}
