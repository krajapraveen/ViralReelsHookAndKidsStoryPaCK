/**
 * Loading States Component
 * Provides detailed, engaging loading indicators for generation features
 */
import React, { useState, useEffect } from 'react';
import { Loader2, Sparkles, Wand2, Film, Image, Mic, Check, AlertCircle } from 'lucide-react';
import { Progress } from './ui/progress';

// Loading messages for different generation types
const LOADING_MESSAGES = {
  story: [
    "Analyzing your story structure...",
    "Identifying characters and settings...",
    "Breaking down into scenes...",
    "Crafting visual descriptions...",
    "Generating character profiles...",
    "Finalizing scene prompts..."
  ],
  image: [
    "Preparing your visual prompt...",
    "Initializing AI image generator...",
    "Creating artistic composition...",
    "Applying style and effects...",
    "Rendering high-quality output...",
    "Finalizing your image..."
  ],
  voice: [
    "Processing narration text...",
    "Selecting voice characteristics...",
    "Synthesizing speech patterns...",
    "Adding natural intonations...",
    "Rendering audio track...",
    "Finalizing voice output..."
  ],
  video: [
    "Preparing scene assets...",
    "Synchronizing audio and visuals...",
    "Applying transitions and effects...",
    "Adding background music...",
    "Rendering final video...",
    "Encoding and optimizing..."
  ],
  comic: [
    "Analyzing your photo...",
    "Applying comic style filter...",
    "Enhancing artistic details...",
    "Adding comic book effects...",
    "Finalizing transformation...",
    "Preparing download..."
  ],
  reel: [
    "Analyzing your topic...",
    "Generating viral hooks...",
    "Crafting engaging script...",
    "Creating captions...",
    "Generating hashtags...",
    "Finalizing content pack..."
  ],
  default: [
    "Processing your request...",
    "AI is working its magic...",
    "Almost there...",
    "Finalizing output..."
  ]
};

// Animated dots component
const AnimatedDots = () => {
  const [dots, setDots] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, []);
  
  return <span className="inline-block w-6">{dots}</span>;
};

// Main Loading State Component
export const GenerationLoader = ({ 
  type = 'default', 
  progress = 0, 
  stage = 0,
  estimatedTime = null,
  error = null,
  className = ''
}) => {
  const messages = LOADING_MESSAGES[type] || LOADING_MESSAGES.default;
  const currentMessage = messages[Math.min(stage, messages.length - 1)];
  
  const icons = {
    story: Sparkles,
    image: Image,
    voice: Mic,
    video: Film,
    comic: Wand2,
    reel: Sparkles,
    default: Loader2
  };
  
  const Icon = icons[type] || icons.default;
  
  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center p-8 ${className}`}>
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-red-400 text-center">{error}</p>
      </div>
    );
  }
  
  return (
    <div className={`flex flex-col items-center justify-center p-8 ${className}`}>
      {/* Animated Icon */}
      <div className="relative mb-6">
        <div className="absolute inset-0 bg-purple-500/20 rounded-full blur-xl animate-pulse" />
        <div className="relative bg-gradient-to-br from-purple-500 to-pink-500 p-4 rounded-full">
          <Icon className="w-8 h-8 text-white animate-pulse" />
        </div>
      </div>
      
      {/* Progress Bar */}
      <div className="w-full max-w-xs mb-4">
        <Progress value={progress} className="h-2" />
      </div>
      
      {/* Progress Text */}
      <p className="text-lg font-medium text-white mb-2">
        {progress}% Complete
      </p>
      
      {/* Current Stage Message */}
      <p className="text-slate-400 text-center flex items-center">
        {currentMessage}<AnimatedDots />
      </p>
      
      {/* Estimated Time */}
      {estimatedTime && (
        <p className="text-slate-500 text-sm mt-2">
          Estimated time: ~{estimatedTime}
        </p>
      )}
      
      {/* Stage Indicators */}
      <div className="flex gap-1 mt-4">
        {messages.map((_, index) => (
          <div
            key={index}
            className={`w-2 h-2 rounded-full transition-colors ${
              index <= stage ? 'bg-purple-500' : 'bg-slate-700'
            }`}
          />
        ))}
      </div>
    </div>
  );
};

// Skeleton Loader for lists/grids
export const SkeletonLoader = ({ count = 3, type = 'card' }) => {
  const renderSkeleton = () => {
    switch (type) {
      case 'card':
        return (
          <div className="bg-slate-800/50 rounded-xl p-4 animate-pulse">
            <div className="h-32 bg-slate-700/50 rounded-lg mb-4" />
            <div className="h-4 bg-slate-700/50 rounded w-3/4 mb-2" />
            <div className="h-3 bg-slate-700/50 rounded w-1/2" />
          </div>
        );
      case 'list':
        return (
          <div className="flex items-center gap-4 p-4 bg-slate-800/50 rounded-xl animate-pulse">
            <div className="w-12 h-12 bg-slate-700/50 rounded-lg" />
            <div className="flex-1">
              <div className="h-4 bg-slate-700/50 rounded w-1/2 mb-2" />
              <div className="h-3 bg-slate-700/50 rounded w-1/3" />
            </div>
          </div>
        );
      case 'text':
        return (
          <div className="space-y-2 animate-pulse">
            <div className="h-4 bg-slate-700/50 rounded w-full" />
            <div className="h-4 bg-slate-700/50 rounded w-5/6" />
            <div className="h-4 bg-slate-700/50 rounded w-4/6" />
          </div>
        );
      default:
        return null;
    }
  };
  
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i}>{renderSkeleton()}</div>
      ))}
    </div>
  );
};

// Inline Loading Button
export const LoadingButton = ({ 
  loading = false, 
  children, 
  loadingText = 'Processing...', 
  ...props 
}) => {
  return (
    <button {...props} disabled={loading || props.disabled}>
      {loading ? (
        <>
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          {loadingText}
        </>
      ) : children}
    </button>
  );
};

// Success State
export const SuccessState = ({ message = 'Complete!', onContinue }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="bg-green-500/20 p-4 rounded-full mb-4">
        <Check className="w-8 h-8 text-green-500" />
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">{message}</h3>
      {onContinue && (
        <button
          onClick={onContinue}
          className="mt-4 px-6 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
        >
          Continue
        </button>
      )}
    </div>
  );
};

export default GenerationLoader;
