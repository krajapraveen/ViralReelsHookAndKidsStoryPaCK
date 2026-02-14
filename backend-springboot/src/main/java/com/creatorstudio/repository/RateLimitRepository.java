package com.creatorstudio.repository;

import com.creatorstudio.entity.RateLimit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface RateLimitRepository extends JpaRepository<RateLimit, UUID> {
    Optional<RateLimit> findByUserIdAndDate(UUID userId, LocalDate date);
}
