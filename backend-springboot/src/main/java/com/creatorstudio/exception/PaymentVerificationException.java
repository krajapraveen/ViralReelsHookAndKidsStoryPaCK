package com.creatorstudio.exception;

/**
 * Exception for payment verification failures
 */
public class PaymentVerificationException extends PaymentException {
    public PaymentVerificationException(String message) {
        super(message, "PAYMENT_VERIFICATION_FAILED");
    }
    public PaymentVerificationException(String message, Throwable cause) {
        super(message, "PAYMENT_VERIFICATION_FAILED", cause);
    }
}
