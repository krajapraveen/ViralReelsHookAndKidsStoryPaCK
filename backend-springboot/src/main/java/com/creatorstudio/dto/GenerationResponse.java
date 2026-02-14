package com.creatorstudio.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.Map;
import java.util.UUID;

@Data
@AllArgsConstructor
public class GenerationResponse {
    private UUID generationId;
    private String status;
    private Map<String, Object> output;
}