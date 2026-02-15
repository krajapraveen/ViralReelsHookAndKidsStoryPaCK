package com.creatorstudio.repository;

import com.creatorstudio.entity.Payment;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface PaymentRepository extends JpaRepository<Payment, UUID> {
    Page<Payment> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);
    Optional<Payment> findByProviderOrderId(String providerOrderId);
    
    List<Payment> findTop10ByOrderByCreatedAtDesc();
    
    @Query("SELECT COALESCE(SUM(p.amountInr), 0) FROM Payment p WHERE p.status = 'PAID'")
    BigDecimal sumTotalRevenue();
    
    @Query("SELECT COALESCE(SUM(p.amountInr), 0) FROM Payment p WHERE p.status = 'PAID' AND p.createdAt >= :startDate")
    BigDecimal sumRevenueSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(p) FROM Payment p WHERE p.createdAt >= :startDate")
    long countByCreatedAtAfter(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(p) FROM Payment p WHERE p.status = :status AND p.createdAt >= :startDate")
    long countByStatusAndCreatedAtAfter(@Param("status") Payment.Status status, @Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT p.product.name, COUNT(p), COALESCE(SUM(p.amountInr), 0) FROM Payment p WHERE p.status = 'PAID' AND p.createdAt >= :startDate GROUP BY p.product.name")
    List<Object[]> getSubscriptionsByProduct(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT DATE(p.createdAt), COALESCE(SUM(p.amountInr), 0), COUNT(p) FROM Payment p WHERE p.status = 'PAID' AND p.createdAt >= :startDate GROUP BY DATE(p.createdAt) ORDER BY DATE(p.createdAt)")
    List<Object[]> getDailyRevenueSince(@Param("startDate") LocalDateTime startDate);
    
    @Query("SELECT COUNT(p) FROM Payment p WHERE p.status = 'FAILED' AND p.createdAt >= :startDate AND LOWER(COALESCE(p.providerPaymentId, '')) LIKE %:reason%")
    Long countFailedByReason(@Param("reason") String reason, @Param("startDate") LocalDateTime startDate);
}