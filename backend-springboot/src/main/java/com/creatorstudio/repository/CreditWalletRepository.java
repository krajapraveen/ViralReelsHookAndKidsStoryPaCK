package com.creatorstudio.repository;

import com.creatorstudio.entity.CreditWallet;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface CreditWalletRepository extends JpaRepository<CreditWallet, UUID> {
    Optional<CreditWallet> findByUserId(UUID userId);
}