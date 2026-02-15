package com.creatorstudio.service;

import com.creatorstudio.entity.FeatureRequest;
import com.creatorstudio.entity.FeatureVote;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.FeatureRequestRepository;
import com.creatorstudio.repository.FeatureVoteRepository;
import com.creatorstudio.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class FeatureRequestService {

    private static final Logger logger = LoggerFactory.getLogger(FeatureRequestService.class);

    @Autowired
    private FeatureRequestRepository featureRequestRepository;

    @Autowired
    private FeatureVoteRepository featureVoteRepository;

    @Autowired
    private UserRepository userRepository;

    /**
     * Create a new feature request
     */
    @Transactional
    public FeatureRequest createFeatureRequest(UUID userId, String title, String description, String category) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        FeatureRequest request = new FeatureRequest();
        request.setUser(user);
        request.setTitle(title);
        request.setDescription(description);
        request.setCategory(FeatureRequest.Category.valueOf(category.toUpperCase()));
        request.setStatus(FeatureRequest.Status.PENDING);
        request.setVoteCount(1); // Creator's vote is automatic

        FeatureRequest saved = featureRequestRepository.save(request);

        // Add creator's vote automatically
        FeatureVote vote = new FeatureVote();
        vote.setUser(user);
        vote.setFeatureRequest(saved);
        featureVoteRepository.save(vote);

        logger.info("Feature request created: {} by user {}", saved.getId(), userId);
        return saved;
    }

    /**
     * Vote for a feature request
     */
    @Transactional
    public Map<String, Object> voteForFeature(UUID userId, UUID featureRequestId) {
        // Check if already voted
        if (featureVoteRepository.existsByUserIdAndFeatureRequestId(userId, featureRequestId)) {
            return Map.of(
                "success", false,
                "message", "You have already voted for this feature"
            );
        }

        FeatureRequest request = featureRequestRepository.findById(featureRequestId)
                .orElseThrow(() -> new RuntimeException("Feature request not found"));

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        // Add vote
        FeatureVote vote = new FeatureVote();
        vote.setUser(user);
        vote.setFeatureRequest(request);
        featureVoteRepository.save(vote);

        // Update vote count
        request.setVoteCount(request.getVoteCount() + 1);
        featureRequestRepository.save(request);

        logger.info("User {} voted for feature {}", userId, featureRequestId);

        return Map.of(
            "success", true,
            "message", "Vote recorded successfully",
            "newVoteCount", request.getVoteCount()
        );
    }

    /**
     * Remove vote from a feature request
     */
    @Transactional
    public Map<String, Object> removeVote(UUID userId, UUID featureRequestId) {
        Optional<FeatureVote> existingVote = featureVoteRepository.findByUserIdAndFeatureRequestId(userId, featureRequestId);
        
        if (existingVote.isEmpty()) {
            return Map.of(
                "success", false,
                "message", "You haven't voted for this feature"
            );
        }

        FeatureRequest request = featureRequestRepository.findById(featureRequestId)
                .orElseThrow(() -> new RuntimeException("Feature request not found"));

        // Check if user is the creator (can't remove own initial vote)
        if (request.getUser().getId().equals(userId) && request.getVoteCount() <= 1) {
            return Map.of(
                "success", false,
                "message", "Cannot remove your vote from your own feature request"
            );
        }

        featureVoteRepository.delete(existingVote.get());

        // Update vote count
        request.setVoteCount(Math.max(0, request.getVoteCount() - 1));
        featureRequestRepository.save(request);

        return Map.of(
            "success", true,
            "message", "Vote removed successfully",
            "newVoteCount", request.getVoteCount()
        );
    }

    /**
     * Get all feature requests with pagination
     */
    public Page<FeatureRequest> getAllFeatureRequests(Pageable pageable) {
        return featureRequestRepository.findAllByOrderByVoteCountDesc(pageable);
    }

    /**
     * Get top feature requests
     */
    public List<FeatureRequest> getTopFeatureRequests() {
        return featureRequestRepository.findTop10ByOrderByVoteCountDesc();
    }

    /**
     * Get feature requests by user
     */
    public List<FeatureRequest> getUserFeatureRequests(UUID userId) {
        return featureRequestRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    /**
     * Check if user has voted for a feature
     */
    public boolean hasUserVoted(UUID userId, UUID featureRequestId) {
        return featureVoteRepository.existsByUserIdAndFeatureRequestId(userId, featureRequestId);
    }

    /**
     * Update feature request status (Admin only)
     */
    @Transactional
    public FeatureRequest updateStatus(UUID featureRequestId, String status, String adminResponse) {
        FeatureRequest request = featureRequestRepository.findById(featureRequestId)
                .orElseThrow(() -> new RuntimeException("Feature request not found"));

        request.setStatus(FeatureRequest.Status.valueOf(status.toUpperCase()));
        if (adminResponse != null && !adminResponse.trim().isEmpty()) {
            request.setAdminResponse(adminResponse);
        }
        request.setUpdatedAt(LocalDateTime.now());

        return featureRequestRepository.save(request);
    }

    /**
     * Get feature request analytics for admin dashboard
     */
    public Map<String, Object> getFeatureRequestAnalytics() {
        Map<String, Object> analytics = new LinkedHashMap<>();

        // Total counts
        analytics.put("totalRequests", featureRequestRepository.countTotal());
        analytics.put("totalVotes", featureRequestRepository.sumTotalVotes());

        // By category
        List<Object[]> categoryStats = featureRequestRepository.countByCategory();
        List<Map<String, Object>> categoryList = new ArrayList<>();
        for (Object[] row : categoryStats) {
            Map<String, Object> item = new HashMap<>();
            item.put("category", row[0].toString());
            item.put("count", row[1]);
            categoryList.add(item);
        }
        analytics.put("byCategory", categoryList);

        // By status
        List<Object[]> statusStats = featureRequestRepository.countByStatus();
        Map<String, Long> statusMap = new LinkedHashMap<>();
        for (FeatureRequest.Status s : FeatureRequest.Status.values()) {
            statusMap.put(s.name(), 0L);
        }
        for (Object[] row : statusStats) {
            statusMap.put(row[0].toString(), (Long) row[1]);
        }
        analytics.put("byStatus", statusMap);

        // Top requested features
        List<FeatureRequest> topRequests = featureRequestRepository.findTop10ByOrderByVoteCountDesc();
        List<Map<String, Object>> topList = new ArrayList<>();
        for (FeatureRequest fr : topRequests) {
            Map<String, Object> item = new HashMap<>();
            item.put("id", fr.getId().toString());
            item.put("title", fr.getTitle());
            item.put("description", fr.getDescription());
            item.put("category", fr.getCategory().name());
            item.put("status", fr.getStatus().name());
            item.put("voteCount", fr.getVoteCount());
            item.put("createdAt", fr.getCreatedAt().toString());
            item.put("adminResponse", fr.getAdminResponse());
            topList.add(item);
        }
        analytics.put("topRequests", topList);

        return analytics;
    }
}
