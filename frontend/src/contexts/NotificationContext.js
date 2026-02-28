import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';

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

// Notification provider
export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  // Load notifications from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('creatorstudio_notifications');
      if (saved) {
        const parsed = JSON.parse(saved);
        // Filter out expired notifications (older than 24 hours)
        const now = Date.now();
        const valid = parsed.filter(n => now - n.timestamp < 24 * 60 * 60 * 1000);
        setNotifications(valid);
        setUnreadCount(valid.filter(n => !n.read).length);
      }
    } catch (e) {
      console.error('Failed to load notifications:', e);
    }
  }, []);

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

    setNotifications(prev => [newNotification, ...prev].slice(0, 50));
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
  const markAsRead = useCallback((notificationId) => {
    setNotifications(prev => prev.map(n => 
      n.id === notificationId ? { ...n, read: true } : n
    ));
    setUnreadCount(prev => Math.max(0, prev - 1));
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    setUnreadCount(0);
  }, []);

  // Remove notification
  const removeNotification = useCallback((notificationId) => {
    setNotifications(prev => {
      const notification = prev.find(n => n.id === notificationId);
      if (notification && !notification.read) {
        setUnreadCount(c => Math.max(0, c - 1));
      }
      return prev.filter(n => n.id !== notificationId);
    });
  }, []);

  // Clear all notifications
  const clearAll = useCallback(() => {
    setNotifications([]);
    setUnreadCount(0);
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
