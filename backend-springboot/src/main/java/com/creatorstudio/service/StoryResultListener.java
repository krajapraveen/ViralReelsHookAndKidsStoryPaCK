package com.creatorstudio.service;

import com.creatorstudio.entity.Generation;
import com.creatorstudio.repository.GenerationRepository;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

@Service
public class StoryResultListener {

    @Autowired
    private GenerationRepository generationRepository;

    @RabbitListener(queues = "story.result")
    @Transactional
    public void handleStoryResult(Map<String, Object> message) {
        try {
            String generationId = (String) message.get("generationId");
            Boolean success = (Boolean) message.get("success");
            Map<String, Object> output = (Map<String, Object>) message.get("output");
            String errorMessage = (String) message.get("errorMessage");

            Generation generation = generationRepository.findById(UUID.fromString(generationId))
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
            
            System.out.println("Story generation " + generationId + " completed with status: " + generation.getStatus());
        } catch (Exception e) {
            System.err.println("Error processing story result: " + e.getMessage());
        }
    }
}
