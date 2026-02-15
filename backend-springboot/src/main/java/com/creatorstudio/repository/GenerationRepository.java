package com.creatorstudio.repository;

import com.creatorstudio.entity.Generation;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Repository
public interface GenerationRepository extends JpaRepository<Generation, UUID> {
    Page<Generation> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);
    Page<Generation> findByUserIdAndTypeOrderByCreatedAtDesc(UUID userId, Generation.Type type, Pageable pageable);
    
    @Query("SELECT COUNT(g) FROM Generation g WHERE g.type = :type AND g.createdAt >= :startDate")
    long countByTypeAndCreatedAtAfter(@Param("type") Generation.Type type, @Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(g) FROM Generation g WHERE g.status = :status AND g.createdAt >= :startDate")
    long countByStatusAndCreatedAtAfter(@Param("status") Generation.Status status, @Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COALESCE(SUM(g.creditsUsed), 0) FROM Generation g WHERE g.createdAt >= :startDate")
    BigDecimal sumCreditsUsedSince(@Param("startDate") LocalDateTime startDate);
}