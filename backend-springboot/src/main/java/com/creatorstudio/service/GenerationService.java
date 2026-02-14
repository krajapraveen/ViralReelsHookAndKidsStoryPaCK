package com.creatorstudio.service;

import com.creatorstudio.config.RabbitMQConfig;
import com.creatorstudio.dto.GenerationResponse;
import com.creatorstudio.dto.ReelGenerationRequest;
import com.creatorstudio.dto.StoryGenerationRequest;
import com.creatorstudio.entity.CreditLedger;
import com.creatorstudio.entity.Generation;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.GenerationRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class GenerationService {

    @Autowired
    private GenerationRepository generationRepository;

    @Autowired
    private CreditService creditService;

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private RateLimitService rateLimitService;

    @Value("${worker.api.url}")
    private String workerApiUrl;

    @Transactional
    public GenerationResponse generateReel(UUID userId, ReelGenerationRequest request) {
        // Check rate limit
        rateLimitService.checkAndIncrementRateLimit(userId);
        // Deduct 1 credit
        creditService.deductCredits(userId, BigDecimal.ONE, CreditLedger.Reason.REEL_GEN, null);

        // Create generation record
        Generation generation = new Generation();
        generation.setUser(new User());
        generation.getUser().setId(userId);
        generation.setType(Generation.Type.REEL);
        generation.setStatus(Generation.Status.RUNNING);
        generation.setInputJson(objectMapper.convertValue(request, Map.class));
        generation.setCreditsUsed(BigDecimal.ONE);

        try {
            // Call Python worker directly for instant generation
            Map<String, Object> output = callReelWorker(request);
            generation.setOutputJson(output);
            generation.setStatus(Generation.Status.SUCCEEDED);
            generation.setCompletedAt(LocalDateTime.now());
        } catch (Exception e) {
            generation.setStatus(Generation.Status.FAILED);
            generation.setErrorMessage(e.getMessage());
            generation.setCompletedAt(LocalDateTime.now());
        }

        generation = generationRepository.save(generation);
        return new GenerationResponse(generation.getId(), generation.getStatus().toString(), generation.getOutputJson());
    }

    @Transactional
    public GenerationResponse generateStory(UUID userId, StoryGenerationRequest request) {
        // Calculate credits based on scenes
        BigDecimal credits;
        switch (request.getScenes()) {
            case 8: credits = new BigDecimal("6.00"); break;
            case 10: credits = new BigDecimal("7.00"); break;
            case 12: credits = new BigDecimal("8.00"); break;
            default: credits = new BigDecimal("6.00");
        }

        // Deduct credits
        creditService.deductCredits(userId, credits, CreditLedger.Reason.STORY_GEN, null);

        // Create generation record
        Generation generation = new Generation();
        generation.setUser(new User());
        generation.getUser().setId(userId);
        generation.setType(Generation.Type.STORY);
        generation.setStatus(Generation.Status.PENDING);
        generation.setInputJson(objectMapper.convertValue(request, Map.class));
        generation.setCreditsUsed(credits);
        generation = generationRepository.save(generation);

        // Send to queue
        Map<String, Object> message = new HashMap<>();
        message.put("generationId", generation.getId().toString());
        message.put("userId", userId.toString());
        message.put("inputJson", generation.getInputJson());

        rabbitTemplate.convertAndSend(
                RabbitMQConfig.EXCHANGE,
                RabbitMQConfig.STORY_REQUEST_ROUTING_KEY,
                message
        );

        return new GenerationResponse(generation.getId(), generation.getStatus().toString(), null);
    }

    public Generation getGeneration(UUID generationId) {
        return generationRepository.findById(generationId)
                .orElseThrow(() -> new RuntimeException("Generation not found"));
    }

    public Page<Generation> getUserGenerations(UUID userId, String type, Pageable pageable) {
        if (type != null && !type.isEmpty()) {
            return generationRepository.findByUserIdAndTypeOrderByCreatedAtDesc(
                    userId, Generation.Type.valueOf(type.toUpperCase()), pageable);
        }
        return generationRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    private Map<String, Object> callReelWorker(ReelGenerationRequest request) {
        String workerUrl = workerApiUrl + "/generate/reel";
        
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        
        HttpEntity<ReelGenerationRequest> entity = new HttpEntity<>(request, headers);
        
        try {
            Map<String, Object> response = restTemplate.postForObject(workerUrl, entity, Map.class);
            return response;
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate reel: " + e.getMessage());
        }
    }

    @Transactional
    public void updateGenerationResult(UUID generationId, Map<String, Object> output, boolean success, String errorMessage) {
        Generation generation = generationRepository.findById(generationId)
                .orElseThrow(() -> new RuntimeException("Generation not found"));
        
        if (success) {
            generation.setStatus(Generation.Status.SUCCEEDED);
            generation.setOutputJson(output);
        } else {
            generation.setStatus(Generation.Status.FAILED);
            generation.setErrorMessage(errorMessage);
        }
        generation.setCompletedAt(LocalDateTime.now());
        generationRepository.save(generation);
    }
}
