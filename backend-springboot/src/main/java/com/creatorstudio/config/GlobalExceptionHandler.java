package com.creatorstudio.config;

import com.creatorstudio.exception.*;
import com.razorpay.RazorpayException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.net.SocketTimeoutException;
import java.net.ConnectException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    // ==================== Payment Exception Handlers ====================

    /**
     * Handle base PaymentException and all its subclasses
     */
    @ExceptionHandler(PaymentException.class)
    public ResponseEntity<Map<String, Object>> handlePaymentException(PaymentException ex) {
        logger.error("Payment Exception [{}]: {}", ex.getErrorCode(), ex.getMessage(), ex);
        
        Map<String, Object> error = new HashMap<>();
        error.put("success", false);
        error.put("errorCode", ex.getErrorCode());
        error.put("error", ex.getUserMessage());
        error.put("message", ex.getMessage());
        error.put("timestamp", LocalDateTime.now().toString());
        
        HttpStatus status = determinePaymentErrorStatus(ex);
        return ResponseEntity.status(status).body(error);
    }

    /**
     * Handle Razorpay SDK exceptions
     */
    @ExceptionHandler(RazorpayException.class)
    public ResponseEntity<Map<String, Object>> handleRazorpayException(RazorpayException ex) {
        logger.error("Razorpay SDK Exception: {}", ex.getMessage(), ex);
        
        Map<String, Object> error = new HashMap<>();
        error.put("success", false);
        error.put("errorCode", "RAZORPAY_ERROR");
        error.put("error", "Payment gateway error. Please try again.");
        error.put("message", sanitizeRazorpayMessage(ex.getMessage()));
        error.put("timestamp", LocalDateTime.now().toString());
        
        // Provide helpful suggestions based on error type
        String suggestion = getRazorpaySuggestion(ex.getMessage());
        if (suggestion != null) {
            error.put("suggestion", suggestion);
        }
        
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(error);
    }

    /**
     * Handle connection/network timeouts
     */
    @ExceptionHandler({SocketTimeoutException.class, ConnectException.class})
    public ResponseEntity<Map<String, Object>> handleNetworkException(Exception ex) {
        logger.error("Network Exception: {}", ex.getMessage(), ex);
        
        Map<String, Object> error = new HashMap<>();
        error.put("success", false);
        error.put("errorCode", "NETWORK_ERROR");
        error.put("error", "Unable to connect to payment gateway. Please check your internet connection and try again.");
        error.put("message", "Connection timeout or network error");
        error.put("timestamp", LocalDateTime.now().toString());
        error.put("retryable", true);
        
        return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT).body(error);
    }

    // ==================== Validation Exception Handlers ====================

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidationExceptions(MethodArgumentNotValidException ex) {
        Map<String, Object> errors = new HashMap<>();
        errors.put("success", false);
        errors.put("errorCode", "VALIDATION_ERROR");
        errors.put("error", "Validation failed");
        
        Map<String, String> fieldErrors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach((error) -> {
            String fieldName = ((FieldError) error).getField();
            String errorMessage = error.getDefaultMessage();
            fieldErrors.put(fieldName, errorMessage);
        });
        
        errors.put("fields", fieldErrors);
        errors.put("timestamp", LocalDateTime.now().toString());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errors);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, Object>> handleJsonParseException(HttpMessageNotReadableException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("success", false);
        error.put("errorCode", "INVALID_JSON");
        error.put("error", "Invalid JSON format");
        error.put("message", "Please provide valid JSON in the request body");
        error.put("timestamp", LocalDateTime.now().toString());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    // ==================== Generic Exception Handlers ====================

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, Object>> handleRuntimeException(RuntimeException ex) {
        logger.error("RuntimeException: {}", ex.getMessage(), ex);
        Map<String, Object> error = new HashMap<>();
        error.put("success", false);
        error.put("errorCode", "REQUEST_FAILED");
        error.put("error", "Request failed");
        error.put("message", ex.getMessage());
        error.put("timestamp", LocalDateTime.now().toString());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGenericException(Exception ex) {
        logger.error("Generic Exception: {}", ex.getMessage(), ex);
        Map<String, Object> error = new HashMap<>();
        error.put("success", false);
        error.put("errorCode", "INTERNAL_ERROR");
        error.put("error", "Internal server error");
        error.put("message", "An unexpected error occurred. Please try again later.");
        error.put("timestamp", LocalDateTime.now().toString());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }

    // ==================== Helper Methods ====================

    /**
     * Determine appropriate HTTP status based on payment exception type
     */
    private HttpStatus determinePaymentErrorStatus(PaymentException ex) {
        if (ex instanceof InvalidSignatureException) {
            return HttpStatus.FORBIDDEN;
        } else if (ex instanceof ProductNotFoundException || ex instanceof PaymentNotFoundException) {
            return HttpStatus.NOT_FOUND;
        } else if (ex instanceof PaymentAlreadyProcessedException) {
            return HttpStatus.CONFLICT;
        } else if (ex instanceof RazorpayConnectionException) {
            return HttpStatus.GATEWAY_TIMEOUT;
        } else if (ex instanceof RazorpayOrderException || ex instanceof RazorpayVerificationException) {
            return HttpStatus.BAD_GATEWAY;
        } else if (ex instanceof WebhookProcessingException) {
            return HttpStatus.INTERNAL_SERVER_ERROR;
        }
        return HttpStatus.BAD_REQUEST;
    }

    /**
     * Sanitize Razorpay error messages to remove sensitive information
     */
    private String sanitizeRazorpayMessage(String message) {
        if (message == null) return "Unknown error";
        
        // Remove API key references
        message = message.replaceAll("rzp_[a-zA-Z0-9_]+", "[REDACTED]");
        
        // Remove any potential sensitive data patterns
        message = message.replaceAll("key_id.*?[,}]", "[REDACTED]");
        
        return message;
    }

    /**
     * Provide helpful suggestions based on Razorpay error
     */
    private String getRazorpaySuggestion(String message) {
        if (message == null) return null;
        
        String lowerMessage = message.toLowerCase();
        
        if (lowerMessage.contains("authentication") || lowerMessage.contains("unauthorized")) {
            return "Please contact support - there may be an issue with payment configuration.";
        } else if (lowerMessage.contains("invalid") && lowerMessage.contains("amount")) {
            return "Please refresh the page and try selecting the product again.";
        } else if (lowerMessage.contains("order") && lowerMessage.contains("expired")) {
            return "Your payment session has expired. Please start a new purchase.";
        } else if (lowerMessage.contains("insufficient") || lowerMessage.contains("balance")) {
            return "Please ensure you have sufficient funds in your account.";
        } else if (lowerMessage.contains("card") && lowerMessage.contains("declined")) {
            return "Your card was declined. Please try a different payment method.";
        } else if (lowerMessage.contains("timeout")) {
            return "The request timed out. Please check your connection and try again.";
        }
        
        return "Please try again or contact support if the issue persists.";
    }
}
