package com.creatorstudio.repository;

import com.creatorstudio.entity.FeatureVote;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface FeatureVoteRepository extends JpaRepository<FeatureVote, UUID> {
    
    Optional<FeatureVote> findByUserIdAndFeatureRequestId(UUID userId, UUID featureRequestId);
    
    boolean existsByUserIdAndFeatureRequestId(UUID userId, UUID featureRequestId);
    
    long countByFeatureRequestId(UUID featureRequestId);
    
    void deleteByUserIdAndFeatureRequestId(UUID userId, UUID featureRequestId);
}
