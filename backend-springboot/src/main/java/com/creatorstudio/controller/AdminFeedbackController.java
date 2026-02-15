package com.creatorstudio.controller;

import com.creatorstudio.entity.Feedback;
import com.creatorstudio.repository.FeedbackRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin/feedback")
@PreAuthorize("hasRole('ADMIN')")
public class AdminFeedbackController {

    private static final Logger logger = LoggerFactory.getLogger(AdminFeedbackController.class);

    @Autowired
    private FeedbackRepository feedbackRepository;

    /**
     * Get all feedback for admin dashboard
     */
    @GetMapping("/all")
    public ResponseEntity<Map<String, Object>> getAllFeedback() {
        try {
            List<Feedback> allFeedback = feedbackRepository.findAllByOrderByCreatedAtDesc();
            
            // Calculate stats
            long total = allFeedback.size();
            double avgRating = allFeedback.stream()
                .filter(f -> f.getRating() != null && f.getRating() > 0)
                .mapToInt(Feedback::getRating)
                .average()
                .orElse(0.0);
            
            Map<String, Long> byCategory = allFeedback.stream()
                .filter(f -> f.getType() != null)
                .collect(Collectors.groupingBy(
                    f -> f.getType().name(),
                    Collectors.counting()
                ));

            // Convert feedback to response format
            List<Map<String, Object>> feedbackList = allFeedback.stream()
                .map(f -> {
                    Map<String, Object> item = new HashMap<>();
                    item.put("id", f.getId());
                    item.put("name", f.getName());
                    item.put("email", f.getEmail());
                    item.put("type", f.getType() != null ? f.getType().name() : "GENERAL");
                    item.put("rating", f.getRating());
                    item.put("message", f.getMessage());
                    item.put("createdAt", f.getCreatedAt() != null ? f.getCreatedAt().toString() : null);
                    item.put("allowPublic", f.getAllowPublic());
                    return item;
                })
                .collect(Collectors.toList());

            Map<String, Object> stats = new HashMap<>();
            stats.put("total", total);
            stats.put("averageRating", Math.round(avgRating * 10) / 10.0);
            stats.put("byCategory", byCategory);

            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("feedback", feedbackList);
            response.put("stats", stats);

            logger.info("Admin fetched {} feedback entries", total);
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            logger.error("Error fetching feedback: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to fetch feedback"
            ));
        }
    }

    /**
     * Delete a feedback entry
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteFeedback(@PathVariable UUID id) {
        try {
            feedbackRepository.deleteById(id);
            logger.info("Deleted feedback with id: {}", id);
            return ResponseEntity.ok(Map.of("success", true, "message", "Feedback deleted"));
        } catch (Exception e) {
            logger.error("Error deleting feedback: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to delete feedback"
            ));
        }
    }
}
