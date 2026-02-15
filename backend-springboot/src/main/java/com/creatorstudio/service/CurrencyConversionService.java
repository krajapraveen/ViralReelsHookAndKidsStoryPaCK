package com.creatorstudio.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Live Currency Conversion Service
 * Uses Frankfurter API (free, no API key required)
 * Falls back to cached rates if API is unavailable
 */
@Service
public class CurrencyConversionService {

    private static final Logger logger = LoggerFactory.getLogger(CurrencyConversionService.class);
    
    private static final String FRANKFURTER_API = "https://api.frankfurter.app/latest?from=INR";
    
    private final RestTemplate restTemplate = new RestTemplate();
    
    // Cache for exchange rates (INR as base)
    private final ConcurrentHashMap<String, BigDecimal> cachedRates = new ConcurrentHashMap<>();
    
    // Fallback rates if API fails
    private static final Map<String, BigDecimal> FALLBACK_RATES = Map.of(
        "INR", BigDecimal.ONE,
        "USD", new BigDecimal("0.012"),
        "EUR", new BigDecimal("0.011"),
        "GBP", new BigDecimal("0.0095"),
        "AUD", new BigDecimal("0.018"),
        "CAD", new BigDecimal("0.016"),
        "SGD", new BigDecimal("0.016"),
        "AED", new BigDecimal("0.044")
    );
    
    private long lastUpdateTime = 0;
    private boolean apiAvailable = true;

    public CurrencyConversionService() {
        // Initialize with fallback rates
        cachedRates.putAll(FALLBACK_RATES);
        // Fetch live rates on startup
        refreshExchangeRates();
    }

    /**
     * Get exchange rate from INR to target currency
     */
    public BigDecimal getExchangeRate(String targetCurrency) {
        String currency = targetCurrency.toUpperCase();
        
        if ("INR".equals(currency)) {
            return BigDecimal.ONE;
        }
        
        return cachedRates.getOrDefault(currency, FALLBACK_RATES.getOrDefault(currency, BigDecimal.ONE));
    }

    /**
     * Convert amount from INR to target currency
     */
    public BigDecimal convertFromINR(BigDecimal amountInr, String targetCurrency) {
        if (amountInr == null) {
            return BigDecimal.ZERO;
        }
        
        BigDecimal rate = getExchangeRate(targetCurrency);
        return amountInr.multiply(rate).setScale(2, RoundingMode.CEILING);
    }

    /**
     * Convert amount from target currency to INR
     */
    public BigDecimal convertToINR(BigDecimal amount, String fromCurrency) {
        if (amount == null) {
            return BigDecimal.ZERO;
        }
        
        if ("INR".equalsIgnoreCase(fromCurrency)) {
            return amount;
        }
        
        BigDecimal rate = getExchangeRate(fromCurrency);
        if (rate.compareTo(BigDecimal.ZERO) == 0) {
            return amount;
        }
        
        return amount.divide(rate, 2, RoundingMode.CEILING);
    }

    /**
     * Get all supported currencies with their rates
     */
    public Map<String, Object> getSupportedCurrencies() {
        Map<String, Object> result = new HashMap<>();
        result.put("baseCurrency", "INR");
        result.put("rates", new HashMap<>(cachedRates));
        result.put("lastUpdated", lastUpdateTime);
        result.put("isLiveRate", apiAvailable && (System.currentTimeMillis() - lastUpdateTime < 3600000));
        return result;
    }

    /**
     * Refresh exchange rates from API
     * Called every hour automatically
     */
    @Scheduled(fixedRate = 3600000) // Every hour
    public void refreshExchangeRates() {
        try {
            logger.info("Refreshing exchange rates from Frankfurter API...");
            
            ResponseEntity<Map> response = restTemplate.getForEntity(FRANKFURTER_API, Map.class);
            
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                Map<String, Number> rates = (Map<String, Number>) body.get("rates");
                
                if (rates != null) {
                    // INR is base
                    cachedRates.put("INR", BigDecimal.ONE);
                    
                    for (Map.Entry<String, Number> entry : rates.entrySet()) {
                        BigDecimal rate = new BigDecimal(entry.getValue().toString());
                        cachedRates.put(entry.getKey(), rate);
                    }
                    
                    lastUpdateTime = System.currentTimeMillis();
                    apiAvailable = true;
                    logger.info("Exchange rates updated successfully. {} currencies available.", cachedRates.size());
                }
            }
        } catch (Exception e) {
            logger.warn("Failed to fetch exchange rates from API: {}. Using cached/fallback rates.", e.getMessage());
            apiAvailable = false;
        }
    }

    /**
     * Get currency info for frontend display
     */
    public Map<String, Object> getCurrencyInfo(String currency) {
        Map<String, Object> info = new HashMap<>();
        info.put("code", currency.toUpperCase());
        info.put("rate", getExchangeRate(currency));
        info.put("isLiveRate", apiAvailable);
        
        // Add currency symbols
        Map<String, String> symbols = Map.of(
            "INR", "₹",
            "USD", "$",
            "EUR", "€",
            "GBP", "£",
            "AUD", "A$",
            "CAD", "C$",
            "SGD", "S$",
            "AED", "د.إ"
        );
        info.put("symbol", symbols.getOrDefault(currency.toUpperCase(), currency));
        
        return info;
    }
}
