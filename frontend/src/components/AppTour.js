import React, { useState, useEffect } from 'react';
import Joyride, { STATUS, ACTIONS, EVENTS } from 'react-joyride';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../utils/api';

// Tour steps configuration
const TOUR_STEPS = [
  // Dashboard Introduction
  {
    target: 'body',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Welcome to CreatorStudio AI! 🎉</h3>
        <p className="text-sm text-gray-600">
          Let's take a quick tour to help you get started with creating viral content.
          This will only take about 2 minutes.
        </p>
      </div>
    ),
    placement: 'center',
    disableBeacon: true,
    page: '/app'
  },
  {
    target: '[data-tour="credits-display"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Your Credits 💰</h3>
        <p className="text-sm text-gray-600">
          This shows your available credits. New users get 100 free credits to start!
          Different features cost different amounts of credits.
        </p>
      </div>
    ),
    placement: 'bottom',
    page: '/app'
  },
  {
    target: '[data-tour="reel-generator-card"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Reel Generator 🎬</h3>
        <p className="text-sm text-gray-600">
          Create viral reel scripts with hooks, captions, and hashtags in seconds.
          Perfect for Instagram, TikTok, and YouTube Shorts!
        </p>
      </div>
    ),
    placement: 'right',
    page: '/app'
  },
  {
    target: '[data-tour="story-generator-card"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Kids Story Generator 📖</h3>
        <p className="text-sm text-gray-600">
          Generate complete kids story video packs with scenes, voiceover scripts,
          and image prompts. Great for YouTube kids channels!
        </p>
      </div>
    ),
    placement: 'left',
    page: '/app'
  },
  {
    target: '[data-tour="genstudio-card"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">GenStudio AI 🎨</h3>
        <p className="text-sm text-gray-600">
          Our AI generation suite! Create images from text, convert images to videos,
          and remix existing videos with AI.
        </p>
      </div>
    ),
    placement: 'right',
    page: '/app'
  },
  {
    target: '[data-tour="creator-tools-card"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Creator Tools 🛠️</h3>
        <p className="text-sm text-gray-600">
          Access 30-day content calendars, carousel generators, hashtag banks,
          trending topics, and more! Some tools are FREE!
        </p>
      </div>
    ),
    placement: 'left',
    page: '/app'
  },
  // Reel Generator Page
  {
    target: '[data-tour="reel-topic-input"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Enter Your Topic 📝</h3>
        <p className="text-sm text-gray-600">
          Start by entering what you want to create content about.
          Be specific for better results! Example: "Morning routines for entrepreneurs"
        </p>
      </div>
    ),
    placement: 'bottom',
    page: '/app/reels'
  },
  {
    target: '[data-tour="reel-niche-select"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Choose Your Niche 🎯</h3>
        <p className="text-sm text-gray-600">
          Select the niche that best fits your content.
          This helps our AI generate more relevant hooks and scripts.
        </p>
      </div>
    ),
    placement: 'bottom',
    page: '/app/reels'
  },
  {
    target: '[data-tour="reel-generate-btn"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Generate Your Reel! 🚀</h3>
        <p className="text-sm text-gray-600">
          Click here to generate your viral reel script.
          You'll get 5 hooks, a full script, captions, hashtags, and B-roll ideas!
        </p>
      </div>
    ),
    placement: 'top',
    page: '/app/reels'
  },
  // Creator Tools
  {
    target: '[data-tour="creator-tools-tabs"]',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">Multiple Tools Available 🧰</h3>
        <p className="text-sm text-gray-600">
          Switch between different tools using these tabs.
          Hashtags and Trending are FREE - no credits needed!
        </p>
      </div>
    ),
    placement: 'bottom',
    page: '/app/creator-tools'
  },
  // Final step
  {
    target: 'body',
    content: (
      <div className="text-left">
        <h3 className="text-lg font-bold mb-2">You're All Set! 🎉</h3>
        <p className="text-sm text-gray-600">
          That's the basics! Look for the purple <span className="text-purple-500 font-bold">?</span> button
          on any page for contextual help. Ready to create amazing content?
        </p>
        <p className="text-xs text-gray-500 mt-2">
          You can replay this tour anytime from your Profile settings.
        </p>
      </div>
    ),
    placement: 'center',
    page: '/app/creator-tools'
  }
];

// Custom tooltip component for dark theme
const CustomTooltip = ({
  continuous,
  index,
  step,
  backProps,
  closeProps,
  primaryProps,
  skipProps,
  tooltipProps,
  isLastStep
}) => (
  <div
    {...tooltipProps}
    className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-5 max-w-sm"
  >
    <div className="text-white mb-4">
      {step.content}
    </div>
    <div className="flex items-center justify-between">
      <div>
        {!isLastStep && (
          <button
            {...skipProps}
            className="text-slate-400 hover:text-white text-sm transition-colors"
          >
            Skip Tour
          </button>
        )}
      </div>
      <div className="flex gap-2">
        {index > 0 && (
          <button
            {...backProps}
            className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Back
          </button>
        )}
        <button
          {...primaryProps}
          className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
        >
          {isLastStep ? 'Finish' : 'Next'}
        </button>
      </div>
    </div>
    <div className="mt-3 flex justify-center gap-1">
      {TOUR_STEPS.map((_, i) => (
        <div
          key={i}
          className={`w-2 h-2 rounded-full ${i === index ? 'bg-purple-500' : 'bg-slate-600'}`}
        />
      ))}
    </div>
  </div>
);

export default function AppTour({ children }) {
  const [runTour, setRunTour] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [tourCompleted, setTourCompleted] = useState(true); // Default to true to prevent flash
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    checkTourStatus();
  }, []);

  const checkTourStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setTourCompleted(true);
        return;
      }

      // Check if user has completed the tour
      const response = await api.get('/api/auth/me');
      const user = response.data;
      
      // If tour not completed and user is on dashboard, start tour
      if (!user.tourCompleted && location.pathname === '/app') {
        setTourCompleted(false);
        setTimeout(() => setRunTour(true), 1000); // Delay for page load
      } else {
        setTourCompleted(user.tourCompleted || false);
      }
    } catch (error) {
      setTourCompleted(true); // Don't show tour on error
    }
  };

  const handleJoyrideCallback = async (data) => {
    const { action, index, status, type } = data;

    // Handle step navigation
    if (type === EVENTS.STEP_AFTER) {
      const nextIndex = index + (action === ACTIONS.PREV ? -1 : 1);
      const nextStep = TOUR_STEPS[nextIndex];
      
      // Navigate to the correct page if needed
      if (nextStep && nextStep.page && location.pathname !== nextStep.page) {
        navigate(nextStep.page);
        setTimeout(() => setStepIndex(nextIndex), 500);
      } else {
        setStepIndex(nextIndex);
      }
    }

    // Handle tour completion or skip
    if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status)) {
      setRunTour(false);
      setTourCompleted(true);
      
      // Save tour completion status
      try {
        await api.put('/api/auth/profile', { tourCompleted: true });
      } catch (error) {
        console.error('Failed to save tour status:', error);
      }
    }
  };

  // Function to restart tour (can be called from Profile settings)
  const restartTour = () => {
    setStepIndex(0);
    navigate('/app');
    setTimeout(() => setRunTour(true), 500);
  };

  // Expose restart function globally
  useEffect(() => {
    window.restartAppTour = restartTour;
    return () => {
      delete window.restartAppTour;
    };
  }, []);

  return (
    <>
      {children}
      <Joyride
        steps={TOUR_STEPS}
        run={runTour}
        stepIndex={stepIndex}
        continuous
        scrollToFirstStep
        showProgress
        showSkipButton
        disableOverlayClose
        spotlightClicks
        callback={handleJoyrideCallback}
        tooltipComponent={CustomTooltip}
        styles={{
          options: {
            zIndex: 10000,
            arrowColor: '#1e293b',
            backgroundColor: '#1e293b',
            overlayColor: 'rgba(0, 0, 0, 0.7)',
            primaryColor: '#9333ea',
            textColor: '#fff',
          },
          spotlight: {
            borderRadius: 8,
          },
          overlay: {
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
          }
        }}
        floaterProps={{
          disableAnimation: false,
        }}
        locale={{
          back: 'Back',
          close: 'Close',
          last: 'Finish',
          next: 'Next',
          skip: 'Skip Tour'
        }}
      />
    </>
  );
}

// Hook to manually trigger tour
export const useAppTour = () => {
  const restartTour = () => {
    if (window.restartAppTour) {
      window.restartAppTour();
    }
  };

  return { restartTour };
};
