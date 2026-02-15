package com.creatorstudio.exception;

/**
 * Exception thrown when Razorpay signature validation fails
 */
public class InvalidSignatureException extends PaymentException {
    
    public InvalidSignatureException(String message) {
        super("INVALID_SIGNATURE", message, "Payment signature verification failed. This may indicate a security issue.");
    }
    
    public InvalidSignatureException(String orderId, String paymentId) {
        super("INVALID_SIGNATURE", 
              String.format("Invalid signature for order: %s, payment: %s", orderId, paymentId),
              "Payment signature verification failed. Please contact support.");
    }
}
