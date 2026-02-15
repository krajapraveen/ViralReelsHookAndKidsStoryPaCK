package com.creatorstudio.exception;

/**
 * Exception thrown when attempting to process an already processed payment
 */
public class PaymentAlreadyProcessedException extends PaymentException {
    
    public PaymentAlreadyProcessedException(String orderId, String currentStatus) {
        super("PAYMENT_ALREADY_PROCESSED", 
              String.format("Payment for order %s already processed with status: %s", orderId, currentStatus),
              "This payment has already been processed.");
    }
}
