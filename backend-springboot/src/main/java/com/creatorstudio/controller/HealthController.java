package com.creatorstudio.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Health check endpoints for service monitoring and load balancing
 */
@RestController
@RequestMapping("/api/health")
public class HealthController {

    private static final Logger logger = LoggerFactory.getLogger(HealthController.class);

    @Autowired
    private DataSource dataSource;

    @Autowired(required = false)
    private RedisTemplate<String, Object> redisTemplate;

    /**
     * Basic health check - for load balancer
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "UP");
        health.put("timestamp", LocalDateTime.now().toString());
        health.put("service", "CreatorStudio API");
        return ResponseEntity.ok(health);
    }

    /**
     * Detailed health check with all dependencies
     */
    @GetMapping("/detailed")
    public ResponseEntity<Map<String, Object>> detailedHealthCheck() {
        Map<String, Object> health = new HashMap<>();
        health.put("timestamp", LocalDateTime.now().toString());
        health.put("service", "CreatorStudio API");
        
        boolean allHealthy = true;
        Map<String, Object> components = new HashMap<>();

        // Check Database
        try {
            Connection conn = dataSource.getConnection();
            conn.isValid(5);
            conn.close();
            components.put("database", Map.of("status", "UP", "type", "PostgreSQL"));
        } catch (Exception e) {
            components.put("database", Map.of("status", "DOWN", "error", e.getMessage()));
            allHealthy = false;
        }

        // Check Redis
        try {
            if (redisTemplate != null) {
                redisTemplate.getConnectionFactory().getConnection().ping();
                components.put("redis", Map.of("status", "UP", "type", "Redis"));
            } else {
                components.put("redis", Map.of("status", "DISABLED"));
            }
        } catch (Exception e) {
            components.put("redis", Map.of("status", "DOWN", "error", e.getMessage()));
            // Redis is optional, don't mark as unhealthy
        }

        // Check Memory
        Runtime runtime = Runtime.getRuntime();
        long maxMemory = runtime.maxMemory();
        long totalMemory = runtime.totalMemory();
        long freeMemory = runtime.freeMemory();
        long usedMemory = totalMemory - freeMemory;
        double memoryUsagePercent = (usedMemory * 100.0) / maxMemory;
        
        components.put("memory", Map.of(
            "status", memoryUsagePercent < 90 ? "UP" : "WARNING",
            "used", formatBytes(usedMemory),
            "max", formatBytes(maxMemory),
            "usagePercent", String.format("%.1f%%", memoryUsagePercent)
        ));

        // Overall status
        health.put("status", allHealthy ? "UP" : "DEGRADED");
        health.put("components", components);

        return allHealthy ? ResponseEntity.ok(health) : ResponseEntity.status(503).body(health);
    }

    /**
     * Liveness probe - is the service alive?
     */
    @GetMapping("/live")
    public ResponseEntity<Map<String, Object>> liveness() {
        return ResponseEntity.ok(Map.of(
            "status", "UP",
            "timestamp", LocalDateTime.now().toString()
        ));
    }

    /**
     * Readiness probe - is the service ready to accept traffic?
     */
    @GetMapping("/ready")
    public ResponseEntity<Map<String, Object>> readiness() {
        try {
            // Check database connection
            Connection conn = dataSource.getConnection();
            boolean valid = conn.isValid(3);
            conn.close();
            
            if (valid) {
                return ResponseEntity.ok(Map.of(
                    "status", "UP",
                    "timestamp", LocalDateTime.now().toString()
                ));
            }
        } catch (Exception e) {
            logger.error("Readiness check failed: {}", e.getMessage());
        }
        
        return ResponseEntity.status(503).body(Map.of(
            "status", "DOWN",
            "timestamp", LocalDateTime.now().toString()
        ));
    }

    private String formatBytes(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        if (bytes < 1024 * 1024 * 1024) return String.format("%.1f MB", bytes / (1024.0 * 1024));
        return String.format("%.1f GB", bytes / (1024.0 * 1024 * 1024));
    }
}
