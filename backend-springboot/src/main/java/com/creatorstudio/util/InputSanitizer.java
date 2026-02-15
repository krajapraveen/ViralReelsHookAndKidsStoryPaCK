package com.creatorstudio.util;

import org.springframework.web.util.HtmlUtils;
import java.util.regex.Pattern;

/**
 * Utility class for input sanitization to prevent XSS and injection attacks
 */
public class InputSanitizer {

    // Pattern to detect potential XSS payloads
    private static final Pattern XSS_PATTERN = Pattern.compile(
        "<script.*?>.*?</script>|javascript:|on\\w+\\s*=|<iframe|<object|<embed|<form|<input|<button|<select|<textarea|<style|<link|<meta|expression\\s*\\(|eval\\s*\\(|alert\\s*\\(",
        Pattern.CASE_INSENSITIVE | Pattern.DOTALL
    );

    // Pattern for SQL injection detection
    private static final Pattern SQL_INJECTION_PATTERN = Pattern.compile(
        "('|--|;|/\\*|\\*/|@@|@|char\\s*\\(|nchar\\s*\\(|varchar\\s*\\(|nvarchar\\s*\\(|alter\\s|begin\\s|cast\\s|create\\s|cursor\\s|declare\\s|delete\\s|drop\\s|end\\s|exec\\s|execute\\s|fetch\\s|insert\\s|kill\\s|select\\s|sys\\s|sysobjects|syscolumns|table\\s|update\\s|union\\s|xp_)",
        Pattern.CASE_INSENSITIVE
    );

    /**
     * Sanitize input string by escaping HTML entities
     */
    public static String sanitize(String input) {
        if (input == null) {
            return null;
        }
        // Escape HTML entities
        return HtmlUtils.htmlEscape(input.trim());
    }

    /**
     * Sanitize and validate - throws exception if malicious content detected
     */
    public static String sanitizeStrict(String input) {
        if (input == null) {
            return null;
        }
        
        String trimmed = input.trim();
        
        // Check for XSS patterns
        if (containsXSS(trimmed)) {
            throw new IllegalArgumentException("Input contains potentially malicious content");
        }
        
        // Escape HTML entities
        return HtmlUtils.htmlEscape(trimmed);
    }

    /**
     * Check if input contains potential XSS payload
     */
    public static boolean containsXSS(String input) {
        if (input == null || input.isEmpty()) {
            return false;
        }
        return XSS_PATTERN.matcher(input).find();
    }

    /**
     * Check if input contains potential SQL injection
     */
    public static boolean containsSQLInjection(String input) {
        if (input == null || input.isEmpty()) {
            return false;
        }
        return SQL_INJECTION_PATTERN.matcher(input).find();
    }

    /**
     * Sanitize for display - removes all HTML tags
     */
    public static String stripHtml(String input) {
        if (input == null) {
            return null;
        }
        return input.replaceAll("<[^>]*>", "").trim();
    }

    /**
     * Validate email format
     */
    public static boolean isValidEmail(String email) {
        if (email == null || email.isEmpty()) {
            return false;
        }
        String emailRegex = "^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$";
        return email.matches(emailRegex);
    }

    /**
     * Validate password strength
     */
    public static boolean isStrongPassword(String password) {
        if (password == null || password.length() < 8) {
            return false;
        }
        // At least one uppercase, one lowercase, one digit, one special char
        String passwordRegex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}$";
        return password.matches(passwordRegex);
    }

    /**
     * Validate name field
     */
    public static String sanitizeName(String name) {
        if (name == null) {
            return null;
        }
        // Remove any non-alphanumeric characters except spaces, hyphens, and apostrophes
        return name.trim().replaceAll("[^a-zA-Z\\s'-]", "");
    }

    /**
     * Blocked words for kids content
     */
    private static final String[] KIDS_BLOCKED_WORDS = {
        "adult", "sex", "porn", "xxx", "nude", "naked", "erotic", "violent", "gore", "blood",
        "kill", "murder", "death", "drug", "alcohol", "beer", "wine", "cigarette", "smoke",
        "gun", "weapon", "abuse", "hate", "racist", "discrimination", "vulgar", "profanity",
        "explicit", "mature", "inappropriate", "offensive", "disturbing", "graphic", "brutal",
        "torture", "horror", "scary", "nightmare", "demon", "devil", "evil", "cult", "occult",
        "gambling", "casino", "betting", "suicide", "self-harm", "bully", "harassment"
    };

    /**
     * Validate content is appropriate for kids
     */
    public static boolean isKidsFriendly(String content) {
        if (content == null || content.isEmpty()) {
            return true;
        }
        String lowerContent = content.toLowerCase();
        for (String word : KIDS_BLOCKED_WORDS) {
            if (lowerContent.contains(word)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Validate and sanitize kids genre
     */
    public static String validateKidsGenre(String genre) {
        if (genre == null || genre.trim().isEmpty()) {
            throw new IllegalArgumentException("Genre is required");
        }
        if (genre.trim().length() < 3) {
            throw new IllegalArgumentException("Genre must be at least 3 characters");
        }
        if (genre.trim().length() > 50) {
            throw new IllegalArgumentException("Genre must be less than 50 characters");
        }
        if (!isKidsFriendly(genre)) {
            throw new IllegalArgumentException("Genre contains inappropriate content for kids");
        }
        return sanitize(genre.trim());
    }
}
