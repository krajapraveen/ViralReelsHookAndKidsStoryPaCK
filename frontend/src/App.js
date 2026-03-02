import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { NotificationProvider } from './contexts/NotificationContext';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import ReelGenerator from './pages/ReelGenerator';
import StoryGenerator from './pages/StoryGenerator';
import History from './pages/History';
import Billing from './pages/Billing';
import Pricing from './pages/Pricing';
import AdminDashboard from './pages/AdminDashboard';
import FeatureRequests from './pages/FeatureRequests';
import AuthCallback from './pages/AuthCallback';
import Contact from './pages/Contact';
import Reviews from './pages/Reviews';
import PrivacySettings from './pages/PrivacySettings';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import AutomationDashboard from './pages/AutomationDashboard';
import Profile from './pages/Profile';
import CopyrightInfo from './pages/CopyrightInfo';
import CreatorTools from './pages/CreatorTools';
// ContentVault removed - replaced by ContentBlueprintLibrary
import PaymentHistory from './pages/PaymentHistory';
import VerifyEmail from './pages/VerifyEmail';
import ResetPassword from './pages/ResetPassword';
// New Feature Pages
import CreatorProTools from './pages/CreatorProTools';
import TwinFinder from './pages/TwinFinder';
import ColoringBookWizard from './pages/ColoringBookWizard';
import StorySeries from './pages/StorySeries';
import ChallengeGenerator from './pages/ChallengeGenerator';
import ToneSwitcher from './pages/ToneSwitcher';
import UserManual from './pages/UserManual';
import AdminMonitoring from './pages/AdminMonitoring';
import AdminLoginActivity from './pages/AdminLoginActivity';
import AdminUsersManagement from './pages/AdminUsersManagement';
import SubscriptionManagement from './pages/SubscriptionManagement.jsx';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import ComixAI from './pages/ComixAI';
import PhotoToComic from './pages/PhotoToComic';
import GifMaker from './pages/GifMaker';
import PhotoReactionGIF from './pages/PhotoReactionGIF';
import ComicStorybook from './pages/ComicStorybook';
import ComicStorybookBuilder from './pages/ComicStorybookBuilder';
import RealtimeAnalytics from './pages/RealtimeAnalytics';
import SelfHealingDashboard from './pages/Admin/SelfHealingDashboard';
import UserAnalyticsDashboard from './pages/Admin/UserAnalyticsDashboard';
import SharePage from './pages/SharePage';
import ReferralProgram from './pages/ReferralProgram';
import AIChatbot from './components/AIChatbot';
import FeedbackWidget from './components/FeedbackWidget';
import AppTour, { TourProvider } from './components/AppTour';
// NEW REBUILT FEATURES
import StoryEpisodeCreator from './pages/StoryEpisodeCreator';
import ContentChallengePlanner from './pages/ContentChallengePlanner';
import CaptionRewriterPro from './pages/CaptionRewriterPro';
// CONTENT BLUEPRINT LIBRARY
import ContentBlueprintLibrary from './pages/ContentBlueprintLibrary';
// ADMIN SECURITY DASHBOARD
import AdminSecurityDashboard from './pages/AdminSecurityDashboard';
// ADMIN BIO TEMPLATES
import BioTemplatesAdmin from './pages/Admin/BioTemplatesAdmin';
// INSTAGRAM BIO GENERATOR
import InstagramBioGenerator from './pages/InstagramBioGenerator';
// COMMENT REPLY BANK
import CommentReplyBank from './pages/CommentReplyBank';
// BEDTIME STORY BUILDER
import BedtimeStoryBuilder from './pages/BedtimeStoryBuilder';
// MY DOWNLOADS
import MyDownloads from './pages/MyDownloads';
// NEW 5 TEMPLATE-BASED FEATURES
import YouTubeThumbnailGenerator from './pages/YouTubeThumbnailGenerator';
import BrandStoryBuilder from './pages/BrandStoryBuilder';
import OfferGenerator from './pages/OfferGenerator';
import StoryHookGenerator from './pages/StoryHookGenerator';
import DailyViralIdeas from './pages/DailyViralIdeas';
// TEMPLATE ANALYTICS DASHBOARD
import TemplateAnalyticsDashboard from './pages/Admin/TemplateAnalyticsDashboard';
// ADMIN AUDIT LOGS
import AdminAuditLogs from './pages/Admin/AuditLogs';
// TEMPLATE LEADERBOARD
import TemplateLeaderboard from './pages/Admin/TemplateLeaderboard';
// WORKER DASHBOARD
import WorkerDashboard from './pages/admin/WorkerDashboard';
// DAILY REPORT DASHBOARD
import DailyReportDashboard from './pages/Admin/DailyReportDashboard';
// ACCOUNT LOCK MANAGEMENT
import AccountLockManagement from './pages/Admin/AccountLockManagement';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <NotificationProvider>
    <TourProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/reviews" element={<Reviews />} />
        <Route path="/login" element={<Login setAuth={setIsAuthenticated} />} />
        <Route path="/signup" element={<Signup setAuth={setIsAuthenticated} />} />
        <Route path="/auth/callback" element={<AuthCallback setAuth={setIsAuthenticated} />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        
        {/* Public Share Page - No auth required */}
        <Route path="/share/:shareId" element={<SharePage />} />
        
        {/* Protected routes */}
        <Route path="/app" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/app/reels" element={isAuthenticated ? <ReelGenerator /> : <Navigate to="/login" />} />
        <Route path="/app/reel-generator" element={isAuthenticated ? <ReelGenerator /> : <Navigate to="/login" />} />
        <Route path="/app/reel" element={isAuthenticated ? <Navigate to="/app/reel-generator" /> : <Navigate to="/login" />} />
      <Route path="/app/stories" element={isAuthenticated ? <StoryGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/story-generator" element={isAuthenticated ? <StoryGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/story" element={isAuthenticated ? <Navigate to="/app/story-generator" /> : <Navigate to="/login" />} />
      <Route path="/app/story-pack" element={isAuthenticated ? <Navigate to="/app/story-generator" /> : <Navigate to="/login" />} />
      <Route path="/app/history" element={isAuthenticated ? <History /> : <Navigate to="/login" />} />
      <Route path="/app/billing" element={isAuthenticated ? <Billing /> : <Navigate to="/login" />} />
      <Route path="/app/admin" element={isAuthenticated ? <AdminDashboard /> : <Navigate to="/login" />} />
      <Route path="/app/admin/realtime-analytics" element={isAuthenticated ? <RealtimeAnalytics /> : <Navigate to="/login" />} />
      <Route path="/app/admin/automation" element={isAuthenticated ? <AutomationDashboard /> : <Navigate to="/login" />} />
      <Route path="/app/feature-requests" element={isAuthenticated ? <FeatureRequests /> : <Navigate to="/login" />} />
      <Route path="/app/privacy" element={isAuthenticated ? <PrivacySettings /> : <Navigate to="/login" />} />
      <Route path="/app/profile" element={isAuthenticated ? <Profile /> : <Navigate to="/login" />} />
      <Route path="/app/copyright" element={isAuthenticated ? <CopyrightInfo /> : <Navigate to="/login" />} />
      <Route path="/app/creator-tools" element={isAuthenticated ? <CreatorTools /> : <Navigate to="/login" />} />
      {/* Content Vault deprecated - redirect to Blueprint Library */}
      <Route path="/app/content-vault" element={<Navigate to="/app/blueprint-library" replace />} />
      <Route path="/app/blueprint-library" element={isAuthenticated ? <ContentBlueprintLibrary /> : <Navigate to="/login" />} />
      <Route path="/app/payment-history" element={isAuthenticated ? <PaymentHistory /> : <Navigate to="/login" />} />
      {/* Creator Pro & TwinFinder Routes */}
      <Route path="/app/creator-pro" element={isAuthenticated ? <CreatorProTools /> : <Navigate to="/login" />} />
      <Route path="/app/twinfinder" element={isAuthenticated ? <TwinFinder /> : <Navigate to="/login" />} />
      {/* Coloring Book Wizard - Complete 5-Step Rebuild */}
      <Route path="/app/coloring-book" element={isAuthenticated ? <ColoringBookWizard /> : <Navigate to="/login" />} />
      {/* New Standalone Apps */}
      <Route path="/app/story-series" element={isAuthenticated ? <StorySeries /> : <Navigate to="/login" />} />
      <Route path="/app/challenge-generator" element={isAuthenticated ? <ChallengeGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/tone-switcher" element={isAuthenticated ? <ToneSwitcher /> : <Navigate to="/login" />} />
      {/* NEW REBUILT FEATURES - Simple Wizard UIs */}
      <Route path="/app/story-episode-creator" element={isAuthenticated ? <StoryEpisodeCreator /> : <Navigate to="/login" />} />
      <Route path="/app/content-challenge-planner" element={isAuthenticated ? <ContentChallengePlanner /> : <Navigate to="/login" />} />
      <Route path="/app/caption-rewriter" element={isAuthenticated ? <CaptionRewriterPro /> : <Navigate to="/login" />} />
      {/* User Manual - Available to all */}
      <Route path="/user-manual" element={<UserManual />} />
      <Route path="/help" element={<UserManual />} />
      {/* User Dashboard Routes */}
      <Route path="/app/subscription" element={isAuthenticated ? <SubscriptionManagement /> : <Navigate to="/login" />} />
      <Route path="/app/analytics" element={isAuthenticated ? <AnalyticsDashboard /> : <Navigate to="/login" />} />
      {/* Admin Routes */}
      <Route path="/app/admin/monitoring" element={isAuthenticated ? <AdminMonitoring /> : <Navigate to="/login" />} />
      <Route path="/app/admin/login-activity" element={isAuthenticated ? <AdminLoginActivity /> : <Navigate to="/login" />} />
      <Route path="/app/admin/users" element={isAuthenticated ? <AdminUsersManagement /> : <Navigate to="/login" />} />
      <Route path="/app/admin/self-healing" element={isAuthenticated ? <SelfHealingDashboard /> : <Navigate to="/login" />} />
      <Route path="/app/admin/user-analytics" element={isAuthenticated ? <UserAnalyticsDashboard /> : <Navigate to="/login" />} />
      <Route path="/app/admin/security" element={isAuthenticated ? <AdminSecurityDashboard /> : <Navigate to="/login" />} />
      <Route path="/app/admin/bio-templates" element={isAuthenticated ? <BioTemplatesAdmin /> : <Navigate to="/login" />} />
      <Route path="/app/admin/workers" element={isAuthenticated ? <WorkerDashboard /> : <Navigate to="/login" />} />
      {/* New Feature Routes */}
      <Route path="/app/comix" element={isAuthenticated ? <PhotoToComic /> : <Navigate to="/login" />} />
      <Route path="/app/comix-ai" element={isAuthenticated ? <PhotoToComic /> : <Navigate to="/login" />} />
      <Route path="/app/photo-to-comic" element={isAuthenticated ? <PhotoToComic /> : <Navigate to="/login" />} />
      <Route path="/app/gif-maker" element={isAuthenticated ? <PhotoReactionGIF /> : <Navigate to="/login" />} />
      <Route path="/app/reaction-gif" element={isAuthenticated ? <PhotoReactionGIF /> : <Navigate to="/login" />} />
      <Route path="/app/gif-maker-old" element={isAuthenticated ? <GifMaker /> : <Navigate to="/login" />} />
      <Route path="/app/comic-storybook" element={isAuthenticated ? <ComicStorybookBuilder /> : <Navigate to="/login" />} />
      <Route path="/app/comic-storybook-old" element={isAuthenticated ? <ComicStorybook /> : <Navigate to="/login" />} />
      <Route path="/app/referral" element={isAuthenticated ? <ReferralProgram /> : <Navigate to="/login" />} />
      <Route path="/app/gift-cards" element={isAuthenticated ? <ReferralProgram /> : <Navigate to="/login" />} />
      {/* Instagram Bio Generator */}
      <Route path="/app/instagram-bio-generator" element={isAuthenticated ? <InstagramBioGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/bio-generator" element={isAuthenticated ? <InstagramBioGenerator /> : <Navigate to="/login" />} />
      {/* Comment Reply Bank */}
      <Route path="/app/comment-reply-bank" element={isAuthenticated ? <CommentReplyBank /> : <Navigate to="/login" />} />
      <Route path="/app/reply-bank" element={isAuthenticated ? <CommentReplyBank /> : <Navigate to="/login" />} />
      {/* Bedtime Story Builder */}
      <Route path="/app/bedtime-story-builder" element={isAuthenticated ? <BedtimeStoryBuilder /> : <Navigate to="/login" />} />
      <Route path="/app/bedtime-stories" element={isAuthenticated ? <BedtimeStoryBuilder /> : <Navigate to="/login" />} />
      {/* My Downloads */}
      <Route path="/app/downloads" element={isAuthenticated ? <MyDownloads /> : <Navigate to="/login" />} />
      <Route path="/app/my-downloads" element={isAuthenticated ? <MyDownloads /> : <Navigate to="/login" />} />
      {/* NEW 5 TEMPLATE-BASED FEATURES */}
      <Route path="/app/thumbnail-generator" element={isAuthenticated ? <YouTubeThumbnailGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/brand-story-builder" element={isAuthenticated ? <BrandStoryBuilder /> : <Navigate to="/login" />} />
      <Route path="/app/offer-generator" element={isAuthenticated ? <OfferGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/story-hook-generator" element={isAuthenticated ? <StoryHookGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/daily-viral-ideas" element={isAuthenticated ? <DailyViralIdeas /> : <Navigate to="/login" />} />
      {/* TEMPLATE ANALYTICS DASHBOARD */}
      <Route path="/app/admin/template-analytics" element={isAuthenticated ? <TemplateAnalyticsDashboard /> : <Navigate to="/login" />} />
      {/* ADMIN AUDIT LOGS */}
      <Route path="/app/admin/audit-logs" element={isAuthenticated ? <AdminAuditLogs /> : <Navigate to="/login" />} />
      {/* TEMPLATE LEADERBOARD */}
      <Route path="/app/admin/leaderboard" element={isAuthenticated ? <TemplateLeaderboard /> : <Navigate to="/login" />} />
      {/* DAILY REPORT DASHBOARD */}
      <Route path="/app/admin/daily-report" element={isAuthenticated ? <DailyReportDashboard /> : <Navigate to="/login" />} />
      {/* ACCOUNT LOCK MANAGEMENT */}
      <Route path="/app/admin/account-locks" element={isAuthenticated ? <AccountLockManagement /> : <Navigate to="/login" />} />
      <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      <Route path="/terms" element={<TermsOfService />} />
      <Route path="/terms-of-service" element={<TermsOfService />} />
      </Routes>
      
      {/* AI Chatbot - Available on all pages */}
      <AIChatbot />
      
      {/* Feedback Widget - Collect user suggestions */}
      <FeedbackWidget />
    </TourProvider>
    </NotificationProvider>
  );
}

export default App;