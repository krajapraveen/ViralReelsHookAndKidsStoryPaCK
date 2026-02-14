package com.creatorstudio.controller;

import com.creatorstudio.entity.Generation;
import com.creatorstudio.entity.Payment;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.GenerationRepository;
import com.creatorstudio.repository.PaymentRepository;
import com.creatorstudio.repository.UserRepository;
import com.creatorstudio.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PaymentRepository paymentRepository;

    @Autowired
    private GenerationRepository generationRepository;

    @Autowired
    private AuthService authService;

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats(@AuthenticationPrincipal UserDetails userDetails) {
        User currentUser = authService.getUserByEmail(userDetails.getUsername());
        
        if (currentUser.getRole() != User.Role.ADMIN) {
            return ResponseEntity.status(403).build();
        }

        Map<String, Object> stats = new HashMap<>();
        stats.put("totalUsers", userRepository.count());
        stats.put("totalGenerations", generationRepository.count());
        stats.put("totalPayments", paymentRepository.count());
        
        long successfulGenerations = generationRepository.findAll().stream()
                .filter(g -> g.getStatus() == Generation.Status.SUCCEEDED)
                .count();
        stats.put("successfulGenerations", successfulGenerations);

        return ResponseEntity.ok(stats);
    }

    @GetMapping("/users")
    public ResponseEntity<Page<User>> getUsers(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        User currentUser = authService.getUserByEmail(userDetails.getUsername());
        if (currentUser.getRole() != User.Role.ADMIN) {
            return ResponseEntity.status(403).build();
        }

        return ResponseEntity.ok(userRepository.findAll(PageRequest.of(page, size)));
    }

    @GetMapping("/payments")
    public ResponseEntity<Page<Payment>> getPayments(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        User currentUser = authService.getUserByEmail(userDetails.getUsername());
        if (currentUser.getRole() != User.Role.ADMIN) {
            return ResponseEntity.status(403).build();
        }

        return ResponseEntity.ok(paymentRepository.findAll(PageRequest.of(page, size)));
    }

    @GetMapping("/generations")
    public ResponseEntity<Page<Generation>> getGenerations(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        User currentUser = authService.getUserByEmail(userDetails.getUsername());
        if (currentUser.getRole() != User.Role.ADMIN) {
            return ResponseEntity.status(403).build();
        }

        return ResponseEntity.ok(generationRepository.findAll(PageRequest.of(page, size)));
    }

    @GetMapping("/generations/failed")
    public ResponseEntity<Page<Generation>> getFailedGenerations(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        User currentUser = authService.getUserByEmail(userDetails.getUsername());
        if (currentUser.getRole() != User.Role.ADMIN) {
            return ResponseEntity.status(403).build();
        }

        Page<Generation> failed = generationRepository.findAll(PageRequest.of(page, size))
                .map(g -> g.getStatus() == Generation.Status.FAILED ? g : null);

        return ResponseEntity.ok(failed);
    }
}
