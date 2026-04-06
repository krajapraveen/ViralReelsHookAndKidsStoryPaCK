import { useState } from 'react';
import { MessageCircle, Headphones, MessageSquarePlus, ChevronUp } from 'lucide-react';

export default function SupportDock({ onOpenChat, onOpenSupport, onOpenFeedback }) {
  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-[9980] bg-slate-900/95 backdrop-blur-xl border-t border-slate-700/80 shadow-[0_-4px_24px_rgba(0,0,0,0.4)]"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      data-testid="support-dock"
    >
      <div className="flex items-center justify-around h-14 max-w-lg mx-auto px-2">
        <button
          onClick={onOpenChat}
          className="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors active:scale-95"
          aria-label="AI Chat"
          data-testid="dock-chat-btn"
        >
          <MessageCircle className="w-5 h-5" />
          <span className="text-[10px] font-medium">Chat</span>
        </button>

        <button
          onClick={onOpenSupport}
          className="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors active:scale-95"
          aria-label="Live Support"
          data-testid="dock-support-btn"
        >
          <Headphones className="w-5 h-5" />
          <span className="text-[10px] font-medium">Support</span>
        </button>

        <button
          onClick={onOpenFeedback}
          className="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-slate-400 hover:text-green-400 hover:bg-green-500/10 transition-colors active:scale-95"
          aria-label="Feedback"
          data-testid="dock-feedback-btn"
        >
          <MessageSquarePlus className="w-5 h-5" />
          <span className="text-[10px] font-medium">Feedback</span>
        </button>
      </div>
    </div>
  );
}
