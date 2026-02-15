package com.creatorstudio.controller;

import com.creatorstudio.security.SecurityMonitoringService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * Security Dashboard Controller
 * Admin-only endpoints for security monitoring
 */
@RestController
@RequestMapping("/api/admin/security")
@PreAuthorize("hasRole('ADMIN')")
public class SecurityDashboardController {

    @Autowired
    private SecurityMonitoringService securityService;

    /**
     * Get security statistics
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getSecurityStats() {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("stats", securityService.getSecurityStats());
        return ResponseEntity.ok(response);
    }

    /**
     * Get recent attack attempts
     */
    @GetMapping("/attacks")
    public ResponseEntity<Map<String, Object>> getRecentAttacks(
            @RequestParam(defaultValue = "50") int limit) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("attacks", securityService.getRecentAttacks(limit));
        return ResponseEntity.ok(response);
    }

    /**
     * Get security overview
     */
    @GetMapping("/overview")
    public ResponseEntity<Map<String, Object>> getSecurityOverview() {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("stats", securityService.getSecurityStats());
        response.put("recentAttacks", securityService.getRecentAttacks(10));
        response.put("protectionActive", true);
        response.put("features", Map.of(
            "waf", "Active - Blocking SQL injection, XSS, path traversal",
            "rateLimiting", "Active - 50 req/sec per IP, login: 5 attempts/min",
            "bruteForceProtection", "Active - Auto-blocks after threshold",
            "inputSanitization", "Active - All user inputs sanitized",
            "securityHeaders", "Active - CSP, X-Frame-Options, etc."
        ));
        return ResponseEntity.ok(response);
    }
}
