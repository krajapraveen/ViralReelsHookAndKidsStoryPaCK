package com.creatorstudio.repository;

import com.creatorstudio.entity.UserSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface UserSessionRepository extends JpaRepository<UserSession, Long> {
    
    Optional<UserSession> findBySessionId(String sessionId);
    
    @Query("SELECT s.deviceType, COUNT(s) FROM UserSession s WHERE s.startedAt >= :startDate GROUP BY s.deviceType")
    List<Object[]> getDeviceTypeDistributionSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT s.browser, COUNT(s) FROM UserSession s WHERE s.startedAt >= :startDate GROUP BY s.browser")
    List<Object[]> getBrowserDistributionSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(s) FROM UserSession s WHERE s.startedAt >= :startDate")
    Long countSessionsSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(s) FROM UserSession s WHERE s.isActive = true")
    Long countActiveSessions();
}
