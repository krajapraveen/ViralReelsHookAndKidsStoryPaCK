package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "credit_wallet")
@Data
public class CreditWallet {
    @Id
    private UUID userId;

    @OneToOne
    @MapsId
    @JoinColumn(name = "user_id")
    private User user;

    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal balanceCredits = BigDecimal.ZERO;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}