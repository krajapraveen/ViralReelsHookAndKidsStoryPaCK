package com.creatorstudio.config;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import io.github.resilience4j.retry.RetryRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Resilience configuration for fault tolerance and service reliability
 */
@Configuration
public class ResilienceConfig {

    /**
     * Circuit Breaker for Razorpay API calls
     * - Opens after 5 failures in 10 calls
     * - Stays open for 30 seconds before half-open
     * - Prevents cascading failures
     */
    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        CircuitBreakerConfig razorpayConfig = CircuitBreakerConfig.custom()
                .failureRateThreshold(50) // Open circuit if 50% of calls fail
                .slowCallRateThreshold(80) // Open if 80% of calls are slow
                .slowCallDurationThreshold(Duration.ofSeconds(10))
                .waitDurationInOpenState(Duration.ofSeconds(30))
                .permittedNumberOfCallsInHalfOpenState(3)
                .minimumNumberOfCalls(5)
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(10)
                .build();

        CircuitBreakerConfig aiServiceConfig = CircuitBreakerConfig.custom()
                .failureRateThreshold(60)
                .slowCallRateThreshold(90)
                .slowCallDurationThreshold(Duration.ofSeconds(60)) // AI calls can be slow
                .waitDurationInOpenState(Duration.ofSeconds(60))
                .permittedNumberOfCallsInHalfOpenState(2)
                .minimumNumberOfCalls(3)
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(10)
                .build();

        CircuitBreakerConfig rabbitMqConfig = CircuitBreakerConfig.custom()
                .failureRateThreshold(70)
                .waitDurationInOpenState(Duration.ofSeconds(15))
                .permittedNumberOfCallsInHalfOpenState(5)
                .minimumNumberOfCalls(5)
                .build();

        return CircuitBreakerRegistry.of(java.util.Map.of(
                "razorpay", razorpayConfig,
                "aiService", aiServiceConfig,
                "rabbitMq", rabbitMqConfig
        ));
    }

    @Bean
    public CircuitBreaker razorpayCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker("razorpay");
    }

    @Bean
    public CircuitBreaker aiServiceCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker("aiService");
    }

    @Bean
    public CircuitBreaker rabbitMqCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker("rabbitMq");
    }

    /**
     * Retry configuration for transient failures
     */
    @Bean
    public RetryRegistry retryRegistry() {
        RetryConfig razorpayRetryConfig = RetryConfig.custom()
                .maxAttempts(3)
                .waitDuration(Duration.ofMillis(1000))
                .retryExceptions(java.net.SocketTimeoutException.class, 
                                 java.net.ConnectException.class,
                                 java.io.IOException.class)
                .build();

        RetryConfig rabbitMqRetryConfig = RetryConfig.custom()
                .maxAttempts(5)
                .waitDuration(Duration.ofMillis(500))
                .build();

        return RetryRegistry.of(java.util.Map.of(
                "razorpay", razorpayRetryConfig,
                "rabbitMq", rabbitMqRetryConfig
        ));
    }

    @Bean
    public Retry razorpayRetry(RetryRegistry registry) {
        return registry.retry("razorpay");
    }

    @Bean
    public Retry rabbitMqRetry(RetryRegistry registry) {
        return registry.retry("rabbitMq");
    }
}
