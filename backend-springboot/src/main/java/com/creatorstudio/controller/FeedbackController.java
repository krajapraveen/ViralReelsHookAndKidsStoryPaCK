package com.creatorstudio.controller;

import com.creatorstudio.entity.ContactMessage;
import com.creatorstudio.entity.Feedback;
import com.creatorstudio.repository.ContactMessageRepository;
import com.creatorstudio.repository.FeedbackRepository;
import com.creatorstudio.service.EmailService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class FeedbackController {

    private static final Logger logger = LoggerFactory.getLogger(FeedbackController.class);

    @Autowired
    private FeedbackRepository feedbackRepository;

    @Autowired
    private ContactMessageRepository contactRepository;

    @Autowired
    private EmailService emailService;

    @PostMapping("/feedback")
    public ResponseEntity<Map<String, String>> submitFeedback(@RequestBody Map<String, Object> request) {
        try {
            Feedback feedback = new Feedback();
            feedback.setName((String) request.get("name"));
            feedback.setEmail((String) request.get("email"));
            feedback.setType(Feedback.FeedbackType.valueOf(((String) request.get("type")).toUpperCase()));
            feedback.setRating(Integer.parseInt(request.get("rating").toString()));
            feedback.setMessage((String) request.get("message"));
            feedback.setAllowPublic(Boolean.TRUE.equals(request.get("allowPublic")));
            
            feedbackRepository.save(feedback);
            logger.info("Feedback submitted from: {}", feedback.getEmail());
            
            return ResponseEntity.ok(Map.of("status", "success", "message", "Feedback submitted successfully"));
        } catch (Exception e) {
            logger.error("Error submitting feedback: {}", e.getMessage());
            return ResponseEntity.badRequest().body(Map.of("status", "error", "message", e.getMessage()));
        }
    }

    @GetMapping("/reviews")
    public ResponseEntity<List<Feedback>> getPublicReviews() {
        List<Feedback> reviews = feedbackRepository.findByAllowPublicTrueAndTypeOrderByCreatedAtDesc(Feedback.FeedbackType.REVIEW);
        return ResponseEntity.ok(reviews);
    }

    @PostMapping("/contact")
    public ResponseEntity<Map<String, String>> submitContact(@RequestBody Map<String, String> request) {
        try {
            ContactMessage message = new ContactMessage();
            message.setName(request.get("name"));
            message.setEmail(request.get("email"));
            message.setSubject(request.get("subject"));
            message.setMessage(request.get("message"));
            message.setResolved(false);
            
            contactRepository.save(message);
            logger.info("Contact message from: {} - Subject: {}", message.getEmail(), message.getSubject());
            
            // Send notification email
            emailService.sendContactNotification(
                message.getName(),
                message.getEmail(),
                message.getSubject(),
                message.getMessage()
            );
            
            return ResponseEntity.ok(Map.of("status", "success", "message", "Message sent successfully"));
        } catch (Exception e) {
            logger.error("Error submitting contact: {}", e.getMessage());
            return ResponseEntity.badRequest().body(Map.of("status", "error", "message", e.getMessage()));
        }
    }
}
