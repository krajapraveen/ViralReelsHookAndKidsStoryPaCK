package com.creatorstudio.exception;

/**
 * Exception for payment order creation failures
 */
public class PaymentOrderCreationException extends PaymentException {
    public PaymentOrderCreationException(String message) {
        super("PAYMENT_ORDER_CREATION_FAILED", message, "Unable to create payment order. Please try again.");
    }
    public PaymentOrderCreationException(String message, Throwable cause) {
        super("PAYMENT_ORDER_CREATION_FAILED", message, "Unable to create payment order. Please try again.", cause);
    }
}
