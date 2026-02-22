import React, { useState, useEffect, createContext, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { X, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

// Tour context
const TourContext = createContext(null);

// Tour steps configuration
const TOUR_STEPS = [
  {
    id: 'welcome',
    title: 'Welcome to CreatorStudio AI!',
    content: "Let's take a quick tour to help you get started with creating viral content. This will only take about 2 minutes.",
    target: null,
    page: '/app',
    position: 'center'
  },
  {
    id: 'credits',
    title: 'Your Credits',
    content: 'This shows your available credits. New users get 100 free credits to start! Different features cost different amounts of credits.',
    target: '[data-tour="credits-display"]',
    page: '/app',
    position: 'bottom'
  },
  {
    id: 'reel-generator',
    title: 'Reel Generator',
    content: 'Create viral reel scripts with hooks, captions, and hashtags in seconds. Perfect for Instagram, TikTok, and YouTube Shorts!',
    target: '[data-tour="reel-generator-card"]',
    page: '/app',
    position: 'right'
  },
  {
    id: 'story-generator',
    title: 'Kids Story Generator',
    content: 'Generate complete kids story video packs with scenes, voiceover scripts, and image prompts. Great for YouTube kids channels!',
    target: '[data-tour="story-generator-card"]',
    page: '/app',
    position: 'left'
  },
  {
    id: 'genstudio',
    title: 'GenStudio AI',
    content: 'Our AI generation suite! Create images from text, convert images to videos, and remix existing videos with AI.',
    target: '[data-tour="genstudio-card"]',
    page: '/app',
    position: 'bottom'
  },
  {
    id: 'creator-tools',
    title: 'Creator Tools',
    content: 'Access 30-day content calendars, carousel generators, hashtag banks, trending topics, and more! Some tools are FREE!',
    target: '[data-tour="creator-tools-card"]',
    page: '/app',
    position: 'bottom'
  },
  {
    id: 'complete',
    title: "You're All Set!",
    content: 'That\'s the basics! Look for the purple ? button on any page for contextual help. Ready to create amazing content?',
    target: null,
    page: '/app',
    position: 'center'
  }
];

// Custom hook for tour
export function useAppTour() {
  const context = useContext(TourContext);
  if (!context) {
    return { restartTour: () => {}, isActive: false };
  }
  return context;
}

// Tour Provider Component
export function TourProvider({ children }) {
  const [isActive, setIsActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [hasCompleted, setHasCompleted] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    checkTourStatus();
  }, []);

  const checkTourStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await api.get('/api/auth/me');
      const user = response.data;
      
      if (!user.tourCompleted && location.pathname === '/app') {
        setHasCompleted(false);
        setTimeout(() => startTour(), 1500);
      }
    } catch (error) {
      console.error('Tour status check failed:', error);
    }
  };

  const startTour = () => {
    setCurrentStep(0);
    setIsActive(true);
    navigate('/app');
  };

  const restartTour = () => {
    startTour();
  };

  const nextStep = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      completeTour();
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const skipTour = () => {
    completeTour();
  };

  const completeTour = async () => {
    setIsActive(false);
    setHasCompleted(true);
    
    try {
      await api.put('/api/auth/profile', { tourCompleted: true });
    } catch (error) {
      console.error('Failed to save tour status:', error);
    }
  };

  const value = {
    isActive,
    currentStep,
    restartTour,
    nextStep,
    prevStep,
    skipTour,
    completeTour
  };

  return (
    <TourContext.Provider value={value}>
      {children}
      {isActive && <TourOverlay />}
    </TourContext.Provider>
  );
}

// Tour Overlay Component
function TourOverlay() {
  const { currentStep, nextStep, prevStep, skipTour } = useAppTour();
  const step = TOUR_STEPS[currentStep];
  const [position, setPosition] = useState({ top: '50%', left: '50%' });
  const [targetRect, setTargetRect] = useState(null);

  useEffect(() => {
    if (step.target) {
      const element = document.querySelector(step.target);
      if (element) {
        const rect = element.getBoundingClientRect();
        setTargetRect(rect);
        
        // Calculate tooltip position based on step.position
        let top, left;
        switch (step.position) {
          case 'top':
            top = rect.top - 10;
            left = rect.left + rect.width / 2;
            break;
          case 'bottom':
            top = rect.bottom + 20;
            left = rect.left + rect.width / 2;
            break;
          case 'left':
            top = rect.top + rect.height / 2;
            left = rect.left - 10;
            break;
          case 'right':
            top = rect.top + rect.height / 2;
            left = rect.right + 20;
            break;
          default:
            top = window.innerHeight / 2;
            left = window.innerWidth / 2;
        }
        setPosition({ top: `${top}px`, left: `${left}px` });
      }
    } else {
      setPosition({ top: '50%', left: '50%' });
      setTargetRect(null);
    }
  }, [step, currentStep]);

  const isLastStep = currentStep === TOUR_STEPS.length - 1;
  const isFirstStep = currentStep === 0;
  const isCentered = step.position === 'center' || !step.target;

  return (
    <div className="fixed inset-0 z-[9999]">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/70" onClick={skipTour} />
      
      {/* Spotlight */}
      {targetRect && (
        <div
          className="absolute bg-transparent border-4 border-purple-500 rounded-lg shadow-[0_0_0_9999px_rgba(0,0,0,0.7)] pointer-events-none"
          style={{
            top: targetRect.top - 8,
            left: targetRect.left - 8,
            width: targetRect.width + 16,
            height: targetRect.height + 16,
          }}
        />
      )}
      
      {/* Tooltip */}
      <div
        className={`absolute z-10 w-96 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-5 ${
          isCentered ? 'transform -translate-x-1/2 -translate-y-1/2' : ''
        }`}
        style={isCentered ? { top: '50%', left: '50%' } : position}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            <h3 className="font-bold text-white text-lg">{step.title}</h3>
          </div>
          <button
            onClick={skipTour}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <p className="text-slate-300 mb-4">{step.content}</p>
        
        {/* Progress */}
        <div className="flex justify-center gap-1 mb-4">
          {TOUR_STEPS.map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full ${
                i === currentStep ? 'bg-purple-500' : 'bg-slate-600'
              }`}
            />
          ))}
        </div>
        
        {/* Actions */}
        <div className="flex items-center justify-between">
          <button
            onClick={skipTour}
            className="text-slate-400 hover:text-white text-sm transition-colors"
          >
            Skip Tour
          </button>
          <div className="flex gap-2">
            {!isFirstStep && (
              <Button
                onClick={prevStep}
                variant="outline"
                size="sm"
                className="border-slate-600 text-slate-300 hover:bg-slate-800"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
            <Button
              onClick={nextStep}
              size="sm"
              className="bg-purple-600 hover:bg-purple-500"
            >
              {isLastStep ? 'Finish' : 'Next'}
              {!isLastStep && <ChevronRight className="w-4 h-4 ml-1" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TourProvider;
