import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Command } from 'lucide-react';
import FounderAuthorityBlock from '../components/FounderAuthorityBlock';

/**
 * AboutPage — Standalone About page reusing FounderAuthorityBlock.
 * Route: /about
 */
export default function AboutPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#07070f]" data-testid="about-page">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-[#07070f]/80 backdrop-blur-xl border-b border-white/[0.04]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Command className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-base font-bold tracking-tight text-white">Visionary Suite</span>
          </Link>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
            data-testid="about-back-btn"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
        </div>
      </nav>

      {/* Content */}
      <div className="pt-8 pb-16">
        <FounderAuthorityBlock onExplore={() => navigate('/app')} />
      </div>
    </div>
  );
}
