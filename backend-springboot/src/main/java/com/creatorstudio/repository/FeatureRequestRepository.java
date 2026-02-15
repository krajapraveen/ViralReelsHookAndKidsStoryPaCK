package com.creatorstudio.repository;

import com.creatorstudio.entity.FeatureRequest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface FeatureRequestRepository extends JpaRepository<FeatureRequest, UUID> {
    
    Page<FeatureRequest> findAllByOrderByVoteCountDesc(Pageable pageable);
    
    Page<FeatureRequest> findByStatusOrderByVoteCountDesc(FeatureRequest.Status status, Pageable pageable);
    
    Page<FeatureRequest> findByCategoryOrderByVoteCountDesc(FeatureRequest.Category category, Pageable pageable);
    
    List<FeatureRequest> findTop10ByOrderByVoteCountDesc();
    
    List<FeatureRequest> findByUserIdOrderByCreatedAtDesc(UUID userId);
    
    @Query("SELECT fr.category, COUNT(fr) FROM FeatureRequest fr GROUP BY fr.category ORDER BY COUNT(fr) DESC")
    List<Object[]> countByCategory();
    
    @Query("SELECT fr.status, COUNT(fr) FROM FeatureRequest fr GROUP BY fr.status")
    List<Object[]> countByStatus();
    
    @Query("SELECT COUNT(fr) FROM FeatureRequest fr")
    long countTotal();
    
    @Query("SELECT COALESCE(SUM(fr.voteCount), 0) FROM FeatureRequest fr")
    long sumTotalVotes();
}
