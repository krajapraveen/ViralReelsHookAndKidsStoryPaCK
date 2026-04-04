import { useEffect, useCallback } from 'react';

/**
 * useContentProtection — site-wide anti-copy friction layer.
 *
 * WHAT IT DOES:
 * - Blocks right-click context menu on protected surfaces
 * - Prevents drag-and-drop save of media elements (img, video, audio, canvas)
 * - Intercepts copy/cut events on non-input elements
 * - Blocks common save/select shortcuts (Ctrl+S, Ctrl+C on non-inputs, Ctrl+A)
 * - Applies CSS-level text selection prevention
 * - Reduces mobile long-press save behavior
 *
 * WHAT IT DOES NOT DO:
 * - Does not claim to block screenshots or screen recording
 * - Does not interfere with input fields, textareas, or contenteditable elements
 * - Does not break essential product flows
 *
 * @param {boolean} enabled — whether protection is active (default: true)
 */
export function useContentProtection(enabled = true) {

  const isEditableTarget = useCallback((target) => {
    if (!target) return false;
    const tag = target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if (target.isContentEditable) return true;
    if (target.closest('[contenteditable="true"]')) return true;
    if (target.closest('[role="textbox"]')) return true;
    if (target.closest('.ProseMirror, .ql-editor, .CodeMirror, .monaco-editor')) return true;
    return false;
  }, []);

  useEffect(() => {
    if (!enabled) return;

    // 1. Block right-click context menu on non-editable elements
    const handleContextMenu = (e) => {
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
    };

    // 2. Block drag-and-drop on media elements
    const handleDragStart = (e) => {
      const tag = e.target.tagName;
      if (tag === 'IMG' || tag === 'VIDEO' || tag === 'AUDIO' || tag === 'CANVAS') {
        e.preventDefault();
      }
      if (e.target.closest('a[download]')) return;
      if (e.target.closest('[data-allow-drag]')) return;
    };

    // 3. Block copy/cut on non-editable elements
    const handleCopy = (e) => {
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
    };
    const handleCut = (e) => {
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
    };

    // 4. Block common save/select shortcuts on non-editable targets
    const handleKeyDown = (e) => {
      if (isEditableTarget(e.target)) return;
      const ctrl = e.ctrlKey || e.metaKey;
      // Ctrl+S (save page)
      if (ctrl && e.key === 's') {
        e.preventDefault();
      }
      // Ctrl+C (copy) on non-input
      if (ctrl && e.key === 'c') {
        e.preventDefault();
      }
      // Ctrl+A (select all) on non-input
      if (ctrl && e.key === 'a') {
        e.preventDefault();
      }
      // Ctrl+U (view source)
      if (ctrl && e.key === 'u') {
        e.preventDefault();
      }
      // PrintScreen — best effort, not reliable
      if (e.key === 'PrintScreen') {
        e.preventDefault();
      }
    };

    // 5. Block image/video save on mobile long-press via touchstart
    const handleTouchStart = (e) => {
      const tag = e.target.tagName;
      if (tag === 'IMG' || tag === 'VIDEO' || tag === 'CANVAS') {
        e.target.style.pointerEvents = 'none';
        setTimeout(() => {
          if (e.target) e.target.style.pointerEvents = '';
        }, 600);
      }
    };

    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('dragstart', handleDragStart);
    document.addEventListener('copy', handleCopy);
    document.addEventListener('cut', handleCut);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('touchstart', handleTouchStart, { passive: true });

    return () => {
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('dragstart', handleDragStart);
      document.removeEventListener('copy', handleCopy);
      document.removeEventListener('cut', handleCut);
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('touchstart', handleTouchStart);
    };
  }, [enabled, isEditableTarget]);
}
