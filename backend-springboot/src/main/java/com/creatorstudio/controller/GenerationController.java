package com.creatorstudio.controller;

import com.creatorstudio.dto.GenerationResponse;
import com.creatorstudio.dto.ReelGenerationRequest;
import com.creatorstudio.dto.StoryGenerationRequest;
import com.creatorstudio.entity.Generation;
import com.creatorstudio.entity.User;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.GenerationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/generate")
public class GenerationController {

    @Autowired
    private GenerationService generationService;

    @Autowired
    private AuthService authService;

    @PostMapping("/reel")
    public ResponseEntity<GenerationResponse> generateReel(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody ReelGenerationRequest request) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(generationService.generateReel(user.getId(), request));
    }

    @PostMapping("/story")
    public ResponseEntity<GenerationResponse> generateStory(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody StoryGenerationRequest request) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(generationService.generateStory(user.getId(), request));
    }

    @GetMapping("/generations/{id}")
    public ResponseEntity<Generation> getGeneration(@PathVariable UUID id) {
        return ResponseEntity.ok(generationService.getGeneration(id));
    }

    @GetMapping("/generations")
    public ResponseEntity<Page<Generation>> getGenerations(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(required = false) String type,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(generationService.getUserGenerations(user.getId(), type, PageRequest.of(page, size)));
    }
}