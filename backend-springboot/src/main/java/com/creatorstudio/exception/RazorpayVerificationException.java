package com.creatorstudio.exception;

/**
 * Exception thrown when payment verification fails
 */
public class RazorpayVerificationException extends PaymentException {
    
    public RazorpayVerificationException(String message) {
        super("VERIFICATION_FAILED", message, "Payment verification failed. Please contact support if amount was deducted.");
    }
    
    public RazorpayVerificationException(String message, Throwable cause) {
        super("VERIFICATION_FAILED", message, "Payment verification failed. Please contact support if amount was deducted.", cause);
    }
}
