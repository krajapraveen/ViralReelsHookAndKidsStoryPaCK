package com.creatorstudio.controller;

import com.creatorstudio.entity.ContactMessage;
import com.creatorstudio.entity.Feedback;
import com.creatorstudio.repository.ContactMessageRepository;
import com.creatorstudio.repository.FeedbackRepository;
import com.creatorstudio.service.EmailService;
import com.creatorstudio.util.InputSanitizer;
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
            String name = (String) request.get("name");
            String email = (String) request.get("email");
            String message = (String) request.get("message");
            
            // Validation
            if (name == null || name.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Name is required"));
            }
            if (email == null || !InputSanitizer.isValidEmail(email)) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Valid email is required"));
            }
            if (message == null || message.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Message is required"));
            }
            
            // XSS check
            if (InputSanitizer.containsXSS(name) || InputSanitizer.containsXSS(message)) {
                logger.warn("XSS attempt detected in feedback from: {}", email);
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Invalid input detected"));
            }
            
            Feedback feedback = new Feedback();
            feedback.setName(InputSanitizer.sanitize(name));
            feedback.setEmail(email.trim().toLowerCase());
            feedback.setType(Feedback.FeedbackType.valueOf(((String) request.get("type")).toUpperCase()));
            feedback.setRating(Integer.parseInt(request.get("rating").toString()));
            feedback.setMessage(InputSanitizer.sanitize(message));
            feedback.setAllowPublic(Boolean.TRUE.equals(request.get("allowPublic")));
            
            feedbackRepository.save(feedback);
            logger.info("Feedback submitted from: {}", feedback.getEmail());
            
            return ResponseEntity.ok(Map.of("status", "success", "message", "Feedback submitted successfully"));
        } catch (Exception e) {
            logger.error("Error submitting feedback: {}", e.getMessage());
            return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Failed to submit feedback"));
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
            String name = request.get("name");
            String email = request.get("email");
            String subject = request.get("subject");
            String message = request.get("message");
            
            // Validation
            if (name == null || name.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Name is required"));
            }
            if (email == null || !InputSanitizer.isValidEmail(email)) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Valid email is required"));
            }
            if (subject == null || subject.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Subject is required"));
            }
            if (message == null || message.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Message is required"));
            }
            
            // XSS check
            if (InputSanitizer.containsXSS(name) || InputSanitizer.containsXSS(subject) || InputSanitizer.containsXSS(message)) {
                logger.warn("XSS attempt detected in contact from: {}", email);
                return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Invalid input detected"));
            }
            
            ContactMessage contactMessage = new ContactMessage();
            contactMessage.setName(InputSanitizer.sanitize(name));
            contactMessage.setEmail(email.trim().toLowerCase());
            contactMessage.setSubject(InputSanitizer.sanitize(subject));
            contactMessage.setMessage(InputSanitizer.sanitize(message));
            contactMessage.setResolved(false);
            
            contactRepository.save(contactMessage);
            logger.info("Contact message from: {} - Subject: {}", contactMessage.getEmail(), contactMessage.getSubject());
            
            // Send notification email
            try {
                emailService.sendContactNotification(
                    contactMessage.getName(),
                    contactMessage.getEmail(),
                    contactMessage.getSubject(),
                    contactMessage.getMessage()
                );
            } catch (Exception emailEx) {
                logger.warn("Failed to send contact notification email: {}", emailEx.getMessage());
            }
            
            return ResponseEntity.ok(Map.of("status", "success", "message", "Message sent successfully"));
        } catch (Exception e) {
            logger.error("Error submitting contact: {}", e.getMessage());
            return ResponseEntity.badRequest().body(Map.of("status", "error", "message", "Failed to send message"));
        }
    }

    /**
     * Submit improvement suggestion from feedback widget
     */
    @PostMapping("/feedback/suggestion")
    public ResponseEntity<Map<String, Object>> submitSuggestion(@RequestBody Map<String, Object> request) {
        try {
            String suggestion = (String) request.get("suggestion");
            String category = (String) request.get("category");
            Object ratingObj = request.get("rating");
            String email = (String) request.get("email");
            
            if (suggestion == null || suggestion.trim().isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false, 
                    "error", "Suggestion is required"
                ));
            }
            
            // XSS check
            if (InputSanitizer.containsXSS(suggestion)) {
                logger.warn("XSS attempt detected in suggestion");
                return ResponseEntity.badRequest().body(Map.of(
                    "success", false, 
                    "error", "Invalid input detected"
                ));
            }
            
            // Save as feedback
            Feedback feedback = new Feedback();
            feedback.setName("Anonymous User");
            feedback.setEmail(email != null && !email.isEmpty() ? email : "anonymous@feedback.local");
            feedback.setType(Feedback.FeedbackType.SUGGESTION);
            feedback.setRating(ratingObj != null ? ((Number) ratingObj).intValue() : 5);
            feedback.setMessage("[" + (category != null ? category.toUpperCase() : "GENERAL") + "] " + InputSanitizer.sanitize(suggestion));
            feedback.setAllowPublic(false);
            
            feedbackRepository.save(feedback);
            logger.info("Improvement suggestion received: category={}", category);
            
            return ResponseEntity.ok(Map.of(
                "success", true, 
                "message", "Thank you for your feedback!"
            ));
        } catch (Exception e) {
            logger.error("Error saving suggestion: {}", e.getMessage());
            return ResponseEntity.ok(Map.of(
                "success", false, 
                "error", "Failed to save feedback"
            ));
        }
    }
}
