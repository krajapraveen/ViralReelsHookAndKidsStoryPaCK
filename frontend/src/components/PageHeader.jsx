import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from './ui/button';

/**
 * Universal responsive page header.
 * Mobile: compact, title truncated, subtitle hidden, right-padding for GlobalUserBar.
 * Desktop: full display, unchanged from current layout.
 * 
 * Props:
 *  - title: string (page name)
 *  - subtitle: string (optional description, hidden on mobile)
 *  - icon: React component (e.g. Film from lucide)
 *  - backTo: string (route for back button, default "/app")
 *  - rightContent: JSX (optional right-side content like status indicators)
 *  - className: string (additional classes)
 */
export default function PageHeader({
  title,
  subtitle,
  icon: Icon,
  backTo = '/app',
  rightContent,
  className = '',
  children,
}) {
  return (
    <header className={`sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10 vs-page-header ${className}`}>
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-2.5 sm:py-4 flex items-center justify-between">
        {/* Left: Back + Title */}
        <div className="flex items-center gap-2 sm:gap-4 min-w-0 vs-header-left">
          <Link to={backTo}>
            <Button variant="ghost" size="icon" className="text-white flex-shrink-0 h-9 w-9 sm:h-10 sm:w-10" data-testid="header-back-btn">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div className="min-w-0">
            <h1 className="text-base sm:text-xl font-bold text-white flex items-center gap-2 vs-header-title" data-testid="page-title">
              {Icon && <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400 flex-shrink-0" />}
              <span className="truncate">{title}</span>
            </h1>
            {subtitle && (
              <p className="text-xs sm:text-sm text-slate-400 vs-header-subtitle truncate">{subtitle}</p>
            )}
          </div>
        </div>

        {/* Right: Optional content */}
        {(rightContent || children) && (
          <div className="flex items-center gap-2 flex-shrink-0">
            {rightContent || children}
          </div>
        )}
      </div>
    </header>
  );
}
