package com.creatorstudio.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "page_visits")
@Data
public class PageVisit {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "user_id")
    private UUID userId;
    
    @Column(name = "session_id")
    private String sessionId;
    
    @Column(nullable = false)
    private String page;
    
    @Column(name = "user_agent")
    private String userAgent;
    
    @Column(name = "ip_address")
    private String ipAddress;
    
    @Column(name = "referrer")
    private String referrer;
    
    @CreationTimestamp
    @Column(name = "visited_at")
    private LocalDateTime visitedAt;
}
