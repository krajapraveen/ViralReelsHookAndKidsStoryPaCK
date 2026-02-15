package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "feature_requests")
@Data
public class FeatureRequest {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;
    
    @Column(nullable = false)
    private String title;
    
    @Column(columnDefinition = "TEXT", nullable = false)
    private String description;
    
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Category category;
    
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Status status = Status.PENDING;
    
    @Column(name = "vote_count")
    private Integer voteCount = 0;
    
    @Column(name = "admin_response", columnDefinition = "TEXT")
    private String adminResponse;
    
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    public enum Category {
        AI_GENERATION,
        UI_UX,
        PAYMENTS,
        INTEGRATIONS,
        EXPORT_OPTIONS,
        ANALYTICS,
        COLLABORATION,
        MOBILE_APP,
        OTHER
    }
    
    public enum Status {
        PENDING,
        UNDER_REVIEW,
        PLANNED,
        IN_PROGRESS,
        COMPLETED,
        DECLINED
    }
}
