import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send, Minimize2, Maximize2, Bot, User, Sparkles, HelpCircle, Phone, Mail, Clock, ExternalLink, ChevronRight, Zap, BookOpen, Video, Image, Palette } from 'lucide-react';
import { Button } from './ui/button';
import { useLocation } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Enhanced Quick Replies based on current page
const getQuickReplies = (pathname) => {
  const baseReplies = [
    { text: "How do I get started?", icon: Sparkles },
    { text: "What are credits?", icon: Zap },
    { text: "Contact support", icon: Mail }
  ];
  
  if (pathname.includes('reel')) {
    return [
      { text: "How to generate reels?", icon: Video },
      { text: "Best topics for reels", icon: Sparkles },
      ...baseReplies.slice(0, 1)
    ];
  } else if (pathname.includes('comic') || pathname.includes('photo-to-comic')) {
    return [
      { text: "How to create comics?", icon: Image },
      { text: "What images work best?", icon: HelpCircle },
      ...baseReplies.slice(0, 1)
    ];
  } else if (pathname.includes('story')) {
    return [
      { text: "How do story packs work?", icon: BookOpen },
      { text: "Story pack themes", icon: Sparkles },
      ...baseReplies.slice(0, 1)
    ];
  } else if (pathname.includes('gif')) {
    return [
      { text: "How to make GIFs?", icon: Video },
      { text: "Best reactions to use", icon: Sparkles },
      ...baseReplies.slice(0, 1)
    ];
  } else if (pathname.includes('coloring')) {
    return [
      { text: "How coloring books work?", icon: Palette },
      { text: "Can I use photos?", icon: Image },
      ...baseReplies.slice(0, 1)
    ];
  } else if (pathname.includes('billing') || pathname.includes('pricing')) {
    return [
      { text: "Pricing plans", icon: Zap },
      { text: "How to get more credits?", icon: Sparkles },
      { text: "Payment methods", icon: HelpCircle }
    ];
  }
  
  return baseReplies;
};

// Comprehensive auto-responses with contextual awareness
const AUTO_RESPONSES = {
  // Getting Started
  "how do i get started": {
    message: "Getting started with Visionary Suite is easy!\n\n1. Sign up for free - get 100 credits instantly\n2. Choose your tool from the Dashboard\n3. Enter your topic or upload an image\n4. Let AI create amazing content!\n\nEach tool has a step-by-step wizard to guide you.",
    link: { text: "Go to Dashboard", url: "/app" },
    suggestions: ["What are credits?", "Best features to try"]
  },
  
  // Credits & Pricing
  "what are credits": {
    message: "Credits are our simple pay-as-you-go system:\n\n- Reel Scripts: 10 credits\n- Story Packs: 6 credits\n- Comic Avatars: 15 credits\n- GIFs: 8 credits\n- Coloring Books: 5-10 credits\n\nYou get 100 FREE credits on signup!",
    link: { text: "View Pricing", url: "/pricing" },
    suggestions: ["How to get more credits?", "Pricing plans"]
  },
  "pricing plans": {
    message: "Our flexible pricing:\n\nSubscriptions:\n- Weekly: ₹199 (50 credits)\n- Monthly: ₹699 (200 credits)\n- Quarterly: ₹1999 (500 credits) - 35% off!\n- Yearly: ₹5999 (2500 credits) - 50% off!\n\nCredit Packs:\n- Starter: ₹499 (100 credits)\n- Creator: ₹999 (300 credits)\n- Pro: ₹2499 (1000 credits)",
    link: { text: "Subscribe Now", url: "/app/billing" },
    suggestions: ["What are credits?", "How do I get started?"]
  },
  "how to get more credits": {
    message: "You can get more credits by:\n\n1. Daily Reward - Claim free credits daily!\n2. Credit Packs - One-time purchases\n3. Subscriptions - Monthly plans with bonus credits\n4. Referral Program - Invite friends, earn credits!",
    link: { text: "Buy Credits", url: "/app/billing" },
    suggestions: ["Pricing plans", "Daily rewards"]
  },
  "payment methods": {
    message: "We accept multiple payment methods through our secure payment gateway:\n\n- Credit/Debit Cards (Visa, Mastercard, RuPay)\n- UPI (GPay, PhonePe, Paytm)\n- Net Banking\n- Wallets\n\nAll payments are securely processed by Cashfree.",
    link: { text: "View Billing", url: "/app/billing" }
  },
  
  // Reel Generator
  "how to generate reels": {
    message: "Creating viral reel scripts is easy!\n\n1. Go to Reel Generator\n2. Enter your topic (e.g., '5 morning habits')\n3. Select niche, tone, duration (30-60s)\n4. Click 'Generate Reel Script'\n\nYou'll get 5 hooks, full script, captions & hashtags!",
    link: { text: "Try Reel Generator", url: "/app/reels" },
    suggestions: ["Best topics for reels", "What are credits?"]
  },
  "best topics for reels": {
    message: "Top-performing reel topics:\n\n1. Life hacks & tips\n2. Behind-the-scenes\n3. Before/After transformations\n4. Day-in-my-life\n5. Product reviews\n6. Quick tutorials\n7. Storytelling hooks\n8. Motivational content\n\nPro tip: Use trending audio and hooks!",
    link: { text: "Generate Reel Now", url: "/app/reels" }
  },
  
  // Comics
  "how to create comics": {
    message: "Creating comic avatars:\n\n1. Go to Photo to Comic\n2. Upload a clear face photo\n3. Choose style (Superhero, Retro, etc.)\n4. Select genre (Action, Comedy, etc.)\n5. Click Generate!\n\nPro tip: Use well-lit photos with clear faces for best results.",
    link: { text: "Create Comic", url: "/app/photo-to-comic" },
    suggestions: ["What images work best?", "Comic styles available"]
  },
  "what images work best": {
    message: "For best comic results:\n\n✅ DO:\n- Clear, front-facing photos\n- Good lighting (natural preferred)\n- Single person in frame\n- High resolution (at least 500px)\n\n❌ DON'T:\n- Blurry or dark photos\n- Group photos\n- Copyrighted characters\n- Very low quality images",
    link: { text: "Upload Photo", url: "/app/photo-to-comic" }
  },
  
  // Story Packs
  "how do story packs work": {
    message: "Kids Story Packs create complete story content:\n\n1. Enter character name & age\n2. Choose theme (Adventure, Bedtime, etc.)\n3. Set story length\n4. Generate!\n\nYou get: Story text, character images, video-ready format, and printable version!",
    link: { text: "Create Story Pack", url: "/app/story-generator" },
    suggestions: ["Story pack themes", "What are credits?"]
  },
  "story pack themes": {
    message: "Available story themes:\n\n- Space Adventure\n- Magical Forest\n- Ocean Explorer\n- Dinosaur World\n- Fairy Tale Kingdom\n- Superhero Training\n- Animal Friends\n- Dream Journey\n\nAll stories are AI-generated, original, and kid-safe!",
    link: { text: "Start Creating", url: "/app/story-generator" }
  },
  
  // GIF Maker
  "how to make gifs": {
    message: "Creating reaction GIFs:\n\n1. Upload your photo (clear face)\n2. Choose reaction type (Happy, Surprised, etc.)\n3. Select animation style\n4. Generate & download!\n\nPerfect for social media reactions and memes!",
    link: { text: "Make GIF", url: "/app/gif-maker" },
    suggestions: ["Best reactions to use", "What images work best?"]
  },
  "best reactions to use": {
    message: "Popular reaction types:\n\n1. Happy - Joyful smile\n2. Laughing - LOL moments\n3. Love - Heart eyes\n4. Surprised - Wow face\n5. Cool - Sunglasses vibe\n6. Celebrate - Clapping\n7. Waving - Hello/Goodbye\n8. Wow - Fire/Amazing\n9. Sad - Emotional moments",
    link: { text: "Create GIF", url: "/app/gif-maker" }
  },
  
  // Coloring Books
  "how coloring books work": {
    message: "Two ways to create coloring books:\n\n1. Generate From Story - AI creates original coloring pages from your story idea\n2. Convert Photos - Turn any photo into a coloring page outline\n\nDownload as PDF, ready to print!",
    link: { text: "Create Coloring Book", url: "/app/coloring-book" },
    suggestions: ["Can I use photos?", "What are credits?"]
  },
  "can i use photos": {
    message: "Yes! You can convert photos to coloring pages:\n\n1. Upload any photo (people, pets, objects)\n2. AI extracts outlines\n3. Generates printable coloring page\n\nNote: Use photos you own or have permission to use. No copyrighted characters.",
    link: { text: "Convert Photo", url: "/app/coloring-book" }
  },
  
  // Support
  "contact support": {
    message: "Need help from our team?\n\nEmail: krajapraveen@visionary-suite.com\nResponse time: Within 24 hours\n\nOr use the Contact form on our website. Include your account email for faster support!",
    link: { text: "Contact Form", url: "/contact" },
    suggestions: ["Common issues", "How do I get started?"]
  },
  "common issues": {
    message: "Frequently asked:\n\n1. Generation taking long? - Usually 30-60 seconds\n2. Credits not updating? - Refresh the page\n3. Download not working? - Try a different browser\n4. Image quality poor? - Use higher resolution source\n\nStill stuck? Contact our support team!",
    link: { text: "Get Help", url: "/contact" }
  },
  
  // Features
  "best features to try": {
    message: "Start with these popular features:\n\n1. Reel Generator - Fastest, great results\n2. Comic Avatar - Fun transformation\n3. Reaction GIF - Social media ready\n4. Story Pack - Perfect for kids content\n\nAll features have guided wizards!",
    link: { text: "Explore Dashboard", url: "/app" }
  },
  "daily rewards": {
    message: "Claim free credits daily!\n\n- Visit your Dashboard\n- Click 'Daily Reward' button\n- Get bonus credits!\n\nThe more consecutive days you visit, the bigger the rewards!",
    link: { text: "Claim Reward", url: "/app" }
  }
};

// Find best matching response
const findResponse = (input) => {
  const lowerInput = input.toLowerCase().trim();
  
  // Exact match first
  for (const [key, response] of Object.entries(AUTO_RESPONSES)) {
    if (lowerInput === key || lowerInput.includes(key)) {
      return response;
    }
  }
  
  // Partial match
  for (const [key, response] of Object.entries(AUTO_RESPONSES)) {
    const keyWords = key.split(' ');
    const matchCount = keyWords.filter(word => lowerInput.includes(word)).length;
    if (matchCount >= Math.ceil(keyWords.length / 2)) {
      return response;
    }
  }
  
  // Keyword matching
  const keywords = {
    'credit': AUTO_RESPONSES['what are credits'],
    'price': AUTO_RESPONSES['pricing plans'],
    'cost': AUTO_RESPONSES['pricing plans'],
    'reel': AUTO_RESPONSES['how to generate reels'],
    'script': AUTO_RESPONSES['how to generate reels'],
    'comic': AUTO_RESPONSES['how to create comics'],
    'avatar': AUTO_RESPONSES['how to create comics'],
    'story': AUTO_RESPONSES['how do story packs work'],
    'kid': AUTO_RESPONSES['how do story packs work'],
    'gif': AUTO_RESPONSES['how to make gifs'],
    'reaction': AUTO_RESPONSES['how to make gifs'],
    'color': AUTO_RESPONSES['how coloring books work'],
    'support': AUTO_RESPONSES['contact support'],
    'help': AUTO_RESPONSES['contact support'],
    'start': AUTO_RESPONSES['how do i get started'],
    'begin': AUTO_RESPONSES['how do i get started'],
    'pay': AUTO_RESPONSES['payment methods'],
    'image': AUTO_RESPONSES['what images work best'],
    'photo': AUTO_RESPONSES['what images work best']
  };
  
  for (const [keyword, response] of Object.entries(keywords)) {
    if (lowerInput.includes(keyword)) {
      return response;
    }
  }
  
  // Default response
  return {
    message: "I'm here to help! Try asking about:\n\n- Getting started\n- Credits & pricing\n- Specific features (reels, comics, GIFs, stories)\n- Technical support\n\nOr click one of the quick questions below!",
    link: { text: "View All Features", url: "/app" },
    suggestions: ["How do I get started?", "What are credits?", "Contact support"]
  };
};

export default function LiveChatWidget() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      text: "Hi there! I'm your Visionary Suite assistant. How can I help you today?",
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const quickReplies = getQuickReplies(location.pathname);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus();
      setUnreadCount(0);
    }
  }, [isOpen, isMinimized]);

  // Context-aware greeting based on current page
  useEffect(() => {
    if (isOpen && messages.length === 1) {
      let contextMessage = null;
      
      if (location.pathname.includes('reel')) {
        contextMessage = "I see you're on the Reel Generator! Need help creating viral content?";
      } else if (location.pathname.includes('comic')) {
        contextMessage = "Ready to transform your photos into comics? I can help!";
      } else if (location.pathname.includes('gif')) {
        contextMessage = "Creating reaction GIFs? Let me guide you through it!";
      } else if (location.pathname.includes('billing')) {
        contextMessage = "Looking at our plans? I can help you choose the right one!";
      }
      
      if (contextMessage) {
        setTimeout(() => {
          setMessages(prev => [...prev, {
            id: Date.now(),
            type: 'bot',
            text: contextMessage,
            timestamp: new Date()
          }]);
        }, 1500);
      }
    }
  }, [isOpen, location.pathname]);

  const handleSend = (text = inputValue) => {
    if (!text.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: text.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    // Simulate thinking delay for more natural feel
    const thinkingTime = Math.random() * 500 + 800;
    
    setTimeout(() => {
      const response = findResponse(text);
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: response.message,
        link: response.link,
        suggestions: response.suggestions,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
      
      if (!isOpen) {
        setUnreadCount(prev => prev + 1);
      }
    }, thinkingTime);
  };

  const handleQuickReply = (reply) => {
    handleSend(reply.text || reply);
  };

  const handleSuggestionClick = (suggestion) => {
    handleSend(suggestion);
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
        className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
        data-testid="chat-widget-button"
        aria-label="Open chat"
      >
        <MessageCircle className="w-6 h-6 text-white" />
        {unreadCount > 0 ? (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full border-2 border-white flex items-center justify-center text-xs text-white font-bold">
            {unreadCount}
          </span>
        ) : (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white animate-pulse"></span>
        )}
        
        {/* Enhanced Tooltip */}
        <span className="absolute right-full mr-3 px-4 py-2 bg-slate-900 text-white text-sm rounded-xl opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-xl border border-slate-700">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            Need help? Chat with us!
          </span>
        </span>
      </button>
    );
  }

  return (
    <div 
      className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ${
        isMinimized ? 'w-80 h-16' : 'w-[360px] sm:w-[400px] h-[550px]'
      }`}
      data-testid="chat-widget"
    >
      <div className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 overflow-hidden h-full flex flex-col">
        {/* Enhanced Header */}
        <div className="bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                Visionary Assistant
                <span className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></span>
              </h3>
              <p className="text-white/80 text-xs">AI-powered help • Always online</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
              aria-label={isMinimized ? "Maximize" : "Minimize"}
            >
              {isMinimized ? <Maximize2 className="w-4 h-4 text-white" /> : <Minimize2 className="w-4 h-4 text-white" />}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
              aria-label="Close chat"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-slate-900 to-slate-950">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start gap-2 max-w-[85%] ${message.type === 'user' ? 'flex-row-reverse' : ''}`}>
                    {/* Avatar */}
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.type === 'user' 
                        ? 'bg-indigo-500' 
                        : 'bg-gradient-to-r from-emerald-500 to-teal-500'
                    }`}>
                      {message.type === 'user' ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-white" />
                      )}
                    </div>
                    
                    {/* Message Bubble */}
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        message.type === 'user'
                          ? 'bg-indigo-500 text-white rounded-tr-sm'
                          : 'bg-slate-800 text-slate-200 rounded-tl-sm border border-slate-700'
                      }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-line">{message.text}</p>
                      
                      {message.link && (
                        <a
                          href={message.link.url}
                          className="inline-flex items-center gap-1 mt-3 text-xs text-emerald-400 hover:text-emerald-300 font-medium"
                        >
                          {message.link.text}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                      
                      {/* Suggestion chips */}
                      {message.suggestions && message.suggestions.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-700/50">
                          <p className="text-xs text-slate-500 mb-2">Related questions:</p>
                          <div className="flex flex-wrap gap-2">
                            {message.suggestions.map((suggestion, idx) => (
                              <button
                                key={idx}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="text-xs px-2 py-1 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors flex items-center gap-1"
                              >
                                <ChevronRight className="w-3 h-3" />
                                {suggestion}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="flex items-start gap-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 border border-slate-700">
                      <div className="flex gap-1.5">
                        <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                        <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                        <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Context-Aware Quick Replies */}
            {messages.length <= 3 && (
              <div className="px-4 py-3 bg-slate-900/80 border-t border-slate-800">
                <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Quick questions:
                </p>
                <div className="flex flex-wrap gap-2">
                  {quickReplies.map((reply, idx) => {
                    const Icon = reply.icon || HelpCircle;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleQuickReply(reply)}
                        className="text-xs px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-all hover:scale-105 flex items-center gap-2 border border-slate-700/50"
                      >
                        <Icon className="w-3 h-3 text-emerald-400" />
                        {reply.text}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Enhanced Input Area */}
            <div className="p-4 bg-slate-900 border-t border-slate-800">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me anything..."
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                  data-testid="chat-input"
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={!inputValue.trim()}
                  className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 rounded-xl px-4 transition-all disabled:opacity-50"
                  data-testid="chat-send-btn"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              
              {/* Help Footer */}
              <div className="mt-3 flex items-center justify-center gap-4 text-xs text-slate-500">
                <a href="/contact" className="flex items-center gap-1 hover:text-emerald-400 transition-colors">
                  <Mail className="w-3 h-3" />
                  Email Support
                </a>
                <span className="text-slate-700">|</span>
                <a href="/user-manual" className="flex items-center gap-1 hover:text-emerald-400 transition-colors">
                  <BookOpen className="w-3 h-3" />
                  User Manual
                </a>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
