package com.creatorstudio.service;

import com.creatorstudio.entity.CreditLedger;
import com.creatorstudio.entity.CreditWallet;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.CreditLedgerRepository;
import com.creatorstudio.repository.CreditWalletRepository;
import com.creatorstudio.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.UUID;

@Service
public class CreditService {

    private static final Logger logger = LoggerFactory.getLogger(CreditService.class);
    private static final int LOW_CREDITS_THRESHOLD = 10;

    @Autowired
    private CreditWalletRepository walletRepository;

    @Autowired
    private CreditLedgerRepository ledgerRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private EmailService emailService;

    @Cacheable(value = "userCredits", key = "#userId")
    public BigDecimal getBalance(UUID userId) {
        return walletRepository.findById(userId)
                .map(CreditWallet::getBalanceCredits)
                .orElse(BigDecimal.ZERO);
    }

    public Page<CreditLedger> getLedger(UUID userId, Pageable pageable) {
        return ledgerRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    @Transactional
    @CacheEvict(value = "userCredits", key = "#userId")
    public void deductCredits(UUID userId, BigDecimal amount, CreditLedger.Reason reason, String referenceId) {
        CreditWallet wallet = walletRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("Wallet not found"));

        if (wallet.getBalanceCredits().compareTo(amount) < 0) {
            throw new RuntimeException("Insufficient credits");
        }

        BigDecimal newBalance = wallet.getBalanceCredits().subtract(amount);
        wallet.setBalanceCredits(newBalance);
        walletRepository.save(wallet);

        addCreditLedgerEntry(userId, amount, CreditLedger.Type.DEBIT, reason, referenceId);

        // Check for low credits and send notification
        checkAndNotifyLowCredits(userId, newBalance);
    }

    @Transactional
    @CacheEvict(value = "userCredits", key = "#userId")
    public void addCredits(UUID userId, BigDecimal amount, CreditLedger.Reason reason, String referenceId) {
        CreditWallet wallet = walletRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("Wallet not found"));

        wallet.setBalanceCredits(wallet.getBalanceCredits().add(amount));
        walletRepository.save(wallet);

        addCreditLedgerEntry(userId, amount, CreditLedger.Type.CREDIT, reason, referenceId);
    }

    public void addCreditLedgerEntry(UUID userId, BigDecimal amount, CreditLedger.Type type, 
                                      CreditLedger.Reason reason, String referenceId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CreditLedger entry = new CreditLedger();
        entry.setUser(user);
        entry.setAmount(amount);
        entry.setType(type);
        entry.setReason(reason);
        entry.setReferenceId(referenceId);
        ledgerRepository.save(entry);
    }

    private void checkAndNotifyLowCredits(UUID userId, BigDecimal newBalance) {
        if (newBalance.compareTo(BigDecimal.valueOf(LOW_CREDITS_THRESHOLD)) <= 0 
                && newBalance.compareTo(BigDecimal.ZERO) > 0) {
            try {
                User user = userRepository.findById(userId).orElse(null);
                if (user != null) {
                    logger.info("Sending low credits notification to user: {}", user.getEmail());
                    emailService.sendLowCreditsEmail(user.getEmail(), user.getName(), newBalance.intValue());
                }
            } catch (Exception e) {
                logger.error("Failed to send low credits notification: {}", e.getMessage());
            }
        }
    }
}