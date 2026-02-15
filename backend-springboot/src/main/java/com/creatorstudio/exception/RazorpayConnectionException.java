package com.creatorstudio.exception;

/**
 * Exception thrown when connection to Razorpay fails
 */
public class RazorpayConnectionException extends PaymentException {
    
    public RazorpayConnectionException(String message, Throwable cause) {
        super("RAZORPAY_CONNECTION_ERROR", 
              message,
              "Unable to connect to payment gateway. Please try again in a few moments.", 
              cause);
    }
}
