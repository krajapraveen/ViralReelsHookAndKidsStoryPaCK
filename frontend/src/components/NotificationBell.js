import React from 'react';
import { Bell } from 'lucide-react';
import { useNotifications } from '../contexts/NotificationContext';
import NotificationCenter from './NotificationCenter';

export default function NotificationBell() {
  const { unreadCount, isOpen, setIsOpen } = useNotifications();

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
        data-testid="notification-bell-btn"
        aria-label="Notifications"
      >
        <Bell 
          className={`w-5 h-5 transition-colors ${
            unreadCount > 0 ? 'text-indigo-400' : 'text-slate-400'
          }`} 
        />
        
        {/* Unread badge */}
        {unreadCount > 0 && (
          <span 
            className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-red-500 rounded-full flex items-center justify-center text-xs font-bold text-white animate-pulse"
            data-testid="notification-badge"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification panel dropdown */}
      {isOpen && <NotificationCenter />}
    </div>
  );
}
