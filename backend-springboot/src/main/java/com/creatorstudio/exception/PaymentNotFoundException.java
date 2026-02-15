package com.creatorstudio.exception;

/**
 * Exception thrown when a payment record is not found
 */
public class PaymentNotFoundException extends PaymentException {
    
    public PaymentNotFoundException(String orderId) {
        super("PAYMENT_NOT_FOUND", 
              String.format("Payment with order ID %s not found", orderId),
              "Payment record not found. Please contact support if you were charged.");
    }
}
