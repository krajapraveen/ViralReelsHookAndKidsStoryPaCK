package com.creatorstudio.repository;

import com.creatorstudio.entity.FeatureUsage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface FeatureUsageRepository extends JpaRepository<FeatureUsage, Long> {
    
    @Query("SELECT f.feature, COUNT(f) as count FROM FeatureUsage f WHERE f.usedAt >= :startDate GROUP BY f.feature ORDER BY count DESC")
    List<Object[]> getFeatureUsageCountsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT f.feature, f.action, COUNT(f) as count FROM FeatureUsage f WHERE f.usedAt >= :startDate GROUP BY f.feature, f.action ORDER BY count DESC")
    List<Object[]> getFeatureActionCountsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT DATE(f.usedAt), f.feature, COUNT(f) FROM FeatureUsage f WHERE f.usedAt >= :startDate GROUP BY DATE(f.usedAt), f.feature ORDER BY DATE(f.usedAt)")
    List<Object[]> getDailyFeatureUsageSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(DISTINCT f.userId) FROM FeatureUsage f WHERE f.feature = :feature AND f.usedAt >= :startDate")
    Long countUniqueUsersByFeatureSince(@Param("feature") String feature, @Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT f.feature, COUNT(DISTINCT f.userId) as uniqueUsers FROM FeatureUsage f WHERE f.usedAt >= :startDate GROUP BY f.feature ORDER BY uniqueUsers DESC")
    List<Object[]> getFeatureUniqueUsersSince(@Param("startDate") LocalDateTime startDate);
}
