package com.creatorstudio.dto;

import lombok.Data;

import java.util.List;

@Data
public class StoryGenerationRequest {
    private String ageGroup;
    private String theme;
    private String moral;
    private List<String> characters;
    private String setting;
    private Integer scenes;
    private String language;
    private String style;
    private String length;
}