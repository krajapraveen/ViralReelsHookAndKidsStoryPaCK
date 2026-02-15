package com.creatorstudio.service;

import com.creatorstudio.entity.CreditLedger;
import com.creatorstudio.entity.Payment;
import com.creatorstudio.entity.Product;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.PaymentRepository;
import com.creatorstudio.repository.ProductRepository;
import com.razorpay.Order;
import com.razorpay.RazorpayClient;
import com.razorpay.RazorpayException;
import com.razorpay.Utils;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class PaymentService {

    @Autowired
    private PaymentRepository paymentRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CreditService creditService;

    @Autowired
    private EmailService emailService;

    @Value("${razorpay.key.id}")
    private String razorpayKeyId;

    @Value("${razorpay.key.secret}")
    private String razorpayKeySecret;

    @Value("${razorpay.webhook.secret}")
    private String webhookSecret;

    @Cacheable(value = "products")
    public List<Product> getProducts() {
        return productRepository.findByActiveTrue();
    }

    @Transactional
    public Map<String, Object> createOrder(UUID userId, Long productId) throws RazorpayException {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new RuntimeException("Product not found"));

        RazorpayClient client = new RazorpayClient(razorpayKeyId, razorpayKeySecret);

        JSONObject options = new JSONObject();
        options.put("amount", product.getPriceInr().multiply(new BigDecimal("100")).intValue()); // Convert to paise
        options.put("currency", "INR");
        options.put("receipt", "rcpt_" + System.currentTimeMillis());

        Order order = client.orders.create(options);

        // Save payment record
        Payment payment = new Payment();
        payment.setUser(new User());
        payment.getUser().setId(userId);
        payment.setProduct(product);
        payment.setAmountInr(product.getPriceInr());
        payment.setProviderOrderId(order.get("id"));
        payment.setStatus(Payment.Status.CREATED);
        paymentRepository.save(payment);

        return Map.of(
                "orderId", order.get("id"),
                "amount", order.get("amount"),
                "currency", order.get("currency"),
                "keyId", razorpayKeyId
        );
    }

    @Transactional
    public void verifyPayment(String orderId, String paymentId, String signature) throws RazorpayException {
        Payment payment = paymentRepository.findByProviderOrderId(orderId)
                .orElseThrow(() -> new RuntimeException("Payment not found"));

        // Verify signature
        JSONObject options = new JSONObject();
        options.put("razorpay_order_id", orderId);
        options.put("razorpay_payment_id", paymentId);
        options.put("razorpay_signature", signature);

        boolean isValid = Utils.verifyPaymentSignature(options, razorpayKeySecret);

        if (!isValid) {
            payment.setStatus(Payment.Status.FAILED);
            paymentRepository.save(payment);
            throw new RuntimeException("Invalid payment signature");
        }

        // Update payment
        payment.setProviderPaymentId(paymentId);
        payment.setProviderSignature(signature);
        payment.setStatus(Payment.Status.PAID);
        paymentRepository.save(payment);

        // Add credits
        creditService.addCredits(
                payment.getUser().getId(),
                BigDecimal.valueOf(payment.getProduct().getCredits()),
                CreditLedger.Reason.PURCHASE,
                payment.getId().toString()
        );

        // Send success email
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

    public Page<Payment> getUserPayments(UUID userId, Pageable pageable) {
        return paymentRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    @Transactional
    public void markPaymentFailed(String orderId) {
        paymentRepository.findByProviderOrderId(orderId).ifPresent(payment -> {
            payment.setStatus(Payment.Status.FAILED);
            paymentRepository.save(payment);
        });
    }
}
