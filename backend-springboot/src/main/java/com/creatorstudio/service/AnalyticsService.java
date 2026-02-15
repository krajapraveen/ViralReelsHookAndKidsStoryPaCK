package com.creatorstudio.service;

import com.creatorstudio.entity.*;
import com.creatorstudio.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class AnalyticsService {

    private static final Logger logger = LoggerFactory.getLogger(AnalyticsService.class);

    @Autowired
    private PageVisitRepository pageVisitRepository;

    @Autowired
    private FeatureUsageRepository featureUsageRepository;

    @Autowired
    private UserSessionRepository userSessionRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PaymentRepository paymentRepository;

    @Autowired
    private GenerationRepository generationRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private ReviewRepository reviewRepository;

    @Autowired
    private FeedbackRepository feedbackRepository;

    // ==================== Tracking Methods ====================

    @Transactional
    public void trackPageVisit(String page, UUID userId, String sessionId, String userAgent, String ipAddress, String referrer) {
        try {
            PageVisit visit = new PageVisit();
            visit.setPage(page);
            visit.setUserId(userId);
            visit.setSessionId(sessionId);
            visit.setUserAgent(userAgent);
            visit.setIpAddress(maskIpAddress(ipAddress));
            visit.setReferrer(referrer);
            pageVisitRepository.save(visit);
        } catch (Exception e) {
            logger.error("Failed to track page visit: {}", e.getMessage());
        }
    }

    @Transactional
    public void trackFeatureUsage(String feature, String action, UUID userId, String metadata) {
        try {
            FeatureUsage usage = new FeatureUsage();
            usage.setFeature(feature);
            usage.setAction(action);
            usage.setUserId(userId);
            usage.setMetadata(metadata);
            featureUsageRepository.save(usage);
        } catch (Exception e) {
            logger.error("Failed to track feature usage: {}", e.getMessage());
        }
    }

    @Transactional
    public void trackSession(String sessionId, UUID userId, String userAgent, String ipAddress) {
        try {
            UserSession session = userSessionRepository.findBySessionId(sessionId)
                    .orElseGet(() -> {
                        UserSession newSession = new UserSession();
                        newSession.setSessionId(sessionId);
                        return newSession;
                    });
            
            session.setUserId(userId);
            session.setUserAgent(userAgent);
            session.setIpAddress(maskIpAddress(ipAddress));
            session.setDeviceType(detectDeviceType(userAgent));
            session.setBrowser(detectBrowser(userAgent));
            session.setOs(detectOS(userAgent));
            session.setIsActive(true);
            userSessionRepository.save(session);
        } catch (Exception e) {
            logger.error("Failed to track session: {}", e.getMessage());
        }
    }

    // ==================== Analytics Dashboard Data ====================

    public Map<String, Object> getDashboardAnalytics(int days) {
        LocalDateTime startDate = LocalDateTime.now().minusDays(days);
        Map<String, Object> analytics = new LinkedHashMap<>();

        // Overview Stats
        analytics.put("overview", getOverviewStats(startDate));
        
        // Visitor Analytics
        analytics.put("visitors", getVisitorAnalytics(startDate));
        
        // Feature Usage
        analytics.put("featureUsage", getFeatureUsageAnalytics(startDate));
        
        // Subscription & Payment Analytics
        analytics.put("payments", getPaymentAnalytics(startDate));
        
        // User Satisfaction
        analytics.put("satisfaction", getSatisfactionAnalytics());
        
        // Generation Stats
        analytics.put("generations", getGenerationAnalytics(startDate));
        
        // Recent Activity
        analytics.put("recentActivity", getRecentActivity());

        return analytics;
    }

    private Map<String, Object> getOverviewStats(LocalDateTime startDate) {
        Map<String, Object> stats = new LinkedHashMap<>();
        
        // Total Users
        long totalUsers = userRepository.count();
        stats.put("totalUsers", totalUsers);
        
        // New Users (in period)
        long newUsers = userRepository.countByCreatedAtAfter(startDate);
        stats.put("newUsers", newUsers);
        
        // Active Sessions
        Long activeSessions = userSessionRepository.countActiveSessions();
        stats.put("activeSessions", activeSessions != null ? activeSessions : 0);
        
        // Total Revenue
        BigDecimal totalRevenue = paymentRepository.sumTotalRevenue();
        stats.put("totalRevenue", totalRevenue != null ? totalRevenue : BigDecimal.ZERO);
        
        // Revenue in Period
        BigDecimal periodRevenue = paymentRepository.sumRevenueSince(startDate);
        stats.put("periodRevenue", periodRevenue != null ? periodRevenue : BigDecimal.ZERO);
        
        // Total Generations
        long totalGenerations = generationRepository.count();
        stats.put("totalGenerations", totalGenerations);
        
        return stats;
    }

    private Map<String, Object> getVisitorAnalytics(LocalDateTime startDate) {
        Map<String, Object> visitors = new LinkedHashMap<>();
        
        // Unique Visitors
        Long uniqueVisitors = pageVisitRepository.countUniqueVisitorsSince(startDate);
        visitors.put("uniqueVisitors", uniqueVisitors != null ? uniqueVisitors : 0);
        
        // Total Page Views
        Long totalPageViews = pageVisitRepository.countTotalPageViewsSince(startDate);
        visitors.put("totalPageViews", totalPageViews != null ? totalPageViews : 0);
        
        // Anonymous vs Logged In
        Long anonymousVisitors = pageVisitRepository.countAnonymousVisitorsSince(startDate);
        Long loggedInVisitors = pageVisitRepository.countLoggedInVisitorsSince(startDate);
        visitors.put("anonymousVisitors", anonymousVisitors != null ? anonymousVisitors : 0);
        visitors.put("loggedInVisitors", loggedInVisitors != null ? loggedInVisitors : 0);
        
        // Page Views by Page
        List<Object[]> pageViews = pageVisitRepository.getPageViewCountsSince(startDate);
        List<Map<String, Object>> pageViewsList = new ArrayList<>();
        for (Object[] row : pageViews) {
            Map<String, Object> item = new HashMap<>();
            item.put("page", row[0]);
            item.put("views", row[1]);
            pageViewsList.add(item);
        }
        visitors.put("pageViews", pageViewsList);
        
        // Daily Visitors Trend
        List<Object[]> dailyVisitors = pageVisitRepository.getDailyVisitorsSince(startDate);
        List<Map<String, Object>> dailyTrend = new ArrayList<>();
        for (Object[] row : dailyVisitors) {
            Map<String, Object> item = new HashMap<>();
            item.put("date", row[0].toString());
            item.put("visitors", row[1]);
            dailyTrend.add(item);
        }
        visitors.put("dailyTrend", dailyTrend);
        
        // Device Distribution
        List<Object[]> deviceDist = userSessionRepository.getDeviceTypeDistributionSince(startDate);
        Map<String, Long> devices = new HashMap<>();
        for (Object[] row : deviceDist) {
            devices.put(row[0] != null ? row[0].toString() : "Unknown", (Long) row[1]);
        }
        visitors.put("deviceDistribution", devices);
        
        // Browser Distribution
        List<Object[]> browserDist = userSessionRepository.getBrowserDistributionSince(startDate);
        Map<String, Long> browsers = new HashMap<>();
        for (Object[] row : browserDist) {
            browsers.put(row[0] != null ? row[0].toString() : "Unknown", (Long) row[1]);
        }
        visitors.put("browserDistribution", browsers);
        
        return visitors;
    }

    private Map<String, Object> getFeatureUsageAnalytics(LocalDateTime startDate) {
        Map<String, Object> features = new LinkedHashMap<>();
        
        // Feature Usage Counts
        List<Object[]> usageCounts = featureUsageRepository.getFeatureUsageCountsSince(startDate);
        List<Map<String, Object>> featureList = new ArrayList<>();
        long totalUsage = 0;
        for (Object[] row : usageCounts) {
            Map<String, Object> item = new HashMap<>();
            item.put("feature", row[0]);
            item.put("count", row[1]);
            featureList.add(item);
            totalUsage += (Long) row[1];
        }
        features.put("usageCounts", featureList);
        features.put("totalUsage", totalUsage);
        
        // Most Popular Features (Top 5)
        features.put("topFeatures", featureList.stream().limit(5).collect(Collectors.toList()));
        
        // Feature Usage Percentage
        List<Map<String, Object>> featurePercentages = new ArrayList<>();
        for (Object[] row : usageCounts) {
            Map<String, Object> item = new HashMap<>();
            item.put("feature", row[0]);
            long count = (Long) row[1];
            double percentage = totalUsage > 0 ? (count * 100.0 / totalUsage) : 0;
            item.put("percentage", Math.round(percentage * 100.0) / 100.0);
            featurePercentages.add(item);
        }
        features.put("featurePercentages", featurePercentages);
        
        // Unique Users per Feature
        List<Object[]> uniqueUsers = featureUsageRepository.getFeatureUniqueUsersSince(startDate);
        List<Map<String, Object>> uniqueUsersList = new ArrayList<>();
        for (Object[] row : uniqueUsers) {
            Map<String, Object> item = new HashMap<>();
            item.put("feature", row[0]);
            item.put("uniqueUsers", row[1]);
            uniqueUsersList.add(item);
        }
        features.put("uniqueUsersPerFeature", uniqueUsersList);
        
        return features;
    }

    private Map<String, Object> getPaymentAnalytics(LocalDateTime startDate) {
        Map<String, Object> payments = new LinkedHashMap<>();
        
        // Transaction Summary
        long totalTransactions = paymentRepository.countByCreatedAtAfter(startDate);
        long successfulTransactions = paymentRepository.countByStatusAndCreatedAtAfter(Payment.Status.PAID, startDate);
        long failedTransactions = paymentRepository.countByStatusAndCreatedAtAfter(Payment.Status.FAILED, startDate);
        long pendingTransactions = paymentRepository.countByStatusAndCreatedAtAfter(Payment.Status.CREATED, startDate);
        
        payments.put("totalTransactions", totalTransactions);
        payments.put("successfulTransactions", successfulTransactions);
        payments.put("failedTransactions", failedTransactions);
        payments.put("pendingTransactions", pendingTransactions);
        
        // Success Rate
        double successRate = totalTransactions > 0 ? (successfulTransactions * 100.0 / totalTransactions) : 0;
        payments.put("successRate", Math.round(successRate * 100.0) / 100.0);
        
        // Subscription Plans Breakdown
        List<Object[]> planBreakdown = paymentRepository.getSubscriptionsByProduct(startDate);
        List<Map<String, Object>> plansList = new ArrayList<>();
        for (Object[] row : planBreakdown) {
            Map<String, Object> item = new HashMap<>();
            item.put("productName", row[0]);
            item.put("count", row[1]);
            item.put("revenue", row[2]);
            plansList.add(item);
        }
        payments.put("planBreakdown", plansList);
        
        // Failed Transactions Reasons
        List<Map<String, Object>> failedReasons = new ArrayList<>();
        // Common failure reasons
        Map<String, Object> signatureFailure = new HashMap<>();
        signatureFailure.put("reason", "Invalid Signature");
        signatureFailure.put("count", paymentRepository.countFailedByReason("signature", startDate));
        failedReasons.add(signatureFailure);
        
        Map<String, Object> cardDeclined = new HashMap<>();
        cardDeclined.put("reason", "Card Declined");
        cardDeclined.put("count", paymentRepository.countFailedByReason("declined", startDate));
        failedReasons.add(cardDeclined);
        
        Map<String, Object> insufficientFunds = new HashMap<>();
        insufficientFunds.put("reason", "Insufficient Funds");
        insufficientFunds.put("count", paymentRepository.countFailedByReason("insufficient", startDate));
        failedReasons.add(insufficientFunds);
        
        Map<String, Object> timeout = new HashMap<>();
        timeout.put("reason", "Payment Timeout");
        timeout.put("count", paymentRepository.countFailedByReason("timeout", startDate));
        failedReasons.add(timeout);
        
        Map<String, Object> other = new HashMap<>();
        other.put("reason", "Other/Abandoned");
        long otherCount = failedTransactions - failedReasons.stream()
                .mapToLong(r -> r.get("count") != null ? (Long) r.get("count") : 0).sum();
        other.put("count", Math.max(0, otherCount));
        failedReasons.add(other);
        
        payments.put("failureReasons", failedReasons);
        
        // Daily Revenue Trend
        List<Object[]> dailyRevenue = paymentRepository.getDailyRevenueSince(startDate);
        List<Map<String, Object>> revenueTrend = new ArrayList<>();
        for (Object[] row : dailyRevenue) {
            Map<String, Object> item = new HashMap<>();
            item.put("date", row[0].toString());
            item.put("revenue", row[1]);
            item.put("count", row[2]);
            revenueTrend.add(item);
        }
        payments.put("dailyRevenueTrend", revenueTrend);
        
        return payments;
    }

    private Map<String, Object> getSatisfactionAnalytics() {
        Map<String, Object> satisfaction = new LinkedHashMap<>();
        
        // Average Rating
        Double avgRating = reviewRepository.getAverageRating();
        satisfaction.put("averageRating", avgRating != null ? Math.round(avgRating * 100.0) / 100.0 : 0);
        
        // Total Reviews
        long totalReviews = reviewRepository.countReviews();
        satisfaction.put("totalReviews", totalReviews);
        
        // Rating Distribution
        List<Object[]> ratingDist = reviewRepository.getRatingDistribution();
        Map<Integer, Long> ratingDistribution = new LinkedHashMap<>();
        for (int i = 5; i >= 1; i--) {
            ratingDistribution.put(i, 0L);
        }
        for (Object[] row : ratingDist) {
            ratingDistribution.put((Integer) row[0], (Long) row[1]);
        }
        satisfaction.put("ratingDistribution", ratingDistribution);
        
        // Satisfaction Percentage (4+ stars)
        long satisfiedCount = ratingDistribution.entrySet().stream()
                .filter(e -> e.getKey() >= 4)
                .mapToLong(Map.Entry::getValue)
                .sum();
        double satisfactionPercentage = totalReviews > 0 ? (satisfiedCount * 100.0 / totalReviews) : 0;
        satisfaction.put("satisfactionPercentage", Math.round(satisfactionPercentage * 100.0) / 100.0);
        
        // Recent Reviews
        List<Feedback> recentReviews = reviewRepository.findTop5ReviewsByOrderByCreatedAtDesc();
        List<Map<String, Object>> recentList = new ArrayList<>();
        for (Feedback review : recentReviews) {
            Map<String, Object> item = new HashMap<>();
            item.put("rating", review.getRating());
            item.put("comment", review.getComment());
            item.put("createdAt", review.getCreatedAt().toString());
            recentList.add(item);
        }
        satisfaction.put("recentReviews", recentList);
        
        // Feedback Count
        long feedbackCount = feedbackRepository.count();
        satisfaction.put("totalFeedback", feedbackCount);
        
        // NPS Score Estimate (based on ratings)
        // Promoters: 5 stars, Passives: 4 stars, Detractors: 1-3 stars
        long promoters = ratingDistribution.get(5);
        long detractors = ratingDistribution.get(1) + ratingDistribution.get(2) + ratingDistribution.get(3);
        double npsScore = totalReviews > 0 ? ((promoters - detractors) * 100.0 / totalReviews) : 0;
        satisfaction.put("npsScore", Math.round(npsScore));
        
        return satisfaction;
    }

    private Map<String, Object> getGenerationAnalytics(LocalDateTime startDate) {
        Map<String, Object> generations = new LinkedHashMap<>();
        
        // Generation by Type
        long reelGenerations = generationRepository.countByTypeAndCreatedAtAfter(Generation.Type.REEL, startDate);
        long storyGenerations = generationRepository.countByTypeAndCreatedAtAfter(Generation.Type.STORY, startDate);
        
        generations.put("reelGenerations", reelGenerations);
        generations.put("storyGenerations", storyGenerations);
        generations.put("totalGenerations", reelGenerations + storyGenerations);
        
        // Success Rate
        long successfulGenerations = generationRepository.countByStatusAndCreatedAtAfter(Generation.Status.SUCCEEDED, startDate);
        long failedGenerations = generationRepository.countByStatusAndCreatedAtAfter(Generation.Status.FAILED, startDate);
        long total = successfulGenerations + failedGenerations;
        double genSuccessRate = total > 0 ? (successfulGenerations * 100.0 / total) : 100;
        generations.put("successRate", Math.round(genSuccessRate * 100.0) / 100.0);
        
        // Credits Used
        BigDecimal creditsUsed = generationRepository.sumCreditsUsedSince(startDate);
        generations.put("creditsUsed", creditsUsed != null ? creditsUsed : BigDecimal.ZERO);
        
        return generations;
    }

    private Map<String, Object> getRecentActivity() {
        Map<String, Object> activity = new LinkedHashMap<>();
        
        // Recent Users
        List<User> recentUsers = userRepository.findTop10ByOrderByCreatedAtDesc();
        List<Map<String, Object>> usersList = new ArrayList<>();
        for (User user : recentUsers) {
            Map<String, Object> item = new HashMap<>();
            item.put("name", user.getName());
            item.put("email", maskEmail(user.getEmail()));
            item.put("createdAt", user.getCreatedAt().toString());
            usersList.add(item);
        }
        activity.put("recentUsers", usersList);
        
        // Recent Payments
        List<Payment> recentPayments = paymentRepository.findTop10ByOrderByCreatedAtDesc();
        List<Map<String, Object>> paymentsList = new ArrayList<>();
        for (Payment payment : recentPayments) {
            Map<String, Object> item = new HashMap<>();
            item.put("amount", payment.getAmountInr());
            item.put("status", payment.getStatus().toString());
            item.put("product", payment.getProduct() != null ? payment.getProduct().getName() : "Unknown");
            item.put("createdAt", payment.getCreatedAt().toString());
            paymentsList.add(item);
        }
        activity.put("recentPayments", paymentsList);
        
        return activity;
    }

    // ==================== Helper Methods ====================

    private String maskIpAddress(String ip) {
        if (ip == null) return null;
        String[] parts = ip.split("\\.");
        if (parts.length == 4) {
            return parts[0] + "." + parts[1] + ".xxx.xxx";
        }
        return ip;
    }

    private String maskEmail(String email) {
        if (email == null) return null;
        int atIndex = email.indexOf('@');
        if (atIndex > 2) {
            return email.substring(0, 2) + "***" + email.substring(atIndex);
        }
        return "***" + email.substring(atIndex);
    }

    private String detectDeviceType(String userAgent) {
        if (userAgent == null) return "Unknown";
        userAgent = userAgent.toLowerCase();
        if (userAgent.contains("mobile") || userAgent.contains("android") || userAgent.contains("iphone")) {
            return "Mobile";
        } else if (userAgent.contains("tablet") || userAgent.contains("ipad")) {
            return "Tablet";
        }
        return "Desktop";
    }

    private String detectBrowser(String userAgent) {
        if (userAgent == null) return "Unknown";
        userAgent = userAgent.toLowerCase();
        if (userAgent.contains("chrome") && !userAgent.contains("edg")) return "Chrome";
        if (userAgent.contains("firefox")) return "Firefox";
        if (userAgent.contains("safari") && !userAgent.contains("chrome")) return "Safari";
        if (userAgent.contains("edg")) return "Edge";
        if (userAgent.contains("opera") || userAgent.contains("opr")) return "Opera";
        return "Other";
    }

    private String detectOS(String userAgent) {
        if (userAgent == null) return "Unknown";
        userAgent = userAgent.toLowerCase();
        if (userAgent.contains("windows")) return "Windows";
        if (userAgent.contains("mac os") || userAgent.contains("macos")) return "macOS";
        if (userAgent.contains("linux")) return "Linux";
        if (userAgent.contains("android")) return "Android";
        if (userAgent.contains("iphone") || userAgent.contains("ipad")) return "iOS";
        return "Other";
    }
}
