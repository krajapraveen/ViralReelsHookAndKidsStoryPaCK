package com.creatorstudio.exception;

/**
 * Exception thrown when webhook processing fails
 */
public class WebhookProcessingException extends PaymentException {
    
    public WebhookProcessingException(String event, String message, Throwable cause) {
        super("WEBHOOK_PROCESSING_FAILED", 
              String.format("Failed to process webhook event '%s': %s", event, message),
              "Webhook processing failed.", 
              cause);
    }
    
    public WebhookProcessingException(String message) {
        super("WEBHOOK_PROCESSING_FAILED", message, "Webhook processing failed.");
    }
}
