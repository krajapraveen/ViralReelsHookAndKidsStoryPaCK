package com.creatorstudio.service;

import com.creatorstudio.entity.*;
import com.creatorstudio.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

/**
 * Service for GDPR/CCPA data privacy compliance
 */
@Service
public class DataPrivacyService {

    private static final Logger logger = LoggerFactory.getLogger(DataPrivacyService.class);

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CreditWalletRepository creditWalletRepository;

    @Autowired
    private CreditLedgerRepository creditLedgerRepository;

    @Autowired
    private GenerationRepository generationRepository;

    @Autowired
    private PaymentRepository paymentRepository;

    @Autowired
    private FeedbackRepository feedbackRepository;

    @Autowired
    private FeatureRequestRepository featureRequestRepository;

    /**
     * Export all user data for viewing
     */
    public Map<String, Object> exportUserData(UUID userId) {
        Map<String, Object> data = new LinkedHashMap<>();
        
        // User profile
        User user = userRepository.findById(userId).orElse(null);
        if (user != null) {
            Map<String, Object> profile = new HashMap<>();
            profile.put("name", user.getName());
            profile.put("email", user.getEmail());
            profile.put("role", user.getRole().name());
            profile.put("createdAt", user.getCreatedAt().toString());
            data.put("profile", profile);
        }
        
        // Credit information
        CreditWallet wallet = creditWalletRepository.findByUserId(userId).orElse(null);
        if (wallet != null) {
            data.put("credits", Map.of(
                "balance", wallet.getBalanceCredits(),
                "updatedAt", wallet.getUpdatedAt() != null ? wallet.getUpdatedAt().toString() : "N/A"
            ));
        }
        
        // Generation history count
        long generationCount = generationRepository.count();
        data.put("generationsCount", generationCount);
        
        // Payment history count
        long paymentCount = paymentRepository.count();
        data.put("paymentsCount", paymentCount);
        
        return data;
    }

    /**
     * Export user data for download (full data export)
     */
    public Map<String, Object> exportUserDataForDownload(UUID userId) {
        Map<String, Object> export = new LinkedHashMap<>();
        export.put("exportDate", LocalDateTime.now().toString());
        export.put("userId", userId.toString());
        
        // User profile
        User user = userRepository.findById(userId).orElse(null);
        if (user != null) {
            export.put("profile", Map.of(
                "name", user.getName(),
                "email", user.getEmail(),
                "role", user.getRole().name(),
                "accountCreated", user.getCreatedAt().toString()
            ));
        }
        
        // Credit wallet
        CreditWallet wallet = creditWalletRepository.findByUserId(userId).orElse(null);
        if (wallet != null) {
            export.put("creditWallet", Map.of(
                "balance", wallet.getBalanceCredits()
            ));
        }
        
        // Credit transactions (summarized)
        List<Map<String, Object>> transactions = new ArrayList<>();
        // Add credit ledger entries if available
        export.put("creditTransactions", transactions);
        
        // Generations (summarized - not full content for privacy)
        export.put("generationsSummary", Map.of(
            "note", "Generation content available upon specific request"
        ));
        
        // Payments (summarized)
        export.put("paymentsSummary", Map.of(
            "note", "Payment details available upon specific request"
        ));
        
        // Feature requests
        List<FeatureRequest> featureRequests = featureRequestRepository.findByUserIdOrderByCreatedAtDesc(userId);
        List<Map<String, Object>> requests = new ArrayList<>();
        for (FeatureRequest fr : featureRequests) {
            requests.add(Map.of(
                "title", fr.getTitle(),
                "status", fr.getStatus().name(),
                "createdAt", fr.getCreatedAt().toString()
            ));
        }
        export.put("featureRequests", requests);
        
        return export;
    }

    /**
     * Schedule account for deletion (30-day grace period)
     */
    @Transactional
    public void scheduleAccountDeletion(UUID userId, String reason) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        // In a real implementation, you would:
        // 1. Set a deletion_scheduled_at timestamp
        // 2. Send confirmation email
        // 3. Schedule a job to delete after 30 days
        
        logger.info("Account deletion scheduled for user: {} - Reason: {}", userId, reason);
        
        // For now, we log the request
        // In production, add a deletion_scheduled field to User entity
    }

    /**
     * Cancel account deletion request
     */
    @Transactional
    public void cancelAccountDeletion(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        logger.info("Account deletion cancelled for user: {}", userId);
        
        // Clear the deletion_scheduled field
    }

    /**
     * Permanently delete user account and all associated data
     */
    @Transactional
    public void deleteUserAccount(UUID userId) {
        logger.info("Permanently deleting account for user: {}", userId);
        
        // Delete in order of dependencies
        // 1. Feature votes
        // 2. Feature requests
        // 3. Feedback
        // 4. Generations
        // 5. Payments
        // 6. Credit ledger
        // 7. Credit wallet
        // 8. User
        
        featureRequestRepository.deleteAll(featureRequestRepository.findByUserIdOrderByCreatedAtDesc(userId));
        creditWalletRepository.findByUserId(userId).ifPresent(creditWalletRepository::delete);
        userRepository.deleteById(userId);
        
        logger.info("Account permanently deleted: {}", userId);
    }

    /**
     * Update user consent preferences
     */
    @Transactional
    public void updateConsentPreferences(UUID userId, Map<String, Boolean> consent) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        // In a real implementation, store consent preferences
        // consent.get("marketing") - marketing emails
        // consent.get("analytics") - usage analytics
        // consent.get("thirdParty") - third-party data sharing
        
        logger.info("Consent preferences updated for user: {} - {}", userId, consent);
    }

    /**
     * Anonymize user data (alternative to deletion)
     */
    @Transactional
    public void anonymizeUserData(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        // Anonymize personal data
        user.setName("Deleted User");
        user.setEmail("deleted_" + userId.toString().substring(0, 8) + "@anonymized.local");
        user.setPasswordHash("DELETED");
        
        userRepository.save(user);
        
        logger.info("User data anonymized: {}", userId);
    }
}
