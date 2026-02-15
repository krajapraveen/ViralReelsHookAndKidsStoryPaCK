package com.creatorstudio.controller;

import com.creatorstudio.entity.User;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.DataPrivacyService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Controller for GDPR/CCPA data privacy compliance
 */
@RestController
@RequestMapping("/api/privacy")
public class DataPrivacyController {

    private static final Logger logger = LoggerFactory.getLogger(DataPrivacyController.class);

    @Autowired
    private DataPrivacyService privacyService;

    @Autowired
    private AuthService authService;

    /**
     * Get user's personal data (GDPR Article 15 - Right of Access)
     */
    @GetMapping("/my-data")
    public ResponseEntity<Map<String, Object>> getMyData(
            @AuthenticationPrincipal UserDetails userDetails) {
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            Map<String, Object> data = privacyService.exportUserData(user.getId());
            return ResponseEntity.ok(Map.of(
                "success", true,
                "data", data,
                "message", "Your personal data has been retrieved"
            ));
        } catch (Exception e) {
            logger.error("Error exporting user data: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to retrieve data"
            ));
        }
    }

    /**
     * Download user's data as JSON (GDPR Article 20 - Right to Data Portability)
     */
    @GetMapping("/export")
    public ResponseEntity<Map<String, Object>> exportMyData(
            @AuthenticationPrincipal UserDetails userDetails) {
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            Map<String, Object> exportData = privacyService.exportUserDataForDownload(user.getId());
            return ResponseEntity.ok(exportData);
        } catch (Exception e) {
            logger.error("Error exporting user data: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to export data"
            ));
        }
    }

    /**
     * Request account deletion (simplified - no password required from frontend)
     */
    @PostMapping("/delete-request")
    public ResponseEntity<Map<String, Object>> requestAccountDeletionSimple(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody Map<String, String> request) {
        try {
            String reason = request.get("reason");
            
            if (reason == null || reason.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "error", "Please provide a reason for account deletion"
                ));
            }
            
            User user = authService.getUserByEmail(userDetails.getUsername());
            
            // Schedule deletion (30-day grace period)
            privacyService.scheduleAccountDeletion(user.getId(), reason);
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Account scheduled for deletion. You have 30 days to cancel this request."
            ));
        } catch (Exception e) {
            logger.error("Error scheduling account deletion: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to process deletion request"
            ));
        }
    }

    /**
     * Request account deletion (GDPR Article 17 - Right to Erasure)
     */
    @PostMapping("/delete-account")
    public ResponseEntity<Map<String, Object>> requestAccountDeletion(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody Map<String, String> request) {
        try {
            String password = request.get("password");
            String reason = request.get("reason");
            
            if (password == null || password.isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "error", "Password is required to confirm deletion"
                ));
            }
            
            User user = authService.getUserByEmail(userDetails.getUsername());
            
            // Verify password
            if (!authService.verifyPassword(user, password)) {
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "error", "Invalid password"
                ));
            }
            
            // Schedule deletion (30-day grace period)
            privacyService.scheduleAccountDeletion(user.getId(), reason);
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Account scheduled for deletion. You have 30 days to cancel this request."
            ));
        } catch (Exception e) {
            logger.error("Error scheduling account deletion: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to process deletion request"
            ));
        }
    }

    /**
     * Cancel account deletion request
     */
    @PostMapping("/cancel-deletion")
    public ResponseEntity<Map<String, Object>> cancelDeletion(
            @AuthenticationPrincipal UserDetails userDetails) {
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            privacyService.cancelAccountDeletion(user.getId());
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Account deletion cancelled"
            ));
        } catch (Exception e) {
            logger.error("Error cancelling deletion: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to cancel deletion"
            ));
        }
    }

    /**
     * Update consent preferences
     */
    @PostMapping("/consent")
    public ResponseEntity<Map<String, Object>> updateConsent(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody Map<String, Boolean> consent) {
        try {
            User user = authService.getUserByEmail(userDetails.getUsername());
            privacyService.updateConsentPreferences(user.getId(), consent);
            
            return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Consent preferences updated"
            ));
        } catch (Exception e) {
            logger.error("Error updating consent: {}", e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of(
                "success", false,
                "error", "Failed to update consent"
            ));
        }
    }

    /**
     * Get privacy policy information
     */
    @GetMapping("/policy")
    public ResponseEntity<Map<String, Object>> getPrivacyPolicy() {
        return ResponseEntity.ok(Map.of(
            "success", true,
            "policy", Map.of(
                "version", "1.0",
                "lastUpdated", "2026-02-15",
                "dataCollected", new String[]{
                    "Email address",
                    "Name",
                    "Generated content",
                    "Payment information (processed by Razorpay)",
                    "Usage analytics"
                },
                "dataUsage", new String[]{
                    "Provide and improve our services",
                    "Process payments",
                    "Send important notifications",
                    "Analyze usage patterns"
                },
                "dataRetention", "Data is retained while your account is active. Deleted accounts have data removed within 30 days.",
                "thirdParties", new String[]{
                    "Razorpay (payment processing)",
                    "OpenAI (content generation)",
                    "Email service providers"
                },
                "rights", new String[]{
                    "Access your data",
                    "Export your data",
                    "Delete your account",
                    "Update consent preferences"
                },
                "contact", "privacy@creatorstudio.ai"
            )
        ));
    }
}
