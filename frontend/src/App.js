import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
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
import AutomationDashboard from './pages/AutomationDashboard';
import Profile from './pages/Profile';
import CopyrightInfo from './pages/CopyrightInfo';
import CreatorTools from './pages/CreatorTools';
import ContentVault from './pages/ContentVault';
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
      <Route path="/app/content-vault" element={isAuthenticated ? <ContentVault /> : <Navigate to="/login" />} />
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
      <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      </Routes>
      
      {/* AI Chatbot - Available on all pages */}
      <AIChatbot />
      
      {/* Feedback Widget - Collect user suggestions */}
      <FeedbackWidget />
    </TourProvider>
  );
}

export default App;