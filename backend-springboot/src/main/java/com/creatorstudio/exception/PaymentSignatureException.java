package com.creatorstudio.exception;

/**
 * Exception for invalid signature during webhook verification
 */
public class PaymentSignatureException extends PaymentException {
    public PaymentSignatureException(String message) {
        super(message, "PAYMENT_SIGNATURE_INVALID");
    }
}
