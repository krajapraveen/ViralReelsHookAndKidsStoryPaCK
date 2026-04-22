import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { NotificationProvider } from './contexts/NotificationContext';
import { CreditProvider } from './contexts/CreditContext';
import { MediaEntitlementProvider } from './contexts/MediaEntitlementContext';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { FeedbackProvider } from './contexts/FeedbackContext';
import { ProductGuideProvider } from './contexts/ProductGuideContext';
import { ContentProtectionWrapper } from './components/ContentProtectionWrapper';
import GlobalUserBar from './components/GlobalUserBar';
import { ErrorBoundary } from './components/recovery';
import AppTour, { TourProvider } from './components/AppTour';
import CookieConsent from './components/CookieConsent';
import PushPrompt from './components/PushPrompt';
import useSessionTracker from './utils/useSessionTracker';
import './App.css';

// ═══ CRITICAL PATH — Eager imports (landing, auth, dashboard) ═══
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import AuthCallback from './pages/AuthCallback';

// ═══ LIGHTWEIGHT — Small components always needed ═══
import JourneyProgressBar from './components/guide/JourneyProgressBar';
import FirstActionOverlay from './components/guide/FirstActionOverlay';
import PostValueOverlay from './components/guide/PostValueOverlay';
import { UpgradeModal } from './components/UpgradeModal';
import ResponsiveSupportWrapper from './components/support/ResponsiveSupportWrapper';
import GuideAssistant from './components/guide/GuideAssistant';

// ═══ ROUTE-LEVEL LAZY LOADING — Everything else loaded on demand ═══
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <div className="text-center">
      <div className="relative w-8 h-8 mx-auto mb-3">
        <div className="absolute inset-0 rounded-full border-2 border-slate-700/50" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-500 animate-spin" />
      </div>
      <p className="text-slate-500 text-xs">Loading...</p>
    </div>
  </div>
);

// Public pages
const Pricing = lazy(() => import('./pages/Pricing'));
const Contact = lazy(() => import('./pages/Contact'));
const Reviews = lazy(() => import('./pages/Reviews'));
const AboutPage = lazy(() => import('./pages/AboutPage'));
const SecurityPage = lazy(() => import('./pages/SecurityPage'));
const SecurityReportPage = lazy(() => import('./pages/SecurityReportPage'));
const SecurityReportSubmittedPage = lazy(() => import('./pages/SecurityReportSubmittedPage'));
const AdminSecurityReports = lazy(() => import('./pages/AdminSecurityReports'));
const AdminSecurityReportDetail = lazy(() => import('./pages/AdminSecurityReportDetail'));
const ReferLanding = lazy(() => import('./pages/ReferLanding'));
const ReferralsPage = lazy(() => import('./pages/ReferralsPage'));
const AdminReferrals = lazy(() => import('./pages/AdminReferrals'));
const Blog = lazy(() => import('./pages/Blog'));
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const SharePage = lazy(() => import('./pages/SharePage'));
const ViralPackShare = lazy(() => import('./pages/ViralPackShare'));
const Gallery = lazy(() => import('./pages/Gallery'));
const ExplorePage = lazy(() => import('./pages/ExplorePage'));
const PublicCreation = lazy(() => import('./pages/PublicCreation'));
const CreatorProfile = lazy(() => import('./pages/CreatorProfile'));
const PublicCharacterPage = lazy(() => import('./pages/PublicCharacterPage'));
const PublicSeries = lazy(() => import('./pages/PublicSeries'));
const InstantStoryExperience = lazy(() => import('./pages/InstantStoryExperience'));
const UserManual = lazy(() => import('./pages/UserManual'));
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy'));
const TermsOfService = lazy(() => import('./pages/TermsOfService'));
const CookiePolicy = lazy(() => import('./pages/CookiePolicy'));

// Core app pages
const StoryVideoPipeline = lazy(() => import('./pages/StoryVideoPipeline'));
const StoryPreview = lazy(() => import('./pages/StoryPreview'));
const StoryBattlePage = lazy(() => import('./pages/StoryBattlePage'));
const StoryViewerPage = lazy(() => import('./pages/StoryViewerPage'));
const StoryChainView = lazy(() => import('./pages/StoryChainView'));
const StoryChainTimeline = lazy(() => import('./pages/StoryChainTimeline'));
const DailyWarPage = lazy(() => import('./pages/DailyWarPage'));
const MyStories = lazy(() => import('./pages/MyStories'));

// Creator tools
const ReelGenerator = lazy(() => import('./pages/ReelGenerator'));
const StoryGenerator = lazy(() => import('./pages/StoryGenerator'));
const ComicStorybookBuilder = lazy(() => import('./pages/ComicStorybookBuilder'));
const PhotoToComic = lazy(() => import('./pages/PhotoToComic'));
const PhotoReactionGIF = lazy(() => import('./pages/PhotoReactionGIF'));
const GifMaker = lazy(() => import('./pages/GifMaker'));
const ComicStorybook = lazy(() => import('./pages/ComicStorybook'));
const CharacterConsistencyStudio = lazy(() => import('./pages/CharacterConsistencyStudio'));
const ColoringBookWizard = lazy(() => import('./pages/ColoringBookWizard'));
const BedtimeStoryBuilder = lazy(() => import('./pages/BedtimeStoryBuilder'));
const StoryEpisodeCreator = lazy(() => import('./pages/StoryEpisodeCreator'));
const ContentChallengePlanner = lazy(() => import('./pages/ContentChallengePlanner'));
const CaptionRewriterPro = lazy(() => import('./pages/CaptionRewriterPro'));
const PromoVideos = lazy(() => import('./pages/PromoVideos'));

// Navigation / user pages
const MySpacePage = lazy(() => import('./pages/MySpacePage'));
const CreatePage = lazy(() => import('./pages/CreatePage'));
const BrowsePage = lazy(() => import('./pages/BrowsePage'));
const CharactersPage = lazy(() => import('./pages/CharactersPage'));
const UserDashboardPage = lazy(() => import('./pages/UserDashboardPage'));
const History = lazy(() => import('./pages/History'));
const Billing = lazy(() => import('./pages/Billing'));
const Profile = lazy(() => import('./pages/Profile'));
const PrivacySettings = lazy(() => import('./pages/PrivacySettings'));
const CopyrightInfo = lazy(() => import('./pages/CopyrightInfo'));
const CreatorTools = lazy(() => import('./pages/CreatorTools'));
const PaymentHistory = lazy(() => import('./pages/PaymentHistory'));
const FeatureRequests = lazy(() => import('./pages/FeatureRequests'));
const ReferralProgram = lazy(() => import('./pages/ReferralProgram'));
const MyDownloads = lazy(() => import('./pages/MyDownloads'));
const PricingPage = lazy(() => import('./pages/PricingPage'));
const SubscriptionManagement = lazy(() => import('./pages/SubscriptionManagement.jsx'));
const AnalyticsDashboard = lazy(() => import('./pages/AnalyticsDashboard'));

// Series / Characters
const StorySeries = lazy(() => import('./pages/StorySeries'));
const CreateSeries = lazy(() => import('./pages/CreateSeries'));
const SeriesTimeline = lazy(() => import('./pages/SeriesTimeline'));
const CharacterCreator = lazy(() => import('./pages/CharacterCreator'));
const CharacterLibrary = lazy(() => import('./pages/CharacterLibrary'));
const CharacterDetail = lazy(() => import('./pages/CharacterDetail'));

// Template features
const CreatorProTools = lazy(() => import('./pages/CreatorProTools'));
const TwinFinder = lazy(() => import('./pages/TwinFinder'));
const ChallengeGenerator = lazy(() => import('./pages/ChallengeGenerator'));
const ToneSwitcher = lazy(() => import('./pages/ToneSwitcher'));
const ContentBlueprintLibrary = lazy(() => import('./pages/ContentBlueprintLibrary'));
const InstagramBioGenerator = lazy(() => import('./pages/InstagramBioGenerator'));
const CommentReplyBank = lazy(() => import('./pages/CommentReplyBank'));
const YouTubeThumbnailGenerator = lazy(() => import('./pages/YouTubeThumbnailGenerator'));
const BrandStoryBuilder = lazy(() => import('./pages/BrandStoryBuilder'));
const OfferGenerator = lazy(() => import('./pages/OfferGenerator'));
const StoryHookGenerator = lazy(() => import('./pages/StoryHookGenerator'));
const DailyViralIdeas = lazy(() => import('./pages/DailyViralIdeas'));
const ConversionDashboard = lazy(() => import('./pages/ConversionDashboard'));
const ContentEngine = lazy(() => import('./pages/ContentEngine'));

// Admin — entire admin chunk lazy loaded
const AdminLayout = lazy(() => import('./components/AdminLayout'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const RetentionDashboard = lazy(() => import('./pages/RetentionDashboard'));
const AutomationDashboard = lazy(() => import('./pages/AutomationDashboard'));
const RealtimeAnalytics = lazy(() => import('./pages/RealtimeAnalytics'));
const AdminMonitoring = lazy(() => import('./pages/AdminMonitoring'));
const AdminLoginActivity = lazy(() => import('./pages/AdminLoginActivity'));
const AdminUsersManagement = lazy(() => import('./pages/AdminUsersManagement'));
const StoryVideoAnalyticsDashboard = lazy(() => import('./pages/StoryVideoAnalyticsDashboard'));
const SelfHealingDashboard = lazy(() => import('./pages/Admin/SelfHealingDashboard'));
const UserAnalyticsDashboard = lazy(() => import('./pages/Admin/UserAnalyticsDashboard'));
const AdminSecurityDashboard = lazy(() => import('./pages/AdminSecurityDashboard'));
const BioTemplatesAdmin = lazy(() => import('./pages/Admin/BioTemplatesAdmin'));
const WorkerDashboard = lazy(() => import('./pages/admin/WorkerDashboard'));
const TTFDDashboard = lazy(() => import('./pages/admin/TTFDDashboard'));
const PaymentsDashboard = lazy(() => import('./pages/admin/PaymentsDashboard'));
const TemplateAnalyticsDashboard = lazy(() => import('./pages/Admin/TemplateAnalyticsDashboard'));
const AdminAuditLogs = lazy(() => import('./pages/Admin/AuditLogs'));
const TemplateLeaderboard = lazy(() => import('./pages/Admin/TemplateLeaderboard'));
const DailyReportDashboard = lazy(() => import('./pages/Admin/DailyReportDashboard'));
const AccountLockManagement = lazy(() => import('./pages/Admin/AccountLockManagement'));
const EnvironmentMonitor = lazy(() => import('./pages/Admin/EnvironmentMonitor'));
const UserActivityDashboard = lazy(() => import('./pages/Admin/UserActivityDashboard'));
const SystemHealthDashboard = lazy(() => import('./pages/Admin/SystemHealthDashboard'));
const AntiAbuseDashboard = lazy(() => import('./pages/Admin/AntiAbuseDashboard'));
const RevenueAnalyticsDashboard = lazy(() => import('./pages/Admin/RevenueAnalyticsDashboard'));
const MonitoringDashboard = lazy(() => import('./pages/Admin/MonitoringDashboard'));
const GA4EventTester = lazy(() => import('./pages/Admin/GA4EventTester'));
const AdminFeedbackPage = lazy(() => import('./pages/Admin/AdminFeedbackPage'));
const GrowthDashboard = lazy(() => import('./pages/Admin/GrowthDashboard'));
const ProductionMetrics = lazy(() => import('./pages/Admin/ProductionMetrics'));
const MediaSecurityDashboard = lazy(() => import('./pages/Admin/MediaSecurityDashboard'));

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

/** Protected route wrapper */
function ProtectedRoute({ auth, children }) {
  const loc = useLocation();
  if (!auth) {
    if (loc.pathname && loc.pathname !== '/login' && loc.pathname !== '/signup') {
      localStorage.setItem('auth_return_path', loc.pathname);
    }
    return <Navigate to="/login" state={{ from: loc }} replace />;
  }
  return children;
}

function AuthenticatedRedirect() {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const returnParam = searchParams.get('return');
  const returnUrl = returnParam || localStorage.getItem('remix_return_url') || '/app';
  if (returnParam || localStorage.getItem('remix_return_url')) {
    localStorage.removeItem('remix_return_url');
  }
  return <Navigate to={returnUrl} replace />;
}

/** Lazy wrapper with suspense fallback */
function L({ children }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [paywallReason, setPaywallReason] = useState('post_value');

  // Session tracking — fires session_started / session_ended
  useSessionTracker();

  const triggerPaywall = useCallback((reason = 'post_value') => {
    setPaywallReason(reason);
    setPaywallOpen(true);
  }, []);

  useEffect(() => {
    const handler = (e) => triggerPaywall(e.detail?.reason || 'exit_interception');
    window.addEventListener('trigger-paywall', handler);
    return () => window.removeEventListener('trigger-paywall', handler);
  }, [triggerPaywall]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) setIsAuthenticated(true);
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%)' }}>
        <div className="text-center">
          <div className="relative w-10 h-10 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-slate-700/50" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-500 animate-spin" />
          </div>
          <p className="text-slate-400 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
    <NotificationProvider>
    <CreditProvider>
    <MediaEntitlementProvider>
    <TourProvider>
    <FeedbackProvider>
    <ProductGuideProvider>
    <ContentProtectionWrapper>
      {isAuthenticated && (() => {
        try {
          const t = localStorage.getItem('token');
          if (t) {
            const p = JSON.parse(atob(t.split('.')[1]));
            if (p.role?.toUpperCase() === 'ADMIN' || p.role?.toUpperCase() === 'SUPERADMIN') return null;
          }
        } catch {}
        const path = window.location.pathname;
        if (path.includes('story-video-studio') || path.includes('character-consistency')) {
          return <JourneyProgressBar />;
        }
        return null;
      })()}
      {isAuthenticated && <GlobalUserBar />}
      <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* ═══ PUBLIC — Eager loaded ═══ */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={isAuthenticated ? <AuthenticatedRedirect /> : <Login setAuth={setIsAuthenticated} />} />
        <Route path="/signup" element={isAuthenticated ? <AuthenticatedRedirect /> : <Signup setAuth={setIsAuthenticated} />} />
        <Route path="/auth/callback" element={<AuthCallback setAuth={setIsAuthenticated} />} />

        {/* ═══ PUBLIC — Lazy loaded ═══ */}
        <Route path="/pricing" element={<L><Pricing /></L>} />
        <Route path="/contact" element={<L><Contact /></L>} />
        <Route path="/reviews" element={<L><Reviews /></L>} />
        <Route path="/about" element={<L><AboutPage /></L>} />
        <Route path="/blog" element={<L><Blog /></L>} />
        <Route path="/blog/:slug" element={<L><Blog /></L>} />
        <Route path="/verify-email" element={<L><VerifyEmail /></L>} />
        <Route path="/reset-password" element={<L><ResetPassword /></L>} />
        <Route path="/forgot-password" element={<L><ForgotPassword /></L>} />
        <Route path="/share/:shareId" element={<L><SharePage /></L>} />
        <Route path="/viral/:jobId" element={<L><ViralPackShare /></L>} />
        <Route path="/gallery" element={<L><Gallery /></L>} />
        <Route path="/explore" element={<L><ExplorePage /></L>} />
        <Route path="/app/explore" element={<L><ExplorePage /></L>} />
        <Route path="/v/:slug" element={<L><PublicCreation /></L>} />
        <Route path="/character/:characterId" element={<L><PublicCharacterPage /></L>} />
        <Route path="/creator/:username" element={<L><CreatorProfile /></L>} />
        <Route path="/series/:seriesId" element={<L><PublicSeries /></L>} />
        <Route path="/experience" element={<L><InstantStoryExperience /></L>} />
        <Route path="/user-manual" element={<L><UserManual /></L>} />
        <Route path="/help" element={<L><UserManual /></L>} />
        <Route path="/privacy-policy" element={<L><PrivacyPolicy /></L>} />
        <Route path="/cookie-policy" element={<L><CookiePolicy /></L>} />
        <Route path="/terms" element={<L><TermsOfService /></L>} />
        <Route path="/terms-of-service" element={<L><TermsOfService /></L>} />

        {/* ═══ SECURITY / VDP ═══ */}
        <Route path="/security" element={<L><SecurityPage /></L>} />
        <Route path="/security/report" element={<L><SecurityReportPage /></L>} />
        <Route path="/security/report/submitted" element={<L><SecurityReportSubmittedPage /></L>} />

        {/* ═══ REFERRALS ═══ */}
        <Route path="/refer" element={<L><ReferLanding /></L>} />

        {/* ═══ CORE APP — Dashboard eager, rest lazy ═══ */}
        <Route path="/app" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/app/story-video-studio" element={<L><ErrorBoundary><StoryVideoPipeline /></ErrorBoundary></L>} />
        <Route path="/app/story-preview/:jobId" element={<L><StoryPreview /></L>} />
        <Route path="/app/story-battle/:storyId" element={isAuthenticated ? <L><StoryBattlePage /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-viewer/:jobId" element={isAuthenticated ? <L><StoryViewerPage /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-chain/:chainId" element={isAuthenticated ? <L><StoryChainView /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-chain-timeline/:storyId" element={isAuthenticated ? <L><StoryChainTimeline /></L> : <Navigate to="/login" />} />
        <Route path="/app/war" element={isAuthenticated ? <L><DailyWarPage /></L> : <Navigate to="/login" />} />
        <Route path="/app/my-stories" element={isAuthenticated ? <L><MyStories /></L> : <Navigate to="/login" />} />

        {/* ═══ NAVIGATION PAGES ═══ */}
        <Route path="/app/my-space" element={isAuthenticated ? <L><MySpacePage /></L> : <Navigate to="/login" />} />
        <Route path="/app/my-space/:assetId" element={isAuthenticated ? <L><MySpacePage /></L> : <Navigate to="/login" />} />
        <Route path="/app/create" element={isAuthenticated ? <L><CreatePage /></L> : <Navigate to="/login" />} />
        <Route path="/app/browse" element={isAuthenticated ? <L><BrowsePage /></L> : <Navigate to="/login" />} />
        <Route path="/app/characters" element={isAuthenticated ? <L><CharacterLibrary /></L> : <Navigate to="/login" />} />
        <Route path="/app/dashboard" element={isAuthenticated ? <L><UserDashboardPage /></L> : <Navigate to="/login" />} />
        <Route path="/app/referrals" element={isAuthenticated ? <L><ReferralsPage /></L> : <Navigate to="/login" />} />
        <Route path="/dashboard/referrals" element={isAuthenticated ? <L><ReferralsPage /></L> : <Navigate to="/login" />} />

        {/* ═══ CREATOR TOOLS ═══ */}
        <Route path="/app/reels" element={isAuthenticated ? <L><ReelGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/reel-generator" element={isAuthenticated ? <L><ReelGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/reel" element={isAuthenticated ? <Navigate to="/app/reel-generator" /> : <Navigate to="/login" />} />
        <Route path="/app/stories" element={isAuthenticated ? <L><StoryGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/kids-story" element={isAuthenticated ? <L><StoryGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-generator" element={isAuthenticated ? <L><StoryGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/story" element={isAuthenticated ? <Navigate to="/app/story-generator" /> : <Navigate to="/login" />} />
        <Route path="/app/story-pack" element={isAuthenticated ? <Navigate to="/app/story-generator" /> : <Navigate to="/login" />} />
        <Route path="/app/character-studio" element={isAuthenticated ? <L><CharacterConsistencyStudio /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-video-studio/characters" element={isAuthenticated ? <L><CharacterConsistencyStudio /></L> : <Navigate to="/login" />} />
        <Route path="/app/coloring-book" element={isAuthenticated ? <L><ColoringBookWizard /></L> : <Navigate to="/login" />} />
        <Route path="/app/comic" element={isAuthenticated ? <L><PhotoToComic /></L> : <Navigate to="/login" />} />
        <Route path="/app/comix" element={isAuthenticated ? <L><PhotoToComic /></L> : <Navigate to="/login" />} />
        <Route path="/app/comix-ai" element={isAuthenticated ? <L><PhotoToComic /></L> : <Navigate to="/login" />} />
        <Route path="/app/photo-to-comic" element={isAuthenticated ? <L><PhotoToComic /></L> : <Navigate to="/login" />} />
        <Route path="/app/gif-maker" element={isAuthenticated ? <L><PhotoReactionGIF /></L> : <Navigate to="/login" />} />
        <Route path="/app/reaction-gif" element={isAuthenticated ? <L><PhotoReactionGIF /></L> : <Navigate to="/login" />} />
        <Route path="/app/gif-maker-old" element={isAuthenticated ? <L><GifMaker /></L> : <Navigate to="/login" />} />
        <Route path="/app/comic-storybook" element={isAuthenticated ? <L><ComicStorybookBuilder /></L> : <Navigate to="/login" />} />
        <Route path="/app/comic-story-builder" element={isAuthenticated ? <L><ComicStorybookBuilder /></L> : <Navigate to="/login" />} />
        <Route path="/app/comic-storybook-old" element={isAuthenticated ? <L><ComicStorybook /></L> : <Navigate to="/login" />} />
        <Route path="/app/bedtime-story-builder" element={isAuthenticated ? <L><BedtimeStoryBuilder /></L> : <Navigate to="/login" />} />
        <Route path="/app/bedtime-stories" element={isAuthenticated ? <L><BedtimeStoryBuilder /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-episode-creator" element={isAuthenticated ? <L><StoryEpisodeCreator /></L> : <Navigate to="/login" />} />
        <Route path="/app/content-challenge-planner" element={isAuthenticated ? <L><ContentChallengePlanner /></L> : <Navigate to="/login" />} />
        <Route path="/app/caption-rewriter" element={isAuthenticated ? <L><CaptionRewriterPro /></L> : <Navigate to="/login" />} />
        <Route path="/app/promo-videos" element={isAuthenticated ? <L><PromoVideos /></L> : <Navigate to="/login" />} />

        {/* ═══ USER PAGES ═══ */}
        <Route path="/app/history" element={isAuthenticated ? <L><History /></L> : <Navigate to="/login" />} />
        <Route path="/app/billing" element={isAuthenticated ? <L><Billing /></L> : <Navigate to="/login" />} />
        <Route path="/app/profile" element={isAuthenticated ? <L><Profile /></L> : <Navigate to="/login" />} />
        <Route path="/app/privacy" element={isAuthenticated ? <L><PrivacySettings /></L> : <Navigate to="/login" />} />
        <Route path="/app/copyright" element={isAuthenticated ? <L><CopyrightInfo /></L> : <Navigate to="/login" />} />
        <Route path="/app/creator-tools" element={isAuthenticated ? <L><CreatorTools /></L> : <Navigate to="/login" />} />
        <Route path="/app/content-vault" element={<Navigate to="/app/blueprint-library" replace />} />
        <Route path="/app/blueprint-library" element={isAuthenticated ? <L><ContentBlueprintLibrary /></L> : <Navigate to="/login" />} />
        <Route path="/app/payment-history" element={isAuthenticated ? <L><PaymentHistory /></L> : <Navigate to="/login" />} />
        <Route path="/app/feature-requests" element={isAuthenticated ? <L><FeatureRequests /></L> : <Navigate to="/login" />} />
        <Route path="/app/referral" element={isAuthenticated ? <L><ReferralProgram /></L> : <Navigate to="/login" />} />
        <Route path="/app/gift-cards" element={isAuthenticated ? <L><ReferralProgram /></L> : <Navigate to="/login" />} />
        <Route path="/app/downloads" element={isAuthenticated ? <L><MyDownloads /></L> : <Navigate to="/login" />} />
        <Route path="/app/my-downloads" element={isAuthenticated ? <L><MyDownloads /></L> : <Navigate to="/login" />} />
        <Route path="/app/pricing" element={isAuthenticated ? <L><PricingPage /></L> : <Navigate to="/login" />} />
        <Route path="/app/subscription" element={isAuthenticated ? <L><SubscriptionManagement /></L> : <Navigate to="/login" />} />
        <Route path="/app/analytics" element={isAuthenticated ? <L><AnalyticsDashboard /></L> : <Navigate to="/login" />} />

        {/* ═══ SERIES / CHARACTERS ═══ */}
        <Route path="/app/story-series" element={isAuthenticated ? <L><StorySeries /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-series/create" element={isAuthenticated ? <L><CreateSeries /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-series/:seriesId" element={<L><SeriesTimeline /></L>} />
        <Route path="/app/characters/create" element={isAuthenticated ? <L><CharacterCreator /></L> : <Navigate to="/login" />} />
        <Route path="/app/characters/:characterId" element={isAuthenticated ? <L><CharacterDetail /></L> : <Navigate to="/login" />} />

        {/* ═══ TEMPLATE FEATURES ═══ */}
        <Route path="/app/creator-pro" element={isAuthenticated ? <L><CreatorProTools /></L> : <Navigate to="/login" />} />
        <Route path="/app/twinfinder" element={isAuthenticated ? <L><TwinFinder /></L> : <Navigate to="/login" />} />
        <Route path="/app/challenge-generator" element={isAuthenticated ? <L><ChallengeGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/tone-switcher" element={isAuthenticated ? <L><ToneSwitcher /></L> : <Navigate to="/login" />} />
        <Route path="/app/instagram-bio-generator" element={isAuthenticated ? <L><InstagramBioGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/bio-generator" element={isAuthenticated ? <L><InstagramBioGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/comment-reply-bank" element={isAuthenticated ? <L><CommentReplyBank /></L> : <Navigate to="/login" />} />
        <Route path="/app/reply-bank" element={isAuthenticated ? <L><CommentReplyBank /></L> : <Navigate to="/login" />} />
        <Route path="/app/thumbnail-generator" element={isAuthenticated ? <L><YouTubeThumbnailGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/brand-story-builder" element={isAuthenticated ? <L><BrandStoryBuilder /></L> : <Navigate to="/login" />} />
        <Route path="/app/offer-generator" element={isAuthenticated ? <L><OfferGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/story-hook-generator" element={isAuthenticated ? <L><StoryHookGenerator /></L> : <Navigate to="/login" />} />
        <Route path="/app/daily-viral-ideas" element={isAuthenticated ? <L><DailyViralIdeas /></L> : <Navigate to="/login" />} />

        {/* ═══ ADMIN — Entire admin lazy loaded ═══ */}
        <Route path="/app/admin" element={<L><AdminLayout /></L>}>
          <Route index element={<L><AdminDashboard /></L>} />
          <Route path="realtime-analytics" element={<L><RealtimeAnalytics /></L>} />
          <Route path="automation" element={<L><AutomationDashboard /></L>} />
          <Route path="story-video-analytics" element={<L><StoryVideoAnalyticsDashboard /></L>} />
          <Route path="performance" element={<L><AdminMonitoring /></L>} />
          <Route path="login-activity" element={<L><AdminLoginActivity /></L>} />
          <Route path="users" element={<L><AdminUsersManagement /></L>} />
          <Route path="security-reports" element={<L><AdminSecurityReports /></L>} />
          <Route path="security-reports/:report_id" element={<L><AdminSecurityReportDetail /></L>} />
          <Route path="referrals" element={<L><AdminReferrals /></L>} />
          <Route path="self-healing" element={<L><SelfHealingDashboard /></L>} />
          <Route path="ttfd-analytics" element={<L><TTFDDashboard /></L>} />
          <Route path="user-analytics" element={<L><UserAnalyticsDashboard /></L>} />
          <Route path="security" element={<L><AdminSecurityDashboard /></L>} />
          <Route path="bio-templates" element={<L><BioTemplatesAdmin /></L>} />
          <Route path="workers" element={<L><WorkerDashboard /></L>} />
          <Route path="template-analytics" element={<L><TemplateAnalyticsDashboard /></L>} />
          <Route path="audit-logs" element={<L><AdminAuditLogs /></L>} />
          <Route path="leaderboard" element={<L><TemplateLeaderboard /></L>} />
          <Route path="daily-report" element={<L><DailyReportDashboard /></L>} />
          <Route path="account-locks" element={<L><AccountLockManagement /></L>} />
          <Route path="environment-monitor" element={<L><EnvironmentMonitor /></L>} />
          <Route path="user-activity" element={<L><UserActivityDashboard /></L>} />
          <Route path="system-health" element={<L><SystemHealthDashboard /></L>} />
          <Route path="anti-abuse" element={<L><AntiAbuseDashboard /></L>} />
          <Route path="revenue" element={<L><RevenueAnalyticsDashboard /></L>} />
          <Route path="revenue-analytics" element={<L><RevenueAnalyticsDashboard /></L>} />
          <Route path="retention" element={<L><RetentionDashboard /></L>} />
          <Route path="monitoring" element={<L><MonitoringDashboard /></L>} />
          <Route path="ga4-tester" element={<L><GA4EventTester /></L>} />
          <Route path="feedback" element={<L><AdminFeedbackPage /></L>} />
          <Route path="growth" element={<L><GrowthDashboard /></L>} />
          <Route path="production-metrics" element={<L><ProductionMetrics /></L>} />
          <Route path="media-security" element={<L><MediaSecurityDashboard /></L>} />
          <Route path="content-engine" element={<L><ContentEngine /></L>} />
          <Route path="payments" element={<L><PaymentsDashboard /></L>} />
          <Route path="conversion" element={<L><ConversionDashboard /></L>} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to={isAuthenticated ? "/app" : "/"} replace />} />
      </Routes>
      </Suspense>

      <ResponsiveSupportWrapper />
      {isAuthenticated && <GuideAssistant />}
      {isAuthenticated && <FirstActionOverlay />}
      {isAuthenticated && <PostValueOverlay onTriggerPaywall={triggerPaywall} />}
      <UpgradeModal open={paywallOpen} onClose={() => setPaywallOpen(false)} reason={paywallReason} triggerSource="app" />
      <CookieConsent />
    </ContentProtectionWrapper>
    {isAuthenticated && <PushPrompt />}
    </ProductGuideProvider>
    </FeedbackProvider>
    </TourProvider>
    </MediaEntitlementProvider>
    </CreditProvider>
    </NotificationProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
