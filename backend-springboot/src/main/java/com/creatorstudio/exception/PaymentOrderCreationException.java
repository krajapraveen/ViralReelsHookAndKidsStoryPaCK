package com.creatorstudio.exception;

/**
 * Comprehensive Payment Exception Hierarchy for Razorpay Integration
 */

// Order Creation Exceptions
public class PaymentOrderCreationException extends PaymentException {
    public PaymentOrderCreationException(String message) {
        super(message, "PAYMENT_ORDER_CREATION_FAILED");
    }
    public PaymentOrderCreationException(String message, Throwable cause) {
        super(message, "PAYMENT_ORDER_CREATION_FAILED", cause);
    }
}
