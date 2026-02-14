package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.math.BigDecimal;

@Entity
@Table(name = "products")
@Data
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Type type;

    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal priceInr;

    @Column(nullable = false)
    private Integer credits;

    private String razorpayPlanId;

    @Column(nullable = false)
    private Boolean active = true;

    public enum Type {
        SUBSCRIPTION, CREDIT_PACK
    }
}