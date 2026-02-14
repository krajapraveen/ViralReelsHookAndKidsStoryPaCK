package com.creatorstudio.controller;

import com.creatorstudio.entity.CreditLedger;
import com.creatorstudio.entity.User;
import com.creatorstudio.service.AuthService;
import com.creatorstudio.service.CreditService;
import com.creatorstudio.service.GenerationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;

@RestController
@RequestMapping("/api/credits")
public class CreditController {

    @Autowired
    private CreditService creditService;

    @Autowired
    private AuthService authService;

    @Autowired
    private GenerationService generationService;

    @GetMapping("/balance")
    public ResponseEntity<Map<String, Object>> getBalance(@AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        BigDecimal balance = creditService.getBalance(user.getId());
        boolean hasPurchased = generationService.hasUserPurchased(user.getId());
        boolean isFreeTier = !hasPurchased;
        
        return ResponseEntity.ok(Map.of(
            "balance", balance,
            "hasPurchased", hasPurchased,
            "isFreeTier", isFreeTier
        ));
    }

    @GetMapping("/ledger")
    public ResponseEntity<Page<CreditLedger>> getLedger(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        User user = authService.getUserByEmail(userDetails.getUsername());
        return ResponseEntity.ok(creditService.getLedger(user.getId(), PageRequest.of(page, size)));
    }
}