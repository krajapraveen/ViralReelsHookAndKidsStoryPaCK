package com.creatorstudio.controller;

import com.creatorstudio.service.AnalyticsService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin/analytics")
public class AdminAnalyticsController {

    private static final Logger logger = LoggerFactory.getLogger(AdminAnalyticsController.class);

    @Autowired
    private AnalyticsService analyticsService;

    /**
     * Get comprehensive dashboard analytics
     * @param days Number of days to look back (default 30)
     */
    @GetMapping("/dashboard")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getDashboardAnalytics(
            @RequestParam(defaultValue = "30") int days) {
        
        logger.info("Admin requesting dashboard analytics for {} days", days);
        
        try {
            Map<String, Object> analytics = analyticsService.getDashboardAnalytics(days);
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("period", days + " days");
            response.put("generatedAt", LocalDateTime.now().toString());
            response.put("data", analytics);
            
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("Error fetching analytics: {}", e.getMessage(), e);
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", "Failed to fetch analytics");
            error.put("message", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    /**
     * Track page visit (called from frontend)
     */
    @PostMapping("/track/pageview")
    public ResponseEntity<Map<String, Object>> trackPageView(
            @RequestBody Map<String, String> request,
            @RequestHeader(value = "X-Session-Id", required = false) String sessionId,
            @RequestHeader(value = "User-Agent", required = false) String userAgent,
            @RequestHeader(value = "X-Forwarded-For", required = false) String ipAddress,
            @RequestHeader(value = "Referer", required = false) String referrer,
            @AuthenticationPrincipal UserDetails userDetails) {
        
        try {
            String page = request.get("page");
            UUID userId = null;
            
            if (userDetails != null) {
                // Get user ID from auth context if needed
            }
            
            if (sessionId == null) {
                sessionId = UUID.randomUUID().toString();
            }
            
            analyticsService.trackPageVisit(page, userId, sessionId, userAgent, ipAddress, referrer);
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("sessionId", sessionId);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("Error tracking page view: {}", e.getMessage());
            return ResponseEntity.ok(Map.of("success", false));
        }
    }

    /**
     * Track feature usage (called from frontend)
     */
    @PostMapping("/track/feature")
    public ResponseEntity<Map<String, Object>> trackFeatureUsage(
            @RequestBody Map<String, String> request,
            @AuthenticationPrincipal UserDetails userDetails) {
        
        try {
            String feature = request.get("feature");
            String action = request.get("action");
            String metadata = request.get("metadata");
            UUID userId = null;
            
            if (userDetails != null) {
                // Get user ID from auth context if needed
            }
            
            analyticsService.trackFeatureUsage(feature, action, userId, metadata);
            
            return ResponseEntity.ok(Map.of("success", true));
        } catch (Exception e) {
            logger.error("Error tracking feature usage: {}", e.getMessage());
            return ResponseEntity.ok(Map.of("success", false));
        }
    }

    /**
     * Get visitor statistics
     */
    @GetMapping("/visitors")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getVisitorStats(
            @RequestParam(defaultValue = "30") int days) {
        
        try {
            Map<String, Object> analytics = analyticsService.getDashboardAnalytics(days);
            Map<String, Object> visitors = (Map<String, Object>) analytics.get("visitors");
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", visitors);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("Error fetching visitor stats: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Get payment/transaction statistics
     */
    @GetMapping("/payments")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getPaymentStats(
            @RequestParam(defaultValue = "30") int days) {
        
        try {
            Map<String, Object> analytics = analyticsService.getDashboardAnalytics(days);
            Map<String, Object> payments = (Map<String, Object>) analytics.get("payments");
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", payments);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("Error fetching payment stats: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Get user satisfaction metrics
     */
    @GetMapping("/satisfaction")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getSatisfactionMetrics() {
        
        try {
            Map<String, Object> analytics = analyticsService.getDashboardAnalytics(30);
            Map<String, Object> satisfaction = (Map<String, Object>) analytics.get("satisfaction");
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", satisfaction);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("Error fetching satisfaction metrics: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }
}
