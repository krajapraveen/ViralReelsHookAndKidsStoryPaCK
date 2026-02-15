package com.creatorstudio.exception;

/**
 * Exception for invalid payment signature
 */
public class PaymentSignatureException extends PaymentException {
    public PaymentSignatureException(String message) {
        super("PAYMENT_SIGNATURE_INVALID", message, "Payment signature verification failed.");
    }
}
