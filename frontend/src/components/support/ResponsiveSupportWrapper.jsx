import { useState, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import useViewport from '../../hooks/useViewport';
import SupportDock from './SupportDock';
import SupportBottomSheet from './SupportBottomSheet';
import AIChatbot from '../AIChatbot';
import LiveChatWidget from '../LiveChatWidget';
import FeedbackWidget from '../FeedbackWidget';

export default function ResponsiveSupportWrapper() {
  const { isDesktop } = useViewport();
  const location = useLocation();
  const [activeSheet, setActiveSheet] = useState(null);
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  const handleOpenChat = useCallback(() => setActiveSheet('chat'), []);
  const handleOpenSupport = useCallback(() => setActiveSheet('support'), []);
  const handleOpenFeedback = useCallback(() => {
    setActiveSheet(null);
    setFeedbackOpen(true);
  }, []);
  const handleCloseSheet = useCallback(() => setActiveSheet(null), []);

  // Hide dock during generation, preview, and fullscreen pages
  const path = location.pathname;
  const hideDock = path.includes('story-video-studio') ||
    path.includes('story-preview') ||
    path.includes('story-viewer') ||
    path.includes('experience');

  if (isDesktop) {
    return (
      <>
        <AIChatbot />
        <FeedbackWidget />
        <LiveChatWidget />
      </>
    );
  }

  // Mobile / Tablet: dock + bottom sheet pattern
  return (
    <>
      {!hideDock && (
        <SupportDock
          onOpenChat={handleOpenChat}
          onOpenSupport={handleOpenSupport}
          onOpenFeedback={handleOpenFeedback}
        />
      )}

      {/* AI Chatbot in bottom sheet */}
      <SupportBottomSheet
        isOpen={activeSheet === 'chat'}
        onClose={handleCloseSheet}
        title="AI Assistant"
      >
        <AIChatbot inline forceOpen={activeSheet === 'chat'} />
      </SupportBottomSheet>

      {/* Live Support in bottom sheet */}
      <SupportBottomSheet
        isOpen={activeSheet === 'support'}
        onClose={handleCloseSheet}
        title="Support Chat"
      >
        <LiveChatWidget inline forceOpen={activeSheet === 'support'} />
      </SupportBottomSheet>

      {/* Feedback uses its own Dialog — just trigger open/close externally */}
      <FeedbackWidget
        hideFloating
        externalOpen={feedbackOpen}
        onExternalClose={() => setFeedbackOpen(false)}
      />
    </>
  );
}
