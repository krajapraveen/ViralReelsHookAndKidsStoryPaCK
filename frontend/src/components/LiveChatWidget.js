import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send, Minimize2, Maximize2, Bot, User } from 'lucide-react';
import { Button } from './ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const QUICK_REPLIES = [
  "How do I get started?",
  "What are credits?",
  "How do I generate reels?",
  "Pricing plans",
  "Contact support"
];

const AUTO_RESPONSES = {
  "how do i get started": {
    message: "Getting started is easy! 1) Sign up for free and get 100 credits 2) Choose a tool (Reels, Stories, Comics) 3) Enter your topic and let AI do the work! Need more help? Visit our User Manual.",
    link: { text: "View User Manual", url: "/user-manual" }
  },
  "what are credits": {
    message: "Credits are our simple pricing system. Each feature costs a set number of credits: Reels = 10 credits, Story Packs = 6 credits, Comics = 15 credits. You get 100 FREE credits on signup!",
    link: { text: "See Pricing", url: "/pricing" }
  },
  "how do i generate reels": {
    message: "To generate reels: 1) Go to Dashboard > Reel Generator 2) Enter your topic or niche 3) Click Generate - you'll get 5 hooks, a script, captions & hashtags in seconds!",
    link: { text: "Try Reel Generator", url: "/app/reel-generator" }
  },
  "pricing plans": {
    message: "We offer flexible credit packs: Starter (500 credits) = ₹499, Creator (1500 credits) = ₹999, Pro (5000 credits) = ₹2499. All purchases are one-time, no subscription!",
    link: { text: "View All Plans", url: "/pricing" }
  },
  "contact support": {
    message: "Need human support? Email us at support@visionary-suite.com or use the Contact form. We typically respond within 24 hours!",
    link: { text: "Contact Us", url: "/contact" }
  }
};

export default function LiveChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      text: "Hi there! I'm your AI assistant. How can I help you today?",
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen, isMinimized]);

  const findResponse = (input) => {
    const lowerInput = input.toLowerCase().trim();
    
    for (const [key, response] of Object.entries(AUTO_RESPONSES)) {
      if (lowerInput.includes(key) || key.includes(lowerInput.substring(0, 10))) {
        return response;
      }
    }
    
    // Default response
    return {
      message: "I'm not sure I understand. Try asking about: getting started, credits, generating reels, pricing, or contact support. You can also check our User Manual for detailed guides!",
      link: { text: "View User Manual", url: "/user-manual" }
    };
  };

  const handleSend = (text = inputValue) => {
    if (!text.trim()) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: text.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    // Simulate typing delay
    setTimeout(() => {
      const response = findResponse(text);
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: response.message,
        link: response.link,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
    }, 1000);
  };

  const handleQuickReply = (reply) => {
    handleSend(reply);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
        data-testid="chat-widget-button"
        aria-label="Open chat"
      >
        <MessageCircle className="w-6 h-6 text-white" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white animate-pulse"></span>
        
        {/* Tooltip */}
        <span className="absolute right-full mr-3 px-3 py-2 bg-slate-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Need help? Chat with us!
        </span>
      </button>
    );
  }

  return (
    <div 
      className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ${
        isMinimized ? 'w-72 h-14' : 'w-80 sm:w-96 h-[500px]'
      }`}
      data-testid="chat-widget"
    >
      <div className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 overflow-hidden h-full flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">Support Chat</h3>
              <p className="text-white/70 text-xs">We typically reply instantly</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
              aria-label={isMinimized ? "Maximize" : "Minimize"}
            >
              {isMinimized ? <Maximize2 className="w-4 h-4 text-white" /> : <Minimize2 className="w-4 h-4 text-white" />}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
              aria-label="Close chat"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                      message.type === 'user'
                        ? 'bg-indigo-500 text-white rounded-br-md'
                        : 'bg-slate-800 text-slate-200 rounded-bl-md'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{message.text}</p>
                    {message.link && (
                      <a
                        href={message.link.url}
                        className="inline-block mt-2 text-xs text-indigo-400 hover:text-indigo-300 underline"
                      >
                        {message.link.text} →
                      </a>
                    )}
                  </div>
                </div>
              ))}
              
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-slate-800 rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Replies */}
            {messages.length <= 2 && (
              <div className="px-4 py-2 bg-slate-900 border-t border-slate-800">
                <p className="text-xs text-slate-500 mb-2">Quick questions:</p>
                <div className="flex flex-wrap gap-2">
                  {QUICK_REPLIES.map((reply, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleQuickReply(reply)}
                      className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full transition-colors"
                    >
                      {reply}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="p-4 bg-slate-900 border-t border-slate-800">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  data-testid="chat-input"
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={!inputValue.trim()}
                  className="bg-indigo-500 hover:bg-indigo-600 rounded-xl px-4"
                  data-testid="chat-send-btn"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
