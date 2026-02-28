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
      
      // Merge backend notifications with local ones
      if (backendNotifications && backendNotifications.length > 0) {
        setNotifications(prev => {
          // Create a map of existing notification IDs
          const existingIds = new Set(prev.map(n => n.id));
          
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
          
          // Add new notifications from backend that we don't have
          const newFromBackend = formattedBackend.filter(n => !existingIds.has(n.id));
          
          // Show toast for new unread notifications
          newFromBackend.filter(n => !n.read).forEach(n => {
            if (n.type === 'generation_complete' || n.type === 'download_ready') {
              toast.success(n.title, { description: n.message });
            }
          });
          
          return [...newFromBackend, ...prev].slice(0, 50);
        });
        
        setUnreadCount(unread_count);
      }
      
      lastPollRef.current = Date.now();
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  }, []);

  // Start polling when user is authenticated
  useEffect(() => {
    if (isAuthenticated()) {
      // Initial fetch
      fetchNotifications();
      
      // Start polling
      pollIntervalRef.current = setInterval(fetchNotifications, POLL_INTERVAL);
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [fetchNotifications]);

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
