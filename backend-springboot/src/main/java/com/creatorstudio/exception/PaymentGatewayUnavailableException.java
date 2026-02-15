package com.creatorstudio.exception;

/**
 * Exception when Razorpay gateway is unavailable
 */
public class PaymentGatewayUnavailableException extends PaymentException {
    public PaymentGatewayUnavailableException(String message) {
        super(message, "PAYMENT_GATEWAY_UNAVAILABLE");
    }
    public PaymentGatewayUnavailableException(String message, Throwable cause) {
        super(message, "PAYMENT_GATEWAY_UNAVAILABLE", cause);
    }
}
