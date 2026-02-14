package com.creatorstudio.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class StoryGenerationRequest {
    @NotNull(message = "Age group is required")
    @Size(max = 50, message = "Age group must be less than 50 characters")
    private String ageGroup;
    
    @Size(max = 100, message = "Theme must be less than 100 characters")
    private String theme;
    
    @Size(max = 100, message = "Genre must be less than 100 characters")
    private String genre;
    
    @Size(max = 200, message = "Moral must be less than 200 characters")
    private String moral;
    
    private List<String> characters;
    
    @Size(max = 100, message = "Setting must be less than 100 characters")
    private String setting;
    
    @NotNull(message = "Number of scenes is required")
    @Min(value = 8, message = "Minimum 8 scenes required")
    @Max(value = 12, message = "Maximum 12 scenes allowed")
    private Integer scenes;
    
    @Size(max = 50, message = "Language must be less than 50 characters")
    private String language;
    
    @Size(max = 100, message = "Style must be less than 100 characters")
    private String style;
    
    @Size(max = 10, message = "Length must be less than 10 characters")
    private String length;
}