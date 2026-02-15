package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "feature_votes", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"user_id", "feature_request_id"})
})
@Data
public class FeatureVote {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "feature_request_id", nullable = false)
    private FeatureRequest featureRequest;
    
    @CreationTimestamp
    @Column(name = "voted_at", nullable = false, updatable = false)
    private LocalDateTime votedAt;
}
