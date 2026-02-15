package com.creatorstudio.exception;

/**
 * Exception thrown when Razorpay order creation fails
 */
public class RazorpayOrderException extends PaymentException {
    
    public RazorpayOrderException(String message) {
        super("ORDER_CREATION_FAILED", message, "Unable to create payment order. Please try again.");
    }
    
    public RazorpayOrderException(String message, Throwable cause) {
        super("ORDER_CREATION_FAILED", message, "Unable to create payment order. Please try again.", cause);
    }
}
