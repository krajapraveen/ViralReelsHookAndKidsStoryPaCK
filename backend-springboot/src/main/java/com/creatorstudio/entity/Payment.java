package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "payments")
@Data
public class Payment {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(nullable = false)
    private String provider = "RAZORPAY";

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Status status = Status.CREATED;

    @Column(unique = true)
    private String providerOrderId;

    private String providerPaymentId;

    private String providerSignature;

    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal amountInr;

    // International payment support
    @Column(length = 3)
    private String currency = "INR";

    @Column(precision = 10, scale = 2)
    private BigDecimal amountInCurrency;

    @Column(length = 3)
    private String country;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    public enum Status {
        CREATED, PAID, FAILED, REFUNDED
    }
}