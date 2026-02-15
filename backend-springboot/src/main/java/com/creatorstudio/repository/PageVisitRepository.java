package com.creatorstudio.repository;

import com.creatorstudio.entity.PageVisit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface PageVisitRepository extends JpaRepository<PageVisit, Long> {
    
    @Query("SELECT COUNT(DISTINCT p.sessionId) FROM PageVisit p WHERE p.visitedAt >= :startDate")
    Long countUniqueVisitorsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(p) FROM PageVisit p WHERE p.visitedAt >= :startDate")
    Long countTotalPageViewsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT p.page, COUNT(p) as count FROM PageVisit p WHERE p.visitedAt >= :startDate GROUP BY p.page ORDER BY count DESC")
    List<Object[]> getPageViewCountsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT DATE(p.visitedAt), COUNT(DISTINCT p.sessionId) FROM PageVisit p WHERE p.visitedAt >= :startDate GROUP BY DATE(p.visitedAt) ORDER BY DATE(p.visitedAt)")
    List<Object[]> getDailyVisitorsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(DISTINCT p.sessionId) FROM PageVisit p WHERE p.visitedAt >= :startDate AND p.userId IS NULL")
    Long countAnonymousVisitorsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(DISTINCT p.userId) FROM PageVisit p WHERE p.visitedAt >= :startDate AND p.userId IS NOT NULL")
    Long countLoggedInVisitorsSince(@Param("startDate") LocalDateTime startDate);
}
