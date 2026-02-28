import React, { useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Bell, X, Check, CheckCheck, Trash2, Download, 
  CheckCircle, AlertTriangle, Clock, ExternalLink,
  Image, Film, BookOpen, Palette, Zap
} from 'lucide-react';
import { Button } from './ui/button';
import { useNotifications, NOTIFICATION_TYPES } from '../contexts/NotificationContext';

// Feature icon mapping
const FEATURE_ICONS = {
  comic_avatar: Image,
  comic_strip: Image,
  comic_storybook: BookOpen,
  gif_maker: Zap,
  reel_generator: Film,
  story_generator: BookOpen,
  coloring_book: Palette,
  default: CheckCircle
};

// Format relative time
const formatRelativeTime = (timestamp) => {
  const now = Date.now();
  const diff = now - timestamp;
  
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
};

// Single notification item
function NotificationItem({ notification, onRead, onRemove, onAction }) {
  const { type, title, message, read, timestamp, color, feature, downloadUrl, actionUrl, expiresAt } = notification;
  
  const Icon = type === NOTIFICATION_TYPES.GENERATION_FAILED 
    ? AlertTriangle 
    : type === NOTIFICATION_TYPES.DOWNLOAD_READY
    ? Download
    : FEATURE_ICONS[feature] || FEATURE_ICONS.default;
  
  const colorClasses = {
    green: 'text-green-400 bg-green-500/10',
    red: 'text-red-400 bg-red-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
    default: 'text-indigo-400 bg-indigo-500/10'
  };

  const iconColor = colorClasses[color] || colorClasses.default;

  // Calculate remaining time for downloads
  const getRemainingTime = () => {
    if (!expiresAt) return null;
    const remaining = new Date(expiresAt).getTime() - Date.now();
    if (remaining <= 0) return 'Expired';
    const mins = Math.floor(remaining / 60000);
    const secs = Math.floor((remaining % 60000) / 1000);
    return `${mins}:${secs.toString().padStart(2, '0')} left`;
  };

  const remainingTime = getRemainingTime();

  return (
    <div 
      className={`p-3 border-b border-slate-700/50 hover:bg-slate-800/50 transition-colors ${
        !read ? 'bg-slate-800/30' : ''
      }`}
      onClick={() => !read && onRead(notification.id)}
    >
      <div className="flex gap-3">
        {/* Icon */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${iconColor}`}>
          <Icon className="w-5 h-5" />
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className={`text-sm font-medium ${!read ? 'text-white' : 'text-slate-300'}`}>
                {title}
              </p>
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                {message}
              </p>
            </div>
            
            {/* Unread indicator */}
            {!read && (
              <div className="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0 mt-1.5" />
            )}
          </div>
          
          {/* Footer */}
          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Clock className="w-3 h-3" />
              <span>{formatRelativeTime(timestamp)}</span>
              {remainingTime && (
                <span className={`px-1.5 py-0.5 rounded text-xs ${
                  remainingTime === 'Expired' 
                    ? 'bg-red-500/20 text-red-400' 
                    : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {remainingTime}
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-1">
              {/* Action button */}
              {(downloadUrl || actionUrl) && remainingTime !== 'Expired' && (
                <a
                  href={downloadUrl || actionUrl}
                  target={downloadUrl ? '_blank' : '_self'}
                  rel="noopener noreferrer"
                  className="p-1 hover:bg-slate-700 rounded transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  {downloadUrl ? (
                    <Download className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <ExternalLink className="w-4 h-4 text-indigo-400" />
                  )}
                </a>
              )}
              
              {/* Remove button */}
              <button
                className="p-1 hover:bg-slate-700 rounded transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(notification.id);
                }}
              >
                <X className="w-4 h-4 text-slate-500 hover:text-slate-300" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main notification center component (dropdown panel)
export default function NotificationCenter() {
  const {
    notifications,
    unreadCount,
    isOpen,
    setIsOpen,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll
  } = useNotifications();
  
  const panelRef = useRef(null);

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        // Check if click is on the bell button
        const bellButton = document.querySelector('[data-testid="notification-bell-btn"]');
        if (bellButton && bellButton.contains(event.target)) {
          return;
        }
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, setIsOpen]);

  if (!isOpen) return null;

  return (
    <div 
      ref={panelRef}
      className="absolute right-0 top-12 w-96 max-h-[500px] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden"
      data-testid="notification-panel"
    >
          {/* Header */}
          <div className="p-4 border-b border-slate-700 flex items-center justify-between bg-slate-800/50">
            <div>
              <h3 className="text-white font-semibold">Notifications</h3>
              <p className="text-xs text-slate-400">
                {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up!'}
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="text-xs"
                >
                  <CheckCheck className="w-4 h-4 mr-1" />
                  Mark all read
                </Button>
              )}
              {notifications.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Notification List */}
          <div className="max-h-[380px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <Bell className="w-12 h-12 mx-auto mb-3 text-slate-600" />
                <p className="text-sm">No notifications yet</p>
                <p className="text-xs mt-1">
                  We'll notify you when your content is ready
                </p>
              </div>
            ) : (
              notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onRead={markAsRead}
                  onRemove={removeNotification}
                />
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="p-3 border-t border-slate-700 bg-slate-800/30">
              <Link
                to="/app/downloads"
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center justify-center gap-1"
                onClick={() => setIsOpen(false)}
              >
                View all downloads
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          )}
    </div>
  );
}
