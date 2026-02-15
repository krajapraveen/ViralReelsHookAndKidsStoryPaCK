package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "feature_usage")
@Data
public class FeatureUsage {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "user_id")
    private UUID userId;
    
    @Column(nullable = false)
    private String feature;
    
    @Column(name = "action")
    private String action;
    
    @Column(name = "metadata", columnDefinition = "TEXT")
    private String metadata;
    
    @CreationTimestamp
    @Column(name = "used_at")
    private LocalDateTime usedAt;
    
    public enum Feature {
        REEL_GENERATOR,
        STORY_GENERATOR,
        DEMO_REEL,
        DOWNLOAD_JSON,
        DOWNLOAD_PDF,
        COPY_CONTENT,
        SHARE_CONTENT,
        VIEW_PRICING,
        INITIATE_PAYMENT,
        COMPLETE_PAYMENT,
        VIEW_HISTORY,
        CONTACT_FORM,
        FEEDBACK_FORM,
        GOOGLE_LOGIN,
        EMAIL_LOGIN,
        REGISTER
    }
}
