package com.creatorstudio.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class ReelGenerationRequest {
    @NotBlank(message = "Topic is required")
    @Size(max = 1000, message = "Topic must be less than 1000 characters")
    private String topic;
    
    @Size(max = 100, message = "Niche must be less than 100 characters")
    private String niche;
    
    @Size(max = 50, message = "Tone must be less than 50 characters")
    private String tone;
    
    @Size(max = 10, message = "Duration must be less than 10 characters")
    private String duration;
    
    @Size(max = 50, message = "Language must be less than 50 characters")
    private String language;
    
    @Size(max = 50, message = "Goal must be less than 50 characters")
    private String goal;
    
    @Size(max = 200, message = "Audience must be less than 200 characters")
    private String audience;
}