package com.creatorstudio.service;

import com.creatorstudio.dto.AuthResponse;
import com.creatorstudio.dto.LoginRequest;
import com.creatorstudio.dto.RegisterRequest;
import com.creatorstudio.entity.CreditWallet;
import com.creatorstudio.entity.User;
import com.creatorstudio.repository.CreditWalletRepository;
import com.creatorstudio.repository.UserRepository;
import com.creatorstudio.security.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

@Service
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CreditWalletRepository walletRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private AuthenticationManager authenticationManager;

    @Autowired
    private CreditService creditService;

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already exists");
        }

        User user = new User();
        user.setName(request.getName());
        user.setEmail(request.getEmail());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setRole(User.Role.USER);
        user = userRepository.save(user);

        // Create wallet with 5 free credits
        CreditWallet wallet = new CreditWallet();
        wallet.setUser(user);
        wallet.setBalanceCredits(new BigDecimal("5.00"));
        walletRepository.save(wallet);

        // Log credit bonus
        creditService.addCreditLedgerEntry(user.getId(), BigDecimal.valueOf(5), 
                com.creatorstudio.entity.CreditLedger.Type.CREDIT,
                com.creatorstudio.entity.CreditLedger.Reason.BONUS, "Welcome bonus");

        String token = jwtUtil.generateToken(user.getEmail());
        return new AuthResponse(token, user.getEmail(), user.getName());
    }

    public AuthResponse login(LoginRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword())
        );

        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new RuntimeException("User not found"));

        String token = jwtUtil.generateToken(user.getEmail());
        return new AuthResponse(token, user.getEmail(), user.getName());
    }

    public User getUserByEmail(String email) {
        return userRepository.findByEmail(email)
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}