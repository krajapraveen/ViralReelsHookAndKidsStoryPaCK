package com.creatorstudio.dto;

import lombok.Data;

import java.util.Map;

@Data
public class ReelGenerationRequest {
    private String topic;
    private String niche;
    private String tone;
    private String duration;
    private String language;
    private String goal;
    private String audience;
}