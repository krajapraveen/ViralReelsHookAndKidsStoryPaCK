package com.creatorstudio.exception;

/**
 * Exception when circuit breaker is open
 */
public class ServiceCircuitBreakerOpenException extends RuntimeException {
    private final String serviceName;
    
    public ServiceCircuitBreakerOpenException(String serviceName) {
        super("Service " + serviceName + " is temporarily unavailable. Please try again later.");
        this.serviceName = serviceName;
    }
    
    public String getServiceName() { return serviceName; }
}
