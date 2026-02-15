package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "feedback")
@Data
public class Feedback {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    private String name;
    private String email;
    
    @Enumerated(EnumType.STRING)
    private FeedbackType type;
    
    private Integer rating;
    
    @Column(columnDefinition = "TEXT")
    private String message;
    
    private boolean allowPublic;
    
    @CreationTimestamp
    private LocalDateTime createdAt;

    public enum FeedbackType {
        FEEDBACK, REVIEW, BUG, FEATURE, SUGGESTION, IMPROVEMENT, PRAISE
    }
}
