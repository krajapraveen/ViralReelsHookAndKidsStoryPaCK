package com.creatorstudio.service;

import com.creatorstudio.entity.RateLimit;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.RateLimitRepository;
import com.creatorstudio.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.UUID;

@Service
public class RateLimitService {

    private static final int MAX_GENERATIONS_PER_DAY = 50; // Configurable limit

    @Autowired
    private RateLimitRepository rateLimitRepository;

    @Autowired
    private UserRepository userRepository;

    @Transactional
    public void checkAndIncrementRateLimit(UUID userId) {
        LocalDate today = LocalDate.now();
        
        RateLimit rateLimit = rateLimitRepository.findByUserIdAndDate(userId, today)
                .orElseGet(() -> {
                    User user = userRepository.findById(userId)
                            .orElseThrow(() -> new RuntimeException("User not found"));
                    RateLimit newLimit = new RateLimit();
                    newLimit.setUser(user);
                    newLimit.setDate(today);
                    newLimit.setCount(0);
                    return newLimit;
                });

        if (rateLimit.getCount() >= MAX_GENERATIONS_PER_DAY) {
            throw new RuntimeException("Daily generation limit exceeded. Maximum " + MAX_GENERATIONS_PER_DAY + " generations per day.");
        }

        rateLimit.setCount(rateLimit.getCount() + 1);
        rateLimitRepository.save(rateLimit);
    }

    public int getRemainingGenerations(UUID userId) {
        LocalDate today = LocalDate.now();
        RateLimit rateLimit = rateLimitRepository.findByUserIdAndDate(userId, today)
                .orElse(null);
        
        if (rateLimit == null) {
            return MAX_GENERATIONS_PER_DAY;
        }
        
        return Math.max(0, MAX_GENERATIONS_PER_DAY - rateLimit.getCount());
    }
}
