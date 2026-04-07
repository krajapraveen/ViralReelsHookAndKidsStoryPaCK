import { useEffect, useRef, useCallback } from 'react';

/**
 * ProtectedContent — Reusable wrapper that applies anti-copy deterrence
 * to generated asset areas ONLY. Does NOT block globally.
 *
 * What it does (deterrence, not security):
 * - Disables right-click context menu
 * - Blocks text selection
 * - Blocks drag-start on media (img/video/audio)
 * - Blocks copy/cut/save/select-all/print shortcuts (Ctrl/Cmd + C,X,S,A,P)
 * - Prevents double-click text selection
 *
 * What it does NOT do:
 * - Break playback controls, buttons, or CTAs
 * - Block interactions outside the protected area
 * - Prevent screenshots (impossible on web)
 *
 * Props:
 *  - children: React nodes to protect
 *  - className: additional CSS classes
 *  - enabled: boolean (default true) — allows disabling for paid/entitled users
 */
export default function ProtectedContent({ children, className = '', enabled = true }) {
  const containerRef = useRef(null);

  const handleContextMenu = useCallback((e) => {
    if (!enabled) return;
    e.preventDefault();
  }, [enabled]);

  const handleDragStart = useCallback((e) => {
    if (!enabled) return;
    const tag = e.target.tagName;
    if (['IMG', 'VIDEO', 'AUDIO', 'CANVAS', 'SOURCE'].includes(tag)) {
      e.preventDefault();
    }
  }, [enabled]);

  const handleSelectStart = useCallback((e) => {
    if (!enabled) return;
    // Only block selection on non-interactive elements
    const tag = e.target.tagName;
    if (!['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A'].includes(tag)) {
      e.preventDefault();
    }
  }, [enabled]);

  const handleCopy = useCallback((e) => {
    if (!enabled) return;
    e.preventDefault();
  }, [enabled]);

  const handleKeyDown = useCallback((e) => {
    if (!enabled) return;
    const key = e.key.toLowerCase();
    const mod = e.ctrlKey || e.metaKey;

    // Block Ctrl/Cmd + C, X, S, A, P inside protected area
    if (mod && ['c', 'x', 's', 'a', 'p'].includes(key)) {
      e.preventDefault();
    }
  }, [enabled]);

  const handleDoubleClick = useCallback((e) => {
    if (!enabled) return;
    const tag = e.target.tagName;
    // Prevent double-click text selection on non-interactive elements
    if (!['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A'].includes(tag)) {
      e.preventDefault();
      // Clear any selection that happened
      window.getSelection()?.removeAllRanges();
    }
  }, [enabled]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !enabled) return;

    el.addEventListener('contextmenu', handleContextMenu);
    el.addEventListener('dragstart', handleDragStart);
    el.addEventListener('selectstart', handleSelectStart);
    el.addEventListener('copy', handleCopy);
    el.addEventListener('cut', handleCopy);
    el.addEventListener('keydown', handleKeyDown);
    el.addEventListener('dblclick', handleDoubleClick);

    return () => {
      el.removeEventListener('contextmenu', handleContextMenu);
      el.removeEventListener('dragstart', handleDragStart);
      el.removeEventListener('selectstart', handleSelectStart);
      el.removeEventListener('copy', handleCopy);
      el.removeEventListener('cut', handleCopy);
      el.removeEventListener('keydown', handleKeyDown);
      el.removeEventListener('dblclick', handleDoubleClick);
    };
  }, [enabled, handleContextMenu, handleDragStart, handleSelectStart, handleCopy, handleKeyDown, handleDoubleClick]);

  if (!enabled) {
    return <div className={className}>{children}</div>;
  }

  return (
    <div
      ref={containerRef}
      className={`protected-content ${className}`}
      data-testid="protected-content"
    >
      {children}
    </div>
  );
}
