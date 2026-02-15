package com.creatorstudio.exception;

/**
 * Exception when payment gateway is unavailable
 */
public class PaymentGatewayUnavailableException extends PaymentException {
    public PaymentGatewayUnavailableException(String message) {
        super("PAYMENT_GATEWAY_UNAVAILABLE", message, "Payment service is temporarily unavailable. Please try again later.");
    }
    public PaymentGatewayUnavailableException(String message, Throwable cause) {
        super("PAYMENT_GATEWAY_UNAVAILABLE", message, "Payment service is temporarily unavailable. Please try again later.", cause);
    }
}
