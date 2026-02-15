package com.creatorstudio.controller;

import com.creatorstudio.dto.CreateOrderRequest;
import com.creatorstudio.dto.VerifyPaymentRequest;
import com.creatorstudio.entity.Payment;
import com.creatorstudio.entity.Product;
import com.creatorstudio.entity.User;
import com.creatorstudio.exception.InvalidSignatureException;
import com.creatorstudio.exception.WebhookProcessingException;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.PaymentService;
import com.razorpay.Utils;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/payments")
public class PaymentController {

    private static final Logger logger = LoggerFactory.getLogger(PaymentController.class);

    @Value("${razorpay.webhook.secret}")
    private String webhookSecret;

    @Autowired
    private PaymentService paymentService;

    @Autowired
    private AuthService authService;

    /**
     * Get all available products
     */
    @GetMapping("/products")
    public ResponseEntity<Map<String, Object>> getProducts() {
        logger.debug("Fetching products");
        try {
            List<Product> products = paymentService.getProducts();
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("products", products);
            response.put("count", products.size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("Error fetching products: {}", e.getMessage());
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", "Failed to fetch products");
            error.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
        }
    }

    /**
     * Get supported currencies for international payments
     */
    @GetMapping("/currencies")
    public ResponseEntity<Map<String, Object>> getSupportedCurrencies() {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("currencies", paymentService.getSupportedCurrencies());
        return ResponseEntity.ok(response);
    }

    /**
     * Create a new Razorpay order with international currency support
     */
    @PostMapping("/create-order")
    public ResponseEntity<Map<String, Object>> createOrder(
            @AuthenticationPrincipal UserDetails userDetails,
            @Valid @RequestBody CreateOrderRequest request) {
        
        String currency = request.getCurrency() != null ? request.getCurrency() : "INR";
        logger.info("Creating order for product: {} in currency: {}", request.getProductId(), currency);
        
        User user = authService.getUserByEmail(userDetails.getUsername());
        Map<String, Object> result = paymentService.createInternationalOrder(
            user.getId(), 
            request.getProductId(),
            currency
        );
        
        Map<String, Object> response = new HashMap<>(result);
        response.put("success", true);
        response.put("message", "Order created successfully");
        
        return ResponseEntity.ok(response);
    }

    /**
     * Verify payment after Razorpay checkout
     */
    @PostMapping("/verify")
    public ResponseEntity<Map<String, Object>> verifyPayment(
            @Valid @RequestBody VerifyPaymentRequest request) {
        
        logger.info("Verifying payment for order: {}", request.getRazorpayOrderId());
        
        Map<String, Object> result = paymentService.verifyPayment(
                request.getRazorpayOrderId(),
                request.getRazorpayPaymentId(),
                request.getRazorpaySignature()
        );
        
        Map<String, Object> response = new HashMap<>(result);
        response.put("success", true);
        
        return ResponseEntity.ok(response);
    }

    /**
     * Handle Razorpay webhooks
     */
    @PostMapping("/webhook")
    public ResponseEntity<Map<String, Object>> handleWebhook(
            @RequestBody String payload,
            @RequestHeader(value = "X-Razorpay-Signature", required = false) String signature) {
        
        logger.info("Received Razorpay webhook");
        Map<String, Object> response = new HashMap<>();
        response.put("timestamp", LocalDateTime.now().toString());

        // Validate signature header
        if (signature == null || signature.trim().isEmpty()) {
            logger.warn("Webhook received without signature header");
            response.put("success", false);
            response.put("error", "Missing signature header");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(response);
        }

        // Verify webhook signature
        try {
            boolean isValid = Utils.verifyWebhookSignature(payload, signature, webhookSecret);
            
            if (!isValid) {
                logger.warn("Invalid webhook signature received");
                response.put("success", false);
                response.put("error", "Invalid signature");
                return ResponseEntity.status(HttpStatus.FORBIDDEN).body(response);
            }
        } catch (Exception e) {
            logger.error("Error verifying webhook signature: {}", e.getMessage());
            response.put("success", false);
            response.put("error", "Signature verification failed");
            return ResponseEntity.status(HttpStatus.FORBIDDEN).body(response);
        }

        // Parse and process webhook
        try {
            JSONObject webhookData = new JSONObject(payload);
            String event = webhookData.getString("event");
            
            logger.info("Processing webhook event: {}", event);
            
            paymentService.processWebhookEvent(event, webhookData);
            
            response.put("success", true);
            response.put("event", event);
            response.put("message", "Webhook processed successfully");
            
            return ResponseEntity.ok(response);
            
        } catch (org.json.JSONException e) {
            logger.error("Invalid webhook JSON payload: {}", e.getMessage());
            response.put("success", false);
            response.put("error", "Invalid JSON payload");
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response);
            
        } catch (WebhookProcessingException e) {
            logger.error("Webhook processing failed: {}", e.getMessage());
            // Return 200 to prevent Razorpay retries for business logic errors
            response.put("success", false);
            response.put("error", e.getUserMessage());
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            logger.error("Unexpected webhook error: {}", e.getMessage(), e);
            // Return 200 to acknowledge receipt even if processing failed
            response.put("success", false);
            response.put("error", "Processing failed");
            response.put("message", e.getMessage());
            return ResponseEntity.ok(response);
        }
    }

    /**
     * Get user's payment history
     */
    @GetMapping("/history")
    public ResponseEntity<Map<String, Object>> getPaymentHistory(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        logger.debug("Fetching payment history for user: {}", userDetails.getUsername());
        
        User user = authService.getUserByEmail(userDetails.getUsername());
        Page<Payment> payments = paymentService.getUserPayments(user.getId(), PageRequest.of(page, size));
        
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("payments", payments.getContent());
        response.put("totalPages", payments.getTotalPages());
        response.put("totalElements", payments.getTotalElements());
        response.put("currentPage", page);
        
        return ResponseEntity.ok(response);
    }

    /**
     * Health check for payment service
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("status", "healthy");
        response.put("timestamp", LocalDateTime.now().toString());
        response.put("service", "payment-gateway");
        return ResponseEntity.ok(response);
    }
}
