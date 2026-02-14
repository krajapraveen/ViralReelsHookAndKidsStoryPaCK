package com.creatorstudio.controller;

import com.creatorstudio.dto.CreateOrderRequest;
import com.creatorstudio.dto.VerifyPaymentRequest;
import com.creatorstudio.entity.Payment;
import com.creatorstudio.entity.Product;
import com.creatorstudio.entity.User;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.PaymentService;
import com.razorpay.RazorpayException;
import org.springframework.beans.factory.annotation.Autowired;
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

    @GetMapping("/history")
    public ResponseEntity<Page<Payment>> getPaymentHistory(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(paymentService.getUserPayments(user.getId(), PageRequest.of(page, size)));
    }
}