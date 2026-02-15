package com.creatorstudio.exception;

/**
 * Base exception for all payment-related errors
 */
public class PaymentException extends RuntimeException {
    
    private final String errorCode;
    private final String userMessage;
    
    public PaymentException(String errorCode, String message, String userMessage) {
        super(message);
        this.errorCode = errorCode;
        this.userMessage = userMessage;
    }
    
    public PaymentException(String errorCode, String message, String userMessage, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.userMessage = userMessage;
    }
    
    public String getErrorCode() {
        return errorCode;
    }
    
    public String getUserMessage() {
        return userMessage;
    }
}
