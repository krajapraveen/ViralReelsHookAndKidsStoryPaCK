import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Play, Pause } from 'lucide-react';
import { Button } from './ui/button';

const features = [
  {
    id: 1,
    title: "Dashboard",
    subtitle: "Your Creative Command Center",
    description: "Access all AI tools from one beautiful dashboard. Track credits, view history, and start creating instantly.",
    gradient: "from-blue-500 to-indigo-600",
    icon: "🎯",
    highlights: ["Quick Access Cards", "Credit Tracking", "Recent Creations"]
  },
  {
    id: 2,
    title: "Reel Script Generator",
    subtitle: "Go Viral in Seconds",
    description: "Enter any topic and get 5 viral hooks, complete scripts with timing, captions, and hashtags. All in under 10 seconds.",
    gradient: "from-purple-500 to-pink-600",
    icon: "🎬",
    highlights: ["5 Viral Hooks", "Timed Scripts", "Auto Hashtags"]
  },
  {
    id: 3,
    title: "Kids Story Pack",
    subtitle: "Complete Video Production",
    description: "Generate full story packs with narration scripts, scene descriptions, and character details. Perfect for YouTube kids channels.",
    gradient: "from-pink-500 to-rose-600",
    icon: "📚",
    highlights: ["Age-Appropriate", "8 Scene Stories", "Ready for Animation"]
  },
  {
    id: 4,
    title: "Comic Story Builder",
    subtitle: "Turn Ideas into Comics",
    description: "5-step wizard to create printable comic books. Choose from 8 genres including Superhero, Fantasy, and Sci-Fi.",
    gradient: "from-orange-500 to-amber-600",
    icon: "💥",
    highlights: ["8 Story Genres", "5-Step Wizard", "Print Ready"]
  },
  {
    id: 5,
    title: "Creator Tools",
    subtitle: "Everything You Need",
    description: "30-day content calendars, carousel generators, hashtag research, thumbnail ideas, and trending topic analysis.",
    gradient: "from-green-500 to-emerald-600",
    icon: "🛠️",
    highlights: ["Content Calendar", "Hashtag Generator", "Trend Analysis"]
  }
];

export default function ProductShowcase() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let interval;
    let progressInterval;

    if (isPlaying) {
      // Progress bar animation
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) return 0;
          return prev + 2;
        });
      }, 100);

      // Auto-advance slides every 5 seconds
      interval = setInterval(() => {
        setCurrentIndex(prev => (prev + 1) % features.length);
        setProgress(0);
      }, 5000);
    }

    return () => {
      clearInterval(interval);
      clearInterval(progressInterval);
    };
  }, [isPlaying]);

  const goToSlide = (index) => {
    setCurrentIndex(index);
    setProgress(0);
  };

  const nextSlide = () => {
    setCurrentIndex(prev => (prev + 1) % features.length);
    setProgress(0);
  };

  const prevSlide = () => {
    setCurrentIndex(prev => (prev - 1 + features.length) % features.length);
    setProgress(0);
  };

  const currentFeature = features[currentIndex];

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Main Showcase Container */}
      <div className="relative bg-slate-900/50 backdrop-blur-xl rounded-3xl border border-white/10 overflow-hidden">
        
        {/* Feature Display */}
        <div className="grid md:grid-cols-2 gap-0">
          
          {/* Left Side - Feature Info */}
          <div className="p-8 md:p-12 flex flex-col justify-center">
            <div className={`inline-flex items-center gap-2 bg-gradient-to-r ${currentFeature.gradient} bg-opacity-20 rounded-full px-4 py-2 mb-4 w-fit`}>
              <span className="text-2xl">{currentFeature.icon}</span>
              <span className="text-white font-medium text-sm">{currentFeature.subtitle}</span>
            </div>
            
            <h3 className="text-3xl md:text-4xl font-bold text-white mb-4 transition-all duration-500">
              {currentFeature.title}
            </h3>
            
            <p className="text-slate-300 text-lg mb-6 leading-relaxed">
              {currentFeature.description}
            </p>
            
            {/* Feature Highlights */}
            <div className="flex flex-wrap gap-2 mb-6">
              {currentFeature.highlights.map((highlight, idx) => (
                <span 
                  key={idx}
                  className="bg-white/10 text-white/90 px-3 py-1 rounded-full text-sm border border-white/20"
                >
                  {highlight}
                </span>
              ))}
            </div>

            {/* Progress Indicators */}
            <div className="flex items-center gap-2">
              {features.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => goToSlide(idx)}
                  className="relative h-1 rounded-full overflow-hidden transition-all duration-300"
                  style={{ width: idx === currentIndex ? '48px' : '24px' }}
                >
                  <div className="absolute inset-0 bg-white/20 rounded-full" />
                  {idx === currentIndex && (
                    <div 
                      className={`absolute inset-y-0 left-0 bg-gradient-to-r ${currentFeature.gradient} rounded-full transition-all`}
                      style={{ width: `${progress}%` }}
                    />
                  )}
                  {idx < currentIndex && (
                    <div className={`absolute inset-0 bg-gradient-to-r ${features[idx].gradient} rounded-full`} />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Right Side - Visual Preview */}
          <div className={`relative bg-gradient-to-br ${currentFeature.gradient} p-8 md:p-12 flex items-center justify-center min-h-[300px] md:min-h-[400px]`}>
            {/* Decorative Elements */}
            <div className="absolute inset-0 opacity-30">
              <div className="absolute top-10 left-10 w-20 h-20 bg-white/20 rounded-full blur-xl" />
              <div className="absolute bottom-10 right-10 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-40 h-40 bg-white/10 rounded-full blur-3xl" />
            </div>
            
            {/* Feature Icon Large */}
            <div className="relative z-10 text-center">
              <div className="text-8xl md:text-9xl mb-4 animate-bounce-slow">
                {currentFeature.icon}
              </div>
              <div className="bg-white/20 backdrop-blur-sm rounded-xl px-6 py-3">
                <p className="text-white font-semibold text-lg">{currentFeature.title}</p>
                <p className="text-white/80 text-sm">Click to explore →</p>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Controls */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsPlaying(!isPlaying)}
            className="text-white/70 hover:text-white hover:bg-white/10"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={prevSlide}
            className="text-white/70 hover:text-white hover:bg-white/10"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={nextSlide}
            className="text-white/70 hover:text-white hover:bg-white/10"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        {/* Feature Counter */}
        <div className="absolute top-4 right-4 bg-black/30 backdrop-blur-sm rounded-full px-3 py-1">
          <span className="text-white/90 text-sm font-medium">
            {currentIndex + 1} / {features.length}
          </span>
        </div>
      </div>

      {/* Quick Feature Links */}
      <div className="flex flex-wrap justify-center gap-2 mt-6">
        {features.map((feature, idx) => (
          <button
            key={idx}
            onClick={() => goToSlide(idx)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
              idx === currentIndex
                ? `bg-gradient-to-r ${feature.gradient} text-white shadow-lg`
                : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
            }`}
          >
            {feature.icon} {feature.title}
          </button>
        ))}
      </div>
    </div>
  );
}
