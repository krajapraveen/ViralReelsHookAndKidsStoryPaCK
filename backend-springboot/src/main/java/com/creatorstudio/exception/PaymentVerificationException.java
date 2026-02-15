package com.creatorstudio.exception;

/**
 * Exception for payment verification failures
 */
public class PaymentVerificationException extends PaymentException {
    public PaymentVerificationException(String message) {
        super("PAYMENT_VERIFICATION_FAILED", message, "Payment verification failed. Please contact support.");
    }
    public PaymentVerificationException(String message, Throwable cause) {
        super("PAYMENT_VERIFICATION_FAILED", message, "Payment verification failed. Please contact support.", cause);
    }
}
