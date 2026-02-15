package com.creatorstudio.service;

import com.creatorstudio.entity.CreditLedger;
import com.creatorstudio.entity.Payment;
import com.creatorstudio.entity.Product;
import com.creatorstudio.entity.User;
import com.creatorstudio.exception.*;
import com.creatorstudio.repository.PaymentRepository;
import com.creatorstudio.repository.ProductRepository;
import com.razorpay.Order;
import com.razorpay.RazorpayClient;
import com.razorpay.RazorpayException;
import com.razorpay.Utils;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.function.Supplier;

@Service
public class PaymentService {

    private static final Logger logger = LoggerFactory.getLogger(PaymentService.class);

    @Autowired
    private PaymentRepository paymentRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CreditService creditService;

    @Autowired
    private EmailService emailService;

    @Autowired
    private CurrencyService currencyService;

    @Autowired
    private CircuitBreakerRegistry circuitBreakerRegistry;

    @Value("${razorpay.key.id}")
    private String razorpayKeyId;

    @Value("${razorpay.key.secret}")
    private String razorpayKeySecret;

    @Value("${razorpay.webhook.secret}")
    private String webhookSecret;

    // Supported international currencies for Razorpay
    private static final Set<String> RAZORPAY_SUPPORTED_CURRENCIES = Set.of(
            "INR", "USD", "EUR", "GBP", "SGD", "AED", "AUD", "CAD", "MYR"
    );

    // Retry configuration
    private static final int MAX_RETRIES = 3;
    private static final long RETRY_DELAY_MS = 1000;

    @Cacheable(value = "products")
    public List<Product> getProducts() {
        logger.debug("Fetching all active products");
        return productRepository.findByActiveTrue();
    }

    /**
     * Get supported currencies for international payments
     */
    public List<Map<String, Object>> getSupportedCurrencies() {
        return currencyService.getSupportedCurrencies();
    }

    /**
     * Create a Razorpay order with international currency support
     */
    @Transactional
    public Map<String, Object> createInternationalOrder(UUID userId, Long productId, String currency) {
        logger.info("Creating international order for user {} and product {} in {}", userId, productId, currency);
        
        // Validate currency
        if (currency == null || currency.isEmpty()) {
            currency = "INR";
        }
        currency = currency.toUpperCase();
        
        if (!RAZORPAY_SUPPORTED_CURRENCIES.contains(currency)) {
            throw new RazorpayOrderException("Currency " + currency + " is not supported. Supported currencies: " + RAZORPAY_SUPPORTED_CURRENCIES);
        }

        // Validate product exists
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new ProductNotFoundException(productId));

        if (!product.isActive()) {
            throw new ProductNotFoundException(productId);
        }

        if (product.getPriceInr() == null || product.getPriceInr().compareTo(BigDecimal.ZERO) <= 0) {
            throw new RazorpayOrderException("Invalid product price configuration");
        }

        // Convert price to target currency
        BigDecimal priceInTargetCurrency = currencyService.convertFromINR(product.getPriceInr(), currency);
        
        // Use circuit breaker for Razorpay calls
        CircuitBreaker circuitBreaker = circuitBreakerRegistry.circuitBreaker("razorpay");
        
        Supplier<Order> orderSupplier = CircuitBreaker.decorateSupplier(circuitBreaker, () -> {
            try {
                RazorpayClient client = createRazorpayClient();
                return createOrderWithCurrency(client, product, currency, priceInTargetCurrency);
            } catch (RazorpayException e) {
                throw new RazorpayOrderException("Failed to create order", e);
            }
        });

        Order order;
        try {
            order = orderSupplier.get();
        } catch (Exception e) {
            logger.error("Circuit breaker prevented order creation: {}", e.getMessage());
            throw new RazorpayConnectionException("Payment service temporarily unavailable. Please try again.", e);
        }

        // Save payment record
        Payment payment = savePaymentRecord(userId, product, order, currency, priceInTargetCurrency);

        logger.info("International order created: {} in {} for user {}", order.get("id"), currency, userId);

        String currencySymbol = currencyService.getCurrencySymbol(currency);
        
        return Map.of(
                "orderId", order.get("id"),
                "amount", order.get("amount"),
                "currency", currency,
                "currencySymbol", currencySymbol,
                "displayAmount", currencySymbol + priceInTargetCurrency.setScale(2, RoundingMode.HALF_UP),
                "amountInINR", product.getPriceInr(),
                "keyId", razorpayKeyId,
                "productName", product.getName(),
                "productCredits", product.getCredits(),
                "exchangeRate", currencyService.getExchangeRate("INR", currency)
        );
    }

    /**
     * Create order with specific currency
     */
    private Order createOrderWithCurrency(RazorpayClient client, Product product, String currency, BigDecimal amount) throws RazorpayException {
        JSONObject options = new JSONObject();
        
        // Amount in smallest currency unit (paise for INR, cents for USD, etc.)
        int amountInSmallestUnit = amount.multiply(new BigDecimal("100")).intValue();
        
        options.put("amount", amountInSmallestUnit);
        options.put("currency", currency);
        options.put("receipt", "rcpt_" + System.currentTimeMillis());
        options.put("notes", new JSONObject()
                .put("product_id", product.getId())
                .put("product_name", product.getName())
                .put("original_currency", "INR")
                .put("original_amount", product.getPriceInr())
        );

        return client.orders.create(options);
    }

    /**
     * Create a Razorpay order with comprehensive error handling (INR default)
     */
    @Transactional
    public Map<String, Object> createOrder(UUID userId, Long productId) {
        return createInternationalOrder(userId, productId, "INR");
    }

    /**
     * Legacy createOrder method - delegates to international version
     */
    @Transactional
    public Map<String, Object> createOrderLegacy(UUID userId, Long productId) {
        logger.info("Creating order for user {} and product {}", userId, productId);
        
        // Validate product exists
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new ProductNotFoundException(productId));

        // Validate product is active
        if (!product.isActive()) {
            throw new ProductNotFoundException(productId);
        }

        // Validate price
        if (product.getPriceInr() == null || product.getPriceInr().compareTo(BigDecimal.ZERO) <= 0) {
            logger.error("Invalid product price for product {}: {}", productId, product.getPriceInr());
            throw new RazorpayOrderException("Invalid product price configuration");
        }

        RazorpayClient client;
        try {
            client = createRazorpayClient();
        } catch (RazorpayException e) {
            logger.error("Failed to initialize Razorpay client: {}", e.getMessage());
            throw new RazorpayConnectionException("Failed to initialize payment gateway", e);
        }

        // Create order with retry logic
        Order order = createOrderWithRetry(client, product);

        // Save payment record
        Payment payment = savePaymentRecord(userId, product, order);

        logger.info("Order created successfully: {} for user {}", order.get("id"), userId);

        return Map.of(
                "orderId", order.get("id"),
                "amount", order.get("amount"),
                "currency", order.get("currency"),
                "keyId", razorpayKeyId,
                "productName", product.getName(),
                "productCredits", product.getCredits()
        );
    }

    /**
     * Verify payment with comprehensive validation
     */
    @Transactional
    public Map<String, Object> verifyPayment(String orderId, String paymentId, String signature) {
        logger.info("Verifying payment - Order: {}, Payment: {}", orderId, paymentId);

        // Validate input parameters
        validatePaymentParams(orderId, paymentId, signature);

        // Find payment record
        Payment payment = paymentRepository.findByProviderOrderId(orderId)
                .orElseThrow(() -> new PaymentNotFoundException(orderId));

        // Check if already processed
        if (payment.getStatus() == Payment.Status.PAID) {
            logger.warn("Payment already processed: {}", orderId);
            throw new PaymentAlreadyProcessedException(orderId, payment.getStatus().toString());
        }

        // Verify signature
        boolean isValid = verifySignature(orderId, paymentId, signature);

        if (!isValid) {
            logger.error("Invalid payment signature for order: {}", orderId);
            payment.setStatus(Payment.Status.FAILED);
            payment.setProviderPaymentId(paymentId);
            paymentRepository.save(payment);
            throw new InvalidSignatureException(orderId, paymentId);
        }

        // Update payment record
        payment.setProviderPaymentId(paymentId);
        payment.setProviderSignature(signature);
        payment.setStatus(Payment.Status.PAID);
        paymentRepository.save(payment);

        // Add credits to user
        try {
            creditService.addCredits(
                    payment.getUser().getId(),
                    BigDecimal.valueOf(payment.getProduct().getCredits()),
                    CreditLedger.Reason.PURCHASE,
                    payment.getId().toString()
            );
            logger.info("Credits added successfully for user: {}", payment.getUser().getId());
        } catch (Exception e) {
            logger.error("Failed to add credits for payment {}: {}", payment.getId(), e.getMessage());
            // Don't throw - payment is successful, credits can be added manually if needed
        }

        // Send confirmation email
        try {
            sendPaymentConfirmationEmail(payment, paymentId);
        } catch (Exception e) {
            logger.error("Failed to send payment confirmation email: {}", e.getMessage());
            // Don't throw - email failure shouldn't affect payment success
        }

        logger.info("Payment verified successfully: {}", paymentId);

        return Map.of(
                "status", "success",
                "paymentId", paymentId,
                "credits", payment.getProduct().getCredits(),
                "message", "Payment successful! Credits have been added to your account."
        );
    }

    /**
     * Process webhook events with proper error handling
     */
    @Transactional
    public void processWebhookEvent(String event, JSONObject webhookData) {
        logger.info("Processing webhook event: {}", event);

        try {
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
                case "subscription.charged":
                    handleSubscriptionCharged(webhookData);
                    break;
                case "subscription.cancelled":
                    handleSubscriptionCancelled(webhookData);
                    break;
                case "refund.created":
                    handleRefundCreated(webhookData);
                    break;
                default:
                    logger.info("Unhandled webhook event: {}", event);
            }
        } catch (Exception e) {
            logger.error("Error processing webhook event {}: {}", event, e.getMessage());
            throw new WebhookProcessingException(event, e.getMessage(), e);
        }
    }

    public Page<Payment> getUserPayments(UUID userId, Pageable pageable) {
        return paymentRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    @Transactional
    public void markPaymentFailed(String orderId) {
        paymentRepository.findByProviderOrderId(orderId).ifPresent(payment -> {
            if (payment.getStatus() != Payment.Status.PAID) {
                payment.setStatus(Payment.Status.FAILED);
                paymentRepository.save(payment);
                logger.info("Payment marked as failed: {}", orderId);
            }
        });
    }

    // ==================== Private Helper Methods ====================

    private RazorpayClient createRazorpayClient() throws RazorpayException {
        if (razorpayKeyId == null || razorpayKeyId.isEmpty()) {
            throw new RazorpayException("Razorpay Key ID not configured");
        }
        if (razorpayKeySecret == null || razorpayKeySecret.isEmpty()) {
            throw new RazorpayException("Razorpay Key Secret not configured");
        }
        return new RazorpayClient(razorpayKeyId, razorpayKeySecret);
    }

    private Order createOrderWithRetry(RazorpayClient client, Product product) {
        int attempts = 0;
        Exception lastException = null;

        while (attempts < MAX_RETRIES) {
            try {
                JSONObject options = new JSONObject();
                options.put("amount", product.getPriceInr().multiply(new BigDecimal("100")).intValue());
                options.put("currency", "INR");
                options.put("receipt", "rcpt_" + System.currentTimeMillis());
                options.put("notes", new JSONObject()
                        .put("product_id", product.getId())
                        .put("product_name", product.getName())
                );

                return client.orders.create(options);
            } catch (RazorpayException e) {
                lastException = e;
                attempts++;
                logger.warn("Order creation attempt {} failed: {}", attempts, e.getMessage());

                if (attempts < MAX_RETRIES) {
                    try {
                        Thread.sleep(RETRY_DELAY_MS * attempts);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }

        logger.error("All {} order creation attempts failed", MAX_RETRIES);
        throw new RazorpayOrderException("Failed to create order after " + MAX_RETRIES + " attempts", lastException);
    }

    private Payment savePaymentRecord(UUID userId, Product product, Order order) {
        return savePaymentRecord(userId, product, order, "INR", product.getPriceInr());
    }

    private Payment savePaymentRecord(UUID userId, Product product, Order order, String currency, BigDecimal amount) {
        Payment payment = new Payment();
        payment.setUser(new User());
        payment.getUser().setId(userId);
        payment.setProduct(product);
        payment.setAmountInr(product.getPriceInr()); // Always store INR equivalent
        payment.setCurrency(currency);
        payment.setAmountInCurrency(amount);
        payment.setProviderOrderId(order.get("id"));
        payment.setStatus(Payment.Status.CREATED);
        return paymentRepository.save(payment);
    }

    private void validatePaymentParams(String orderId, String paymentId, String signature) {
        if (orderId == null || orderId.trim().isEmpty()) {
            throw new RazorpayVerificationException("Order ID is required");
        }
        if (paymentId == null || paymentId.trim().isEmpty()) {
            throw new RazorpayVerificationException("Payment ID is required");
        }
        if (signature == null || signature.trim().isEmpty()) {
            throw new RazorpayVerificationException("Signature is required");
        }
    }

    private boolean verifySignature(String orderId, String paymentId, String signature) {
        try {
            JSONObject options = new JSONObject();
            options.put("razorpay_order_id", orderId);
            options.put("razorpay_payment_id", paymentId);
            options.put("razorpay_signature", signature);
            return Utils.verifyPaymentSignature(options, razorpayKeySecret);
        } catch (RazorpayException e) {
            logger.error("Signature verification error: {}", e.getMessage());
            return false;
        }
    }

    private void sendPaymentConfirmationEmail(Payment payment, String paymentId) {
        User user = payment.getUser();
        emailService.sendPaymentSuccessEmail(
                user.getEmail(),
                user.getName(),
                payment.getProduct().getName(),
                payment.getAmountInr(),
                payment.getProduct().getCredits(),
                paymentId
        );
    }

    private void handlePaymentCaptured(JSONObject webhookData) {
        JSONObject paymentEntity = webhookData.getJSONObject("payload")
                .getJSONObject("payment")
                .getJSONObject("entity");

        String orderId = paymentEntity.getString("order_id");
        String paymentId = paymentEntity.getString("id");

        logger.info("Webhook: Payment captured - Order: {}, Payment: {}", orderId, paymentId);

        // This is a backup - primary verification happens in frontend callback
        paymentRepository.findByProviderOrderId(orderId).ifPresent(payment -> {
            if (payment.getStatus() == Payment.Status.CREATED) {
                logger.info("Updating payment status via webhook for order: {}", orderId);
                payment.setProviderPaymentId(paymentId);
                payment.setStatus(Payment.Status.PAID);
                paymentRepository.save(payment);

                // Add credits if not already added
                try {
                    creditService.addCredits(
                            payment.getUser().getId(),
                            BigDecimal.valueOf(payment.getProduct().getCredits()),
                            CreditLedger.Reason.PURCHASE,
                            payment.getId().toString()
                    );
                } catch (Exception e) {
                    logger.warn("Credits may have already been added: {}", e.getMessage());
                }
            }
        });
    }

    private void handlePaymentFailed(JSONObject webhookData) {
        JSONObject paymentEntity = webhookData.getJSONObject("payload")
                .getJSONObject("payment")
                .getJSONObject("entity");

        String orderId = paymentEntity.getString("order_id");
        String errorCode = paymentEntity.has("error_code") ? paymentEntity.getString("error_code") : "unknown";
        String errorDescription = paymentEntity.has("error_description") ? paymentEntity.getString("error_description") : "";

        logger.warn("Webhook: Payment failed - Order: {}, Error: {} - {}", orderId, errorCode, errorDescription);

        markPaymentFailed(orderId);
    }

    private void handleOrderPaid(JSONObject webhookData) {
        JSONObject orderEntity = webhookData.getJSONObject("payload")
                .getJSONObject("order")
                .getJSONObject("entity");

        String orderId = orderEntity.getString("id");
        logger.info("Webhook: Order paid - Order: {}", orderId);
    }

    private void handleSubscriptionCharged(JSONObject webhookData) {
        logger.info("Webhook: Subscription charged event received");
        // TODO: Implement subscription renewal logic
    }

    private void handleSubscriptionCancelled(JSONObject webhookData) {
        logger.info("Webhook: Subscription cancelled event received");
        // TODO: Implement subscription cancellation logic
    }

    private void handleRefundCreated(JSONObject webhookData) {
        logger.info("Webhook: Refund created event received");
        // TODO: Implement refund handling logic
    }
}
