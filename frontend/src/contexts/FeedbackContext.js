import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import FeedbackModal from '../components/FeedbackModal';
import useIdleFeedbackPrompt from '../hooks/useIdleFeedbackPrompt';
import {
  ensureSessionId,
  getFeedbackEligibility,
  markFeedbackPromptShown,
  clearFeedbackSession,
} from '../utils/feedbackSession';

const FeedbackContext = createContext({});

export function useFeedback() {
  return useContext(FeedbackContext);
}

export function FeedbackProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [source, setSource] = useState('logout_prompt');
  const [idleSec, setIdleSec] = useState(0);
  const pendingLogoutRef = useRef(null);

  // Initialize session ID on mount
  useEffect(() => {
    if (localStorage.getItem('token')) ensureSessionId();
  }, []);

  // Idle prompt callback
  const onIdleTrigger = useCallback((idleSeconds) => {
    setSource('idle_prompt');
    setIdleSec(idleSeconds);
    setIsOpen(true);
  }, []);

  // Only activate idle detection if user is logged in
  const isLoggedIn = !!localStorage.getItem('token');
  useIdleFeedbackPrompt(isLoggedIn ? onIdleTrigger : () => {}, 120000);

  // Called by logout handlers
  const handleLogoutWithFeedback = useCallback((proceedLogoutFn) => {
    const { eligible } = getFeedbackEligibility();
    if (!eligible) {
      clearFeedbackSession();
      proceedLogoutFn();
      return;
    }
    pendingLogoutRef.current = proceedLogoutFn;
    setSource('logout_prompt');
    setIdleSec(0);
    markFeedbackPromptShown();
    setIsOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    if (pendingLogoutRef.current) {
      const fn = pendingLogoutRef.current;
      pendingLogoutRef.current = null;
      clearFeedbackSession();
      fn();
    }
  }, []);

  const handleSubmitDone = useCallback(() => {
    // handleClose will be called after submit
  }, []);

  return (
    <FeedbackContext.Provider value={{ handleLogoutWithFeedback }}>
      {children}
      <FeedbackModal
        isOpen={isOpen}
        onClose={handleClose}
        onSubmitDone={handleSubmitDone}
        source={source}
        idleSeconds={idleSec}
      />
    </FeedbackContext.Provider>
  );
}
