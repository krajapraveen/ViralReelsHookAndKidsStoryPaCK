package com.creatorstudio.repository;

import com.creatorstudio.entity.CreditLedger;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface CreditLedgerRepository extends JpaRepository<CreditLedger, UUID> {
    Page<CreditLedger> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);
}