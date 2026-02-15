package com.creatorstudio.controller;

import com.creatorstudio.entity.FeatureRequest;
import com.creatorstudio.entity.User;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.FeatureRequestService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/feature-requests")
public class FeatureRequestController {

    private static final Logger logger = LoggerFactory.getLogger(FeatureRequestController.class);

    @Autowired
    private FeatureRequestService featureRequestService;

    @Autowired
    private AuthService authService;

    /**
     * Create a new feature request
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> createFeatureRequest(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody Map<String, String> request) {
        
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            
            String title = request.get("title");
            String description = request.get("description");
            String category = request.get("category");
            
            if (title == null || title.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "error", "Title is required"
                ));
            }
            
            if (description == null || description.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "error", "Description is required"
                ));
            }
            
            if (category == null || category.trim().isEmpty()) {
                category = "OTHER";
            }
            
            FeatureRequest created = featureRequestService.createFeatureRequest(
                user.getId(), title, description, category
            );
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "Feature request submitted successfully");
            response.put("featureRequest", mapFeatureRequest(created, user.getId()));
            
            return ResponseEntity.ok(response);
            
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of(
                "success", false,
                "error", "Invalid category. Valid options: AI_GENERATION, UI_UX, PAYMENTS, INTEGRATIONS, EXPORT_OPTIONS, ANALYTICS, COLLABORATION, MOBILE_APP, OTHER"
            ));
        } catch (Exception e) {
            logger.error("Error creating feature request: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Vote for a feature request
     */
    @PostMapping("/{id}/vote")
    public ResponseEntity<Map<String, Object>> voteForFeature(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable UUID id) {
        
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            Map<String, Object> result = featureRequestService.voteForFeature(user.getId(), id);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("Error voting for feature: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Remove vote from a feature request
     */
    @DeleteMapping("/{id}/vote")
    public ResponseEntity<Map<String, Object>> removeVote(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable UUID id) {
        
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            Map<String, Object> result = featureRequestService.removeVote(user.getId(), id);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("Error removing vote: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Get all feature requests
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getAllFeatureRequests(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            Page<FeatureRequest> requests = featureRequestService.getAllFeatureRequests(
                PageRequest.of(page, size)
            );
            
            List<Map<String, Object>> requestList = new ArrayList<>();
            for (FeatureRequest fr : requests.getContent()) {
                requestList.add(mapFeatureRequest(fr, user.getId()));
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("content", requestList);
            response.put("totalPages", requests.getTotalPages());
            response.put("totalElements", requests.getTotalElements());
            response.put("currentPage", page);
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            logger.error("Error fetching feature requests: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Get top feature requests (public - for display)
     */
    @GetMapping("/top")
    public ResponseEntity<Map<String, Object>> getTopFeatureRequests(
            @AuthenticationPrincipal UserDetails userDetails) {
        
        try {
            UUID userId = null;
            if (userDetails != null) {
                User user = authService.getUserByEmail(userDetails.getUsername());
                userId = user.getId();
            }
            
            List<FeatureRequest> topRequests = featureRequestService.getTopFeatureRequests();
            
            List<Map<String, Object>> requestList = new ArrayList<>();
            for (FeatureRequest fr : topRequests) {
                requestList.add(mapFeatureRequest(fr, userId));
            }
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "requests", requestList
            ));
            
        } catch (Exception e) {
            logger.error("Error fetching top feature requests: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Get user's feature requests
     */
    @GetMapping("/my")
    public ResponseEntity<Map<String, Object>> getMyFeatureRequests(
            @AuthenticationPrincipal UserDetails userDetails) {
        
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            List<FeatureRequest> requests = featureRequestService.getUserFeatureRequests(user.getId());
            
            List<Map<String, Object>> requestList = new ArrayList<>();
            for (FeatureRequest fr : requests) {
                requestList.add(mapFeatureRequest(fr, user.getId()));
            }
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "requests", requestList
            ));
            
        } catch (Exception e) {
            logger.error("Error fetching user's feature requests: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Get available categories
     */
    @GetMapping("/categories")
    public ResponseEntity<Map<String, Object>> getCategories() {
        List<Map<String, String>> categories = new ArrayList<>();
        for (FeatureRequest.Category cat : FeatureRequest.Category.values()) {
            Map<String, String> item = new HashMap<>();
            item.put("value", cat.name());
            item.put("label", formatCategoryLabel(cat.name()));
            categories.add(item);
        }
        return ResponseEntity.ok(Map.of(
            "success", true,
            "categories", categories
        ));
    }

    /**
     * Admin: Update feature request status
     */
    @PutMapping("/{id}/status")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> updateStatus(
            @PathVariable UUID id,
            @RequestBody Map<String, String> request) {
        
        try {
            String status = request.get("status");
            String adminResponse = request.get("adminResponse");
            
            FeatureRequest updated = featureRequestService.updateStatus(id, status, adminResponse);
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Status updated successfully",
                "featureRequest", mapFeatureRequest(updated, null)
            ));
            
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of(
                "success", false,
                "error", "Invalid status. Valid options: PENDING, UNDER_REVIEW, PLANNED, IN_PROGRESS, COMPLETED, DECLINED"
            ));
        } catch (Exception e) {
            logger.error("Error updating feature request status: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Admin: Get feature request analytics
     */
    @GetMapping("/analytics")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getAnalytics() {
        try {
            Map<String, Object> analytics = featureRequestService.getFeatureRequestAnalytics();
            return ResponseEntity.ok(Map.of(
                "success", true,
                "data", analytics
            ));
        } catch (Exception e) {
            logger.error("Error fetching feature request analytics: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", e.getMessage()
            ));
        }
    }

    // Helper methods
    private Map<String, Object> mapFeatureRequest(FeatureRequest fr, UUID currentUserId) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", fr.getId().toString());
        map.put("title", fr.getTitle());
        map.put("description", fr.getDescription());
        map.put("category", fr.getCategory().name());
        map.put("categoryLabel", formatCategoryLabel(fr.getCategory().name()));
        map.put("status", fr.getStatus().name());
        map.put("statusLabel", formatStatusLabel(fr.getStatus().name()));
        map.put("voteCount", fr.getVoteCount());
        map.put("createdAt", fr.getCreatedAt().toString());
        map.put("adminResponse", fr.getAdminResponse());
        
        if (fr.getUser() != null) {
            map.put("authorName", fr.getUser().getName());
            map.put("isOwner", currentUserId != null && fr.getUser().getId().equals(currentUserId));
        }
        
        if (currentUserId != null) {
            map.put("hasVoted", featureRequestService.hasUserVoted(currentUserId, fr.getId()));
        }
        
        return map;
    }

    private String formatCategoryLabel(String category) {
        return category.replace("_", " ").toLowerCase()
            .replaceFirst(".", String.valueOf(Character.toUpperCase(category.charAt(0))));
    }

    private String formatStatusLabel(String status) {
        return status.replace("_", " ").toLowerCase()
            .replaceFirst(".", String.valueOf(Character.toUpperCase(status.charAt(0))));
    }
}
