package com.creatorstudio.repository;

import com.creatorstudio.entity.Feedback;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface FeedbackRepository extends JpaRepository<Feedback, UUID> {
    List<Feedback> findByAllowPublicTrueAndTypeOrderByCreatedAtDesc(Feedback.FeedbackType type);
    List<Feedback> findByAllowPublicTrueOrderByCreatedAtDesc();
    List<Feedback> findAllByOrderByCreatedAtDesc();
}
