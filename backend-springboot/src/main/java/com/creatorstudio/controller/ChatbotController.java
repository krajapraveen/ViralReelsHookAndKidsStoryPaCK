package com.creatorstudio.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Controller for AI Chatbot functionality
 * Proxies requests to the Python worker service
 */
@RestController
@RequestMapping("/api/chatbot")
public class ChatbotController {

    private static final Logger logger = LoggerFactory.getLogger(ChatbotController.class);

    @Value("${worker.api.url}")
    private String workerApiUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * Send a message to the chatbot
     */
    @PostMapping("/message")
    public ResponseEntity<Map<String, Object>> sendMessage(@RequestBody Map<String, Object> request) {
        try {
            String url = workerApiUrl + "/chatbot/message";
            
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
            
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            
            return ResponseEntity.ok(response.getBody());
        } catch (Exception e) {
            logger.error("Chatbot error: {}", e.getMessage());
            return ResponseEntity.ok(Map.of(
                "success", false,
                "response", "I'm having trouble connecting. Please try again.",
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Clear a chat session
     */
    @PostMapping("/clear")
    public ResponseEntity<Map<String, Object>> clearSession(@RequestBody Map<String, Object> request) {
        try {
            String url = workerApiUrl + "/chatbot/clear";
            
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
            
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            
            return ResponseEntity.ok(response.getBody());
        } catch (Exception e) {
            logger.error("Clear session error: {}", e.getMessage());
            return ResponseEntity.ok(Map.of("success", true, "message", "Session cleared locally"));
        }
    }
}
