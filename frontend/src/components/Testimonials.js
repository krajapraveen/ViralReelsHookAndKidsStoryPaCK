import React, { useState, useEffect } from 'react';
import { Star, ChevronLeft, ChevronRight, Quote } from 'lucide-react';

const testimonials = [
  {
    id: 1,
    name: "Priya Sharma",
    role: "Instagram Creator",
    location: "Mumbai",
    avatar: "PS",
    rating: 5,
    text: "I was struggling to come up with content ideas every day. Now I generate a whole week's worth of reel scripts in minutes! My followers have grown 3x in just 2 months.",
    highlight: "3x follower growth",
    gradient: "from-pink-500 to-rose-500"
  },
  {
    id: 2,
    name: "Rahul Verma",
    role: "YouTube Kids Channel",
    location: "Delhi",
    avatar: "RV",
    rating: 5,
    text: "The Kids Story Pack is incredible! I used to spend hours writing scripts for my children's channel. Now I get complete story packs with scene descriptions in seconds.",
    highlight: "10x faster content",
    gradient: "from-blue-500 to-indigo-500"
  },
  {
    id: 3,
    name: "Ananya Patel",
    role: "Social Media Manager",
    location: "Bangalore",
    avatar: "AP",
    rating: 5,
    text: "Managing 5 client accounts was overwhelming. The 30-day content calendar feature saves me at least 10 hours every week. Worth every rupee!",
    highlight: "10 hours saved weekly",
    gradient: "from-purple-500 to-violet-500"
  },
  {
    id: 4,
    name: "Vikram Singh",
    role: "Freelance Creator",
    location: "Jaipur",
    avatar: "VS",
    rating: 5,
    text: "The AI hooks are pure gold! My reels started getting 5x more views after I started using the hook suggestions. This tool pays for itself.",
    highlight: "5x more views",
    gradient: "from-orange-500 to-amber-500"
  },
  {
    id: 5,
    name: "Meera Krishnan",
    role: "Mom Blogger",
    location: "Chennai",
    avatar: "MK",
    rating: 5,
    text: "As a mom with limited time, this is a lifesaver. I create a month's content in one sitting. My kids even love the comic stories I make for them!",
    highlight: "Month's content in 1 hour",
    gradient: "from-green-500 to-emerald-500"
  }
];

export default function Testimonials() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  useEffect(() => {
    if (!isAutoPlaying) return;
    
    const interval = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % testimonials.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [isAutoPlaying]);

  const nextTestimonial = () => {
    setCurrentIndex(prev => (prev + 1) % testimonials.length);
  };

  const prevTestimonial = () => {
    setCurrentIndex(prev => (prev - 1 + testimonials.length) % testimonials.length);
  };

  return (
    <section className="py-16 px-4" id="testimonials">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/30 rounded-full px-4 py-2 mb-4">
            <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
            <span className="text-yellow-400 font-medium text-sm">Loved by 5,000+ Creators</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Real Creators, Real Results
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            See what Indian content creators are saying about CreatorStudio AI
          </p>
        </div>

        {/* Main Testimonial Card */}
        <div 
          className="relative bg-slate-900/50 backdrop-blur-xl rounded-3xl border border-white/10 p-8 md:p-12 mb-8"
          onMouseEnter={() => setIsAutoPlaying(false)}
          onMouseLeave={() => setIsAutoPlaying(true)}
        >
          {/* Quote Icon */}
          <div className="absolute top-6 right-6 opacity-10">
            <Quote className="w-24 h-24 text-white" />
          </div>

          <div className="grid md:grid-cols-3 gap-8 items-center">
            {/* Left - Avatar & Info */}
            <div className="text-center md:text-left">
              <div className={`w-20 h-20 rounded-full bg-gradient-to-br ${testimonials[currentIndex].gradient} flex items-center justify-center mx-auto md:mx-0 mb-4 text-2xl font-bold text-white shadow-lg`}>
                {testimonials[currentIndex].avatar}
              </div>
              <h3 className="text-xl font-bold text-white mb-1">
                {testimonials[currentIndex].name}
              </h3>
              <p className="text-slate-400 text-sm mb-2">
                {testimonials[currentIndex].role}
              </p>
              <p className="text-slate-500 text-xs">
                📍 {testimonials[currentIndex].location}
              </p>
              
              {/* Rating */}
              <div className="flex items-center justify-center md:justify-start gap-1 mt-3">
                {[...Array(testimonials[currentIndex].rating)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                ))}
              </div>
            </div>

            {/* Right - Testimonial Text */}
            <div className="md:col-span-2">
              <p className="text-white/90 text-lg md:text-xl leading-relaxed mb-6 italic">
                "{testimonials[currentIndex].text}"
              </p>
              
              {/* Highlight Badge */}
              <div className={`inline-flex items-center gap-2 bg-gradient-to-r ${testimonials[currentIndex].gradient} rounded-full px-4 py-2`}>
                <span className="text-white font-semibold">
                  ✨ {testimonials[currentIndex].highlight}
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Arrows */}
          <button
            onClick={prevTestimonial}
            className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-all"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={nextTestimonial}
            className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-all"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Dot Indicators */}
        <div className="flex justify-center gap-2 mb-8">
          {testimonials.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                idx === currentIndex 
                  ? 'w-8 bg-gradient-to-r from-indigo-500 to-purple-500' 
                  : 'bg-white/20 hover:bg-white/40'
              }`}
            />
          ))}
        </div>

        {/* Mini Testimonial Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {testimonials.map((t, idx) => (
            <button
              key={t.id}
              onClick={() => setCurrentIndex(idx)}
              className={`p-4 rounded-xl border transition-all duration-300 text-left ${
                idx === currentIndex
                  ? 'bg-white/10 border-white/30 scale-105'
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${t.gradient} flex items-center justify-center text-sm font-bold text-white mb-2`}>
                {t.avatar}
              </div>
              <p className="text-white text-sm font-medium truncate">{t.name}</p>
              <p className="text-slate-500 text-xs truncate">{t.role}</p>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
