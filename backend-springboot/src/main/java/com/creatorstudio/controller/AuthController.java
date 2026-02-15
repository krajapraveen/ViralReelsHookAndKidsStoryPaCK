package com.creatorstudio.controller;

import com.creatorstudio.dto.AuthResponse;
import com.creatorstudio.dto.LoginRequest;
import com.creatorstudio.dto.RegisterRequest;
import com.creatorstudio.entity.CreditWallet;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.CreditWalletRepository;
import com.creatorstudio.repository.UserRepository;
import com.creatorstudio.security.JwtUtil;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.CreditService;
import io.github.resilience4j.ratelimiter.annotation.RateLimiter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CreditWalletRepository walletRepository;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private CreditService creditService;
    
    // Simple in-memory rate limiter for login attempts per IP
    private final ConcurrentHashMap<String, AtomicInteger> loginAttempts = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> lastAttemptTime = new ConcurrentHashMap<>();
    private static final int MAX_ATTEMPTS = 5;
    private static final long LOCKOUT_DURATION_MS = 60000; // 1 minute

    @PostMapping("/register")
    @RateLimiter(name = "apiRateLimit")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        return ResponseEntity.ok(authService.register(request));
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request, HttpServletRequest httpRequest) {
        String clientIp = getClientIp(httpRequest);
        
        // Check rate limit
        if (isRateLimited(clientIp)) {
            return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                    .body(Map.of(
                            "success", false,
                            "error", "Too many login attempts. Please try again in 1 minute.",
                            "errorCode", "RATE_LIMIT_EXCEEDED",
                            "retryAfterSeconds", 60
                    ));
        }
        
        try {
            AuthResponse response = authService.login(request);
            // Reset attempts on successful login
            loginAttempts.remove(clientIp);
            lastAttemptTime.remove(clientIp);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            // Increment failed attempts
            incrementFailedAttempts(clientIp);
            throw e;
        }
    }
    
    private String getClientIp(HttpServletRequest request) {
        String xfHeader = request.getHeader("X-Forwarded-For");
        if (xfHeader != null && !xfHeader.isEmpty()) {
            return xfHeader.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
    
    private boolean isRateLimited(String clientIp) {
        Long lastTime = lastAttemptTime.get(clientIp);
        if (lastTime != null && System.currentTimeMillis() - lastTime > LOCKOUT_DURATION_MS) {
            // Reset after lockout period
            loginAttempts.remove(clientIp);
            lastAttemptTime.remove(clientIp);
            return false;
        }
        
        AtomicInteger attempts = loginAttempts.get(clientIp);
        return attempts != null && attempts.get() >= MAX_ATTEMPTS;
    }
    
    private void incrementFailedAttempts(String clientIp) {
        loginAttempts.computeIfAbsent(clientIp, k -> new AtomicInteger(0)).incrementAndGet();
        lastAttemptTime.put(clientIp, System.currentTimeMillis());
    }

    @PostMapping("/google-callback")
    public ResponseEntity<Map<String, Object>> googleCallback(@RequestBody Map<String, String> request) {
        String sessionId = request.get("sessionId");
        
        try {
            // Call Emergent Auth API to get user data
            RestTemplate restTemplate = new RestTemplate();
            HttpHeaders headers = new HttpHeaders();
            headers.set("X-Session-ID", sessionId);
            
            HttpEntity<String> entity = new HttpEntity<>(headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                    HttpMethod.GET,
                    entity,
                    Map.class
            );
            
            Map<String, Object> userData = response.getBody();
            String email = (String) userData.get("email");
            String name = (String) userData.get("name");
            
            // Find or create user
            User user = userRepository.findByEmail(email)
                    .orElseGet(() -> {
                        User newUser = new User();
                        newUser.setEmail(email);
                        newUser.setName(name);
                        newUser.setPasswordHash(""); // No password for OAuth users
                        newUser.setRole(User.Role.USER);
                        newUser = userRepository.save(newUser);
                        
                        // Create wallet with 54 free credits
                        CreditWallet wallet = new CreditWallet();
                        wallet.setUser(newUser);
                        wallet.setBalanceCredits(new BigDecimal("54.00"));
                        walletRepository.save(wallet);
                        
                        // Log credit bonus
                        creditService.addCreditLedgerEntry(newUser.getId(), BigDecimal.valueOf(54), 
                                com.creatorstudio.entity.CreditLedger.Type.CREDIT,
                                com.creatorstudio.entity.CreditLedger.Reason.BONUS, "Welcome bonus");
                        
                        return newUser;
                    });
            
            // Generate JWT token
            String token = jwtUtil.generateToken(user.getEmail());
            
            Map<String, Object> result = new HashMap<>();
            result.put("token", token);
            
            Map<String, Object> userInfo = new HashMap<>();
            userInfo.put("id", user.getId());
            userInfo.put("email", user.getEmail());
            userInfo.put("name", user.getName());
            result.put("user", userInfo);
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            throw new RuntimeException("Google authentication failed: " + e.getMessage());
        }
    }

    @GetMapping("/me")
    public ResponseEntity<Map<String, Object>> getCurrentUser(@AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(Map.of(
                "id", user.getId(),
                "name", user.getName(),
                "email", user.getEmail(),
                "role", user.getRole()
        ));
    }
}