package com.creatorstudio.controller;

import com.creatorstudio.dto.CreateOrderRequest;
import com.creatorstudio.dto.VerifyPaymentRequest;
import com.creatorstudio.entity.Payment;
import com.creatorstudio.entity.Product;
import com.creatorstudio.entity.User;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.PaymentService;
import com.razorpay.RazorpayException;
import com.razorpay.Utils;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

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

    @GetMapping("/products")
    public ResponseEntity<List<Product>> getProducts() {
        return ResponseEntity.ok(paymentService.getProducts());
    }

    @PostMapping("/create-order")
    public ResponseEntity<Map<String, Object>> createOrder(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody CreateOrderRequest request) throws RazorpayException {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(paymentService.createOrder(user.getId(), request.getProductId()));
    }

    @PostMapping("/verify")
    public ResponseEntity<Map<String, String>> verifyPayment(
            @RequestBody VerifyPaymentRequest request) throws RazorpayException {
        paymentService.verifyPayment(
                request.getRazorpayOrderId(),
                request.getRazorpayPaymentId(),
                request.getRazorpaySignature()
        );
        return ResponseEntity.ok(Map.of("status", "success"));
    }

    @PostMapping("/webhook")
    public ResponseEntity<Map<String, String>> handleWebhook(
            @RequestBody String payload,
            @RequestHeader("X-Razorpay-Signature") String signature) {
        
        logger.info("Received Razorpay webhook");
        
        try {
            // Verify webhook signature
            boolean isValid = Utils.verifyWebhookSignature(payload, signature, webhookSecret);
            
            if (!isValid) {
                logger.warn("Invalid webhook signature");
                return ResponseEntity.badRequest().body(Map.of("status", "invalid_signature"));
            }

            JSONObject webhookData = new JSONObject(payload);
            String event = webhookData.getString("event");
            
            logger.info("Webhook event: {}", event);

            switch (event) {
                case "payment.captured":
                    handlePaymentCaptured(webhookData);
                    break;
                case "payment.failed":
                    handlePaymentFailed(webhookData);
                    break;
                case "order.paid":
                    handleOrderPaid(webhookData);
                    break;
                default:
                    logger.info("Unhandled webhook event: {}", event);
            }

            return ResponseEntity.ok(Map.of("status", "success"));
        } catch (Exception e) {
            logger.error("Webhook processing error: {}", e.getMessage());
            return ResponseEntity.ok(Map.of("status", "error", "message", e.getMessage()));
        }
    }

    private void handlePaymentCaptured(JSONObject webhookData) {
        try {
            JSONObject paymentEntity = webhookData.getJSONObject("payload")
                    .getJSONObject("payment")
                    .getJSONObject("entity");
            
            String orderId = paymentEntity.getString("order_id");
            String paymentId = paymentEntity.getString("id");
            
            logger.info("Payment captured - Order: {}, Payment: {}", orderId, paymentId);
            
            // Note: Payment verification is typically done in the frontend callback
            // This webhook is for backup/reconciliation
        } catch (Exception e) {
            logger.error("Error processing payment.captured: {}", e.getMessage());
        }
    }

    private void handlePaymentFailed(JSONObject webhookData) {
        try {
            JSONObject paymentEntity = webhookData.getJSONObject("payload")
                    .getJSONObject("payment")
                    .getJSONObject("entity");
            
            String orderId = paymentEntity.getString("order_id");
            String errorCode = paymentEntity.optJSONObject("error_code") != null 
                    ? paymentEntity.getString("error_code") : "unknown";
            
            logger.warn("Payment failed - Order: {}, Error: {}", orderId, errorCode);
            
            paymentService.markPaymentFailed(orderId);
        } catch (Exception e) {
            logger.error("Error processing payment.failed: {}", e.getMessage());
        }
    }

    private void handleOrderPaid(JSONObject webhookData) {
        try {
            JSONObject orderEntity = webhookData.getJSONObject("payload")
                    .getJSONObject("order")
                    .getJSONObject("entity");
            
            String orderId = orderEntity.getString("id");
            
            logger.info("Order paid - Order: {}", orderId);
        } catch (Exception e) {
            logger.error("Error processing order.paid: {}", e.getMessage());
        }
    }

    @GetMapping("/history")
    public ResponseEntity<Page<Payment>> getPaymentHistory(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(paymentService.getUserPayments(user.getId(), PageRequest.of(page, size)));
    }
}