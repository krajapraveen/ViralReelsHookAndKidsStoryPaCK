import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import api from '../utils/api';

// Notification types
const NOTIFICATION_TYPES = {
  GENERATION_COMPLETE: 'generation_complete',
  GENERATION_FAILED: 'generation_failed',
  DOWNLOAD_READY: 'download_ready',
  DOWNLOAD_EXPIRING: 'download_expiring',
  CREDIT_LOW: 'credit_low',
  SYSTEM: 'system'
};

// Create context
const NotificationContext = createContext(null);

// Polling interval (30 seconds)
const POLL_INTERVAL = 30000;

// Notification provider
export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const pollIntervalRef = useRef(null);
  const lastPollRef = useRef(null);
  const notificationsRef = useRef([]); // Use ref to track current notifications without causing re-renders

  // Check if user is authenticated
  const isAuthenticated = () => {
    return !!localStorage.getItem('token');
  };

  // Fetch notifications from backend
  const fetchNotifications = useCallback(async () => {
    if (!isAuthenticated()) return;
    
    try {
      const response = await api.get('/api/notifications?limit=50');
      const { notifications: backendNotifications, unread_count } = response.data;
      
      // Update with backend notifications
      if (backendNotifications) {
        // Convert backend notifications to frontend format
        const formattedBackend = backendNotifications.map(n => ({
          id: n.id,
          type: n.type,
          title: n.title,
          message: n.message,
          read: n.read,
          timestamp: new Date(n.created_at).getTime(),
          feature: n.feature,
          downloadUrl: n.download_url,
          downloadId: n.download_id,
          actionUrl: n.action_url,
          expiresAt: n.expires_at,
          color: n.type === 'generation_failed' ? 'red' : 
                 n.type === 'download_ready' ? 'blue' : 'green'
        }));
        
        // Check for new notifications (for toast) - use ref to avoid stale closure
        // Skip generation_complete/generation_failed - those are toasted by the page-level code
        if (lastPollRef.current) {
          const existingIds = new Set(notificationsRef.current.map(n => n.id));
          const newNotifications = formattedBackend.filter(n => 
            !existingIds.has(n.id) && !n.read && 
            n.type !== 'generation_complete' && n.type !== 'generation_failed'
          );
          newNotifications.forEach(n => {
            if (n.type === 'download_ready') {
              toast.success(n.title, { description: n.message });
            }
          });
        }
        
        // Update ref and state
        notificationsRef.current = formattedBackend;
        setNotifications(formattedBackend);
        setUnreadCount(unread_count);
      }
      
      lastPollRef.current = Date.now();
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  }, []); // No dependencies - use refs for mutable data

  // Track authentication state change
  const [isAuth, setIsAuth] = useState(isAuthenticated());
  
  // Listen for storage events (token changes)
  useEffect(() => {
    const checkAuth = () => {
      const authenticated = isAuthenticated();
      if (authenticated !== isAuth) {
        setIsAuth(authenticated);
      }
    };
    
    // Check periodically for auth changes
    const authCheckInterval = setInterval(checkAuth, 1000);
    
    // Also listen for storage events
    window.addEventListener('storage', checkAuth);
    
    return () => {
      clearInterval(authCheckInterval);
      window.removeEventListener('storage', checkAuth);
    };
  }, [isAuth]);

  // Start polling when user is authenticated
  useEffect(() => {
    if (isAuth) {
      // Initial fetch
      fetchNotifications();
      
      // Start polling
      pollIntervalRef.current = setInterval(fetchNotifications, POLL_INTERVAL);
    } else {
      // Clear notifications when logged out
      setNotifications([]);
      setUnreadCount(0);
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [isAuth, fetchNotifications]);

  // Save notifications to localStorage when they change
  useEffect(() => {
    try {
      localStorage.setItem('creatorstudio_notifications', JSON.stringify(notifications.slice(0, 50)));
    } catch (e) {
      console.error('Failed to save notifications:', e);
    }
  }, [notifications]);

  // Add a new notification
  const addNotification = useCallback((notification) => {
    const newNotification = {
      id: `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      read: false,
      ...notification
    };

    setNotifications(prev => {
      const updated = [newNotification, ...prev].slice(0, 50);
      notificationsRef.current = updated; // Keep ref in sync
      return updated;
    });
    setUnreadCount(prev => prev + 1);

    // Show toast for important notifications
    if (notification.showToast !== false) {
      const toastType = notification.type === NOTIFICATION_TYPES.GENERATION_FAILED ? 'error' : 'success';
      toast[toastType](notification.title, {
        description: notification.message,
        action: notification.actionUrl ? {
          label: 'View',
          onClick: () => window.location.href = notification.actionUrl
        } : undefined
      });
    }

    return newNotification.id;
  }, []);

  // Mark notification as read
  const markAsRead = useCallback(async (notificationId) => {
    setNotifications(prev => prev.map(n => 
      n.id === notificationId ? { ...n, read: true } : n
    ));
    setUnreadCount(prev => Math.max(0, prev - 1));
    
    // Sync with backend
    try {
      await api.post(`/api/notifications/${notificationId}/read`);
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(async () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    setUnreadCount(0);
    
    // Sync with backend
    try {
      await api.post('/api/notifications/mark-all-read');
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  }, []);

  // Remove notification
  const removeNotification = useCallback(async (notificationId) => {
    setNotifications(prev => {
      const notification = prev.find(n => n.id === notificationId);
      if (notification && !notification.read) {
        setUnreadCount(c => Math.max(0, c - 1));
      }
      return prev.filter(n => n.id !== notificationId);
    });
    
    // Sync with backend
    try {
      await api.delete(`/api/notifications/${notificationId}`);
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  }, []);

  // Clear all notifications
  const clearAll = useCallback(async () => {
    setNotifications([]);
    setUnreadCount(0);
    
    // Sync with backend
    try {
      await api.delete('/api/notifications');
    } catch (error) {
      console.error('Failed to clear notifications:', error);
    }
  }, []);

  // Notify generation complete
  const notifyGenerationComplete = useCallback((data) => {
    return addNotification({
      type: NOTIFICATION_TYPES.GENERATION_COMPLETE,
      title: `${data.featureName || 'Content'} Ready!`,
      message: data.message || 'Your generation is complete and ready for download.',
      icon: 'check-circle',
      color: 'green',
      feature: data.feature,
      jobId: data.jobId,
      downloadUrl: data.downloadUrl,
      previewUrl: data.previewUrl,
      expiresAt: data.expiresAt,
      actionUrl: data.actionUrl,
      showToast: true
    });
  }, [addNotification]);

  // Notify generation failed
  const notifyGenerationFailed = useCallback((data) => {
    return addNotification({
      type: NOTIFICATION_TYPES.GENERATION_FAILED,
      title: `${data.featureName || 'Generation'} Failed`,
      message: data.error || 'Something went wrong. Please try again.',
      icon: 'alert-triangle',
      color: 'red',
      feature: data.feature,
      jobId: data.jobId,
      showToast: true
    });
  }, [addNotification]);

  // Notify download ready
  const notifyDownloadReady = useCallback((data) => {
    return addNotification({
      type: NOTIFICATION_TYPES.DOWNLOAD_READY,
      title: 'Download Ready',
      message: `Your ${data.filename || 'file'} is ready. Available for ${data.expiryMinutes || 5} minutes.`,
      icon: 'download',
      color: 'blue',
      downloadId: data.downloadId,
      downloadUrl: data.downloadUrl,
      filename: data.filename,
      expiresAt: data.expiresAt,
      showToast: true
    });
  }, [addNotification]);

  const value = {
    notifications,
    unreadCount,
    isOpen,
    setIsOpen,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    notifyGenerationComplete,
    notifyGenerationFailed,
    notifyDownloadReady,
    refetchNotifications: fetchNotifications,
    NOTIFICATION_TYPES
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

// Hook to use notifications
export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}

export { NOTIFICATION_TYPES };
