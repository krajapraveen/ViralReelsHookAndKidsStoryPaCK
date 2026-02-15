package com.creatorstudio.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Security Monitoring Service
 * Tracks and reports security events
 */
@Service
public class SecurityMonitoringService {

    private static final Logger logger = LoggerFactory.getLogger(SecurityMonitoringService.class);
    private static final Logger securityLogger = LoggerFactory.getLogger("SECURITY_AUDIT");

    // Attack counters
    private final AtomicLong sqlInjectionAttempts = new AtomicLong(0);
    private final AtomicLong xssAttempts = new AtomicLong(0);
    private final AtomicLong pathTraversalAttempts = new AtomicLong(0);
    private final AtomicLong bruteForceAttempts = new AtomicLong(0);
    private final AtomicLong blockedRequests = new AtomicLong(0);
    private final AtomicLong rateLimitedRequests = new AtomicLong(0);

    // Recent attack sources
    private final ConcurrentHashMap<String, List<SecurityEvent>> recentEvents = new ConcurrentHashMap<>();
    
    // Blocked IPs
    private final Set<String> permanentlyBlockedIPs = ConcurrentHashMap.newKeySet();

    public void recordSQLInjectionAttempt(String ip, String payload) {
        sqlInjectionAttempts.incrementAndGet();
        recordEvent(ip, "SQL_INJECTION", payload);
        securityLogger.warn("SQL_INJECTION attempt from {} - Payload: {}", ip, truncate(payload, 100));
        checkForPermanentBlock(ip);
    }

    public void recordXSSAttempt(String ip, String payload) {
        xssAttempts.incrementAndGet();
        recordEvent(ip, "XSS", payload);
        securityLogger.warn("XSS attempt from {} - Payload: {}", ip, truncate(payload, 100));
        checkForPermanentBlock(ip);
    }

    public void recordPathTraversalAttempt(String ip, String path) {
        pathTraversalAttempts.incrementAndGet();
        recordEvent(ip, "PATH_TRAVERSAL", path);
        securityLogger.warn("PATH_TRAVERSAL attempt from {} - Path: {}", ip, path);
        checkForPermanentBlock(ip);
    }

    public void recordBruteForceAttempt(String ip, String endpoint) {
        bruteForceAttempts.incrementAndGet();
        recordEvent(ip, "BRUTE_FORCE", endpoint);
        securityLogger.warn("BRUTE_FORCE attempt from {} - Endpoint: {}", ip, endpoint);
        checkForPermanentBlock(ip);
    }

    public void recordBlockedRequest(String ip, String reason) {
        blockedRequests.incrementAndGet();
        recordEvent(ip, "BLOCKED", reason);
    }

    public void recordRateLimitedRequest(String ip) {
        rateLimitedRequests.incrementAndGet();
        recordEvent(ip, "RATE_LIMITED", "Request rate exceeded");
    }

    private void recordEvent(String ip, String type, String details) {
        SecurityEvent event = new SecurityEvent(type, details, LocalDateTime.now());
        recentEvents.computeIfAbsent(ip, k -> Collections.synchronizedList(new ArrayList<>())).add(event);
        
        // Keep only last 100 events per IP
        List<SecurityEvent> events = recentEvents.get(ip);
        while (events.size() > 100) {
            events.remove(0);
        }
    }

    private void checkForPermanentBlock(String ip) {
        List<SecurityEvent> events = recentEvents.get(ip);
        if (events != null && events.size() >= 10) {
            // Count recent attack events
            long attackCount = events.stream()
                .filter(e -> System.currentTimeMillis() - e.timestamp.toEpochSecond(java.time.ZoneOffset.UTC) * 1000 < 3600000)
                .filter(e -> !e.type.equals("RATE_LIMITED"))
                .count();
            
            if (attackCount >= 5) {
                permanentlyBlockedIPs.add(ip);
                securityLogger.error("IP {} PERMANENTLY BLOCKED - Multiple attack attempts detected", ip);
            }
        }
    }

    public boolean isPermanentlyBlocked(String ip) {
        return permanentlyBlockedIPs.contains(ip);
    }

    /**
     * Get security statistics
     */
    public Map<String, Object> getSecurityStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("sqlInjectionAttempts", sqlInjectionAttempts.get());
        stats.put("xssAttempts", xssAttempts.get());
        stats.put("pathTraversalAttempts", pathTraversalAttempts.get());
        stats.put("bruteForceAttempts", bruteForceAttempts.get());
        stats.put("blockedRequests", blockedRequests.get());
        stats.put("rateLimitedRequests", rateLimitedRequests.get());
        stats.put("permanentlyBlockedIPs", permanentlyBlockedIPs.size());
        stats.put("activeAttackSources", recentEvents.size());
        stats.put("timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_DATE_TIME));
        return stats;
    }

    /**
     * Get recent attack events
     */
    public List<Map<String, Object>> getRecentAttacks(int limit) {
        List<Map<String, Object>> attacks = new ArrayList<>();
        
        recentEvents.forEach((ip, events) -> {
            for (SecurityEvent event : events) {
                if (!event.type.equals("RATE_LIMITED")) {
                    Map<String, Object> attack = new HashMap<>();
                    attack.put("ip", ip);
                    attack.put("type", event.type);
                    attack.put("details", truncate(event.details, 50));
                    attack.put("timestamp", event.timestamp.format(DateTimeFormatter.ISO_DATE_TIME));
                    attacks.add(attack);
                }
            }
        });
        
        // Sort by timestamp descending
        attacks.sort((a, b) -> ((String) b.get("timestamp")).compareTo((String) a.get("timestamp")));
        
        return attacks.subList(0, Math.min(limit, attacks.size()));
    }

    /**
     * Periodic security report
     */
    @Scheduled(fixedRate = 3600000) // Every hour
    public void generateSecurityReport() {
        Map<String, Object> stats = getSecurityStats();
        
        long totalAttempts = (Long) stats.get("sqlInjectionAttempts") +
                            (Long) stats.get("xssAttempts") +
                            (Long) stats.get("pathTraversalAttempts") +
                            (Long) stats.get("bruteForceAttempts");
        
        if (totalAttempts > 0) {
            logger.info("=== SECURITY REPORT ===");
            logger.info("SQL Injection attempts: {}", stats.get("sqlInjectionAttempts"));
            logger.info("XSS attempts: {}", stats.get("xssAttempts"));
            logger.info("Path Traversal attempts: {}", stats.get("pathTraversalAttempts"));
            logger.info("Brute Force attempts: {}", stats.get("bruteForceAttempts"));
            logger.info("Total blocked requests: {}", stats.get("blockedRequests"));
            logger.info("Permanently blocked IPs: {}", stats.get("permanentlyBlockedIPs"));
            logger.info("=======================");
        }
    }

    private String truncate(String str, int maxLength) {
        if (str == null) return "";
        return str.length() > maxLength ? str.substring(0, maxLength) + "..." : str;
    }

    private static class SecurityEvent {
        final String type;
        final String details;
        final LocalDateTime timestamp;

        SecurityEvent(String type, String details, LocalDateTime timestamp) {
            this.type = type;
            this.details = details;
            this.timestamp = timestamp;
        }
    }
}
