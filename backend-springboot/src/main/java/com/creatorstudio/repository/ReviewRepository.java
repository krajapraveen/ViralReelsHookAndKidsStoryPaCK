package com.creatorstudio.repository;

import com.creatorstudio.entity.Feedback;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface ReviewRepository extends JpaRepository<Feedback, UUID> {
    
    @Query("SELECT AVG(f.rating) FROM Feedback f WHERE f.type = 'REVIEW' AND f.rating IS NOT NULL")
    Double getAverageRating();
    
    @Query("SELECT COUNT(f) FROM Feedback f WHERE f.type = 'REVIEW'")
    long countReviews();
    
    @Query("SELECT f.rating, COUNT(f) FROM Feedback f WHERE f.type = 'REVIEW' AND f.rating IS NOT NULL GROUP BY f.rating")
    List<Object[]> getRatingDistribution();
    
    @Query("SELECT f FROM Feedback f WHERE f.type = 'REVIEW' ORDER BY f.createdAt DESC LIMIT 5")
    List<Feedback> findTop5ReviewsByOrderByCreatedAtDesc();
}
