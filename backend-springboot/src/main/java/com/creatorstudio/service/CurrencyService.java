package com.creatorstudio.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * Service for handling international currency conversions and exchange rates
 */
@Service
public class CurrencyService {

    private static final Logger logger = LoggerFactory.getLogger(CurrencyService.class);

    // Supported currencies with their symbols
    private static final Map<String, CurrencyInfo> SUPPORTED_CURRENCIES = Map.of(
            "INR", new CurrencyInfo("INR", "₹", "Indian Rupee", 1.0),
            "USD", new CurrencyInfo("USD", "$", "US Dollar", 83.0),
            "EUR", new CurrencyInfo("EUR", "€", "Euro", 90.0),
            "GBP", new CurrencyInfo("GBP", "£", "British Pound", 105.0),
            "AUD", new CurrencyInfo("AUD", "A$", "Australian Dollar", 54.0),
            "CAD", new CurrencyInfo("CAD", "C$", "Canadian Dollar", 61.0),
            "SGD", new CurrencyInfo("SGD", "S$", "Singapore Dollar", 62.0),
            "AED", new CurrencyInfo("AED", "د.إ", "UAE Dirham", 22.6),
            "JPY", new CurrencyInfo("JPY", "¥", "Japanese Yen", 0.55),
            "MYR", new CurrencyInfo("MYR", "RM", "Malaysian Ringgit", 17.5)
    );

    // Fallback exchange rates (INR as base)
    private Map<String, BigDecimal> fallbackRates = new HashMap<>();

    public CurrencyService() {
        // Initialize fallback rates
        fallbackRates.put("INR", BigDecimal.ONE);
        fallbackRates.put("USD", new BigDecimal("0.012")); // 1 INR = 0.012 USD
        fallbackRates.put("EUR", new BigDecimal("0.011"));
        fallbackRates.put("GBP", new BigDecimal("0.0095"));
        fallbackRates.put("AUD", new BigDecimal("0.0185"));
        fallbackRates.put("CAD", new BigDecimal("0.0164"));
        fallbackRates.put("SGD", new BigDecimal("0.0161"));
        fallbackRates.put("AED", new BigDecimal("0.044"));
        fallbackRates.put("JPY", new BigDecimal("1.82"));
        fallbackRates.put("MYR", new BigDecimal("0.057"));
    }

    /**
     * Get all supported currencies
     */
    public List<Map<String, Object>> getSupportedCurrencies() {
        List<Map<String, Object>> currencies = new ArrayList<>();
        for (CurrencyInfo info : SUPPORTED_CURRENCIES.values()) {
            Map<String, Object> curr = new HashMap<>();
            curr.put("code", info.code);
            curr.put("symbol", info.symbol);
            curr.put("name", info.name);
            currencies.add(curr);
        }
        return currencies;
    }

    /**
     * Convert amount from INR to target currency
     */
    public BigDecimal convertFromINR(BigDecimal amountInr, String targetCurrency) {
        if (targetCurrency == null || targetCurrency.equalsIgnoreCase("INR")) {
            return amountInr;
        }

        BigDecimal rate = getExchangeRate("INR", targetCurrency);
        return amountInr.multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Convert amount from source currency to INR
     */
    public BigDecimal convertToINR(BigDecimal amount, String sourceCurrency) {
        if (sourceCurrency == null || sourceCurrency.equalsIgnoreCase("INR")) {
            return amount;
        }

        BigDecimal rate = getExchangeRate(sourceCurrency, "INR");
        return amount.multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Get exchange rate between two currencies
     */
    @Cacheable(value = "exchangeRates", key = "#from + '-' + #to")
    public BigDecimal getExchangeRate(String from, String to) {
        if (from.equalsIgnoreCase(to)) {
            return BigDecimal.ONE;
        }

        // Try to fetch live rates, fallback to cached rates
        try {
            return fetchLiveExchangeRate(from, to);
        } catch (Exception e) {
            logger.warn("Failed to fetch live exchange rate, using fallback: {}", e.getMessage());
            return calculateFallbackRate(from, to);
        }
    }

    /**
     * Fetch live exchange rates from external API
     */
    private BigDecimal fetchLiveExchangeRate(String from, String to) {
        // Using fallback rates for now
        // In production, integrate with a currency API like:
        // - Open Exchange Rates
        // - Fixer.io
        // - Currency Layer
        return calculateFallbackRate(from, to);
    }

    /**
     * Calculate rate using fallback rates
     */
    private BigDecimal calculateFallbackRate(String from, String to) {
        BigDecimal fromRate = fallbackRates.getOrDefault(from.toUpperCase(), BigDecimal.ONE);
        BigDecimal toRate = fallbackRates.getOrDefault(to.toUpperCase(), BigDecimal.ONE);
        
        // Convert: from -> INR -> to
        if (from.equalsIgnoreCase("INR")) {
            return toRate;
        } else if (to.equalsIgnoreCase("INR")) {
            return BigDecimal.ONE.divide(fromRate, 6, RoundingMode.HALF_UP);
        } else {
            // Cross rate calculation
            BigDecimal inrAmount = BigDecimal.ONE.divide(fromRate, 6, RoundingMode.HALF_UP);
            return inrAmount.multiply(toRate).setScale(6, RoundingMode.HALF_UP);
        }
    }

    /**
     * Get currency symbol
     */
    public String getCurrencySymbol(String currencyCode) {
        CurrencyInfo info = SUPPORTED_CURRENCIES.get(currencyCode.toUpperCase());
        return info != null ? info.symbol : currencyCode;
    }

    /**
     * Format amount with currency symbol
     */
    public String formatAmount(BigDecimal amount, String currencyCode) {
        String symbol = getCurrencySymbol(currencyCode);
        return symbol + amount.setScale(2, RoundingMode.HALF_UP).toString();
    }

    /**
     * Check if currency is supported
     */
    public boolean isCurrencySupported(String currencyCode) {
        return currencyCode != null && SUPPORTED_CURRENCIES.containsKey(currencyCode.toUpperCase());
    }

    /**
     * Get all exchange rates from INR
     */
    public Map<String, BigDecimal> getAllRatesFromINR() {
        Map<String, BigDecimal> rates = new HashMap<>();
        for (String currency : SUPPORTED_CURRENCIES.keySet()) {
            rates.put(currency, convertFromINR(BigDecimal.ONE, currency));
        }
        return rates;
    }

    // Inner class for currency info
    private static class CurrencyInfo {
        final String code;
        final String symbol;
        final String name;
        final double approxRateToInr;

        CurrencyInfo(String code, String symbol, String name, double approxRateToInr) {
            this.code = code;
            this.symbol = symbol;
            this.name = name;
            this.approxRateToInr = approxRateToInr;
        }
    }
}
