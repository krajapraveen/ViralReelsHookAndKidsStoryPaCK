package com.creatorstudio.security;

import org.springframework.stereotype.Service;

import java.util.regex.Pattern;

/**
 * Input Sanitization Service
 * Sanitizes and validates user input to prevent attacks
 */
@Service
public class InputSanitizer {

    // Pattern to remove potentially dangerous characters
    private static final Pattern DANGEROUS_CHARS = Pattern.compile("[<>\"';&|`$(){}\\[\\]\\\\]");
    
    // Pattern for valid email
    private static final Pattern EMAIL_PATTERN = Pattern.compile(
        "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    );
    
    // Pattern for valid username/name
    private static final Pattern NAME_PATTERN = Pattern.compile(
        "^[a-zA-Z0-9\\s._-]{2,100}$"
    );

    /**
     * Sanitize string input by removing dangerous characters
     */
    public String sanitizeString(String input) {
        if (input == null) return null;
        
        // Trim whitespace
        String sanitized = input.trim();
        
        // Remove null bytes
        sanitized = sanitized.replace("\0", "");
        
        // HTML encode special characters
        sanitized = sanitized
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("'", "&#x27;")
            .replace("/", "&#x2F;");
        
        return sanitized;
    }

    /**
     * Sanitize string for database storage (removes SQL injection chars)
     */
    public String sanitizeForDatabase(String input) {
        if (input == null) return null;
        
        return input
            .replace("'", "''")  // Escape single quotes
            .replace("\\", "\\\\")  // Escape backslashes
            .replace("\0", "");  // Remove null bytes
    }

    /**
     * Validate and sanitize email
     */
    public String sanitizeEmail(String email) {
        if (email == null) return null;
        
        String sanitized = email.trim().toLowerCase();
        
        if (!EMAIL_PATTERN.matcher(sanitized).matches()) {
            throw new IllegalArgumentException("Invalid email format");
        }
        
        return sanitized;
    }

    /**
     * Validate and sanitize name
     */
    public String sanitizeName(String name) {
        if (name == null) return null;
        
        String sanitized = name.trim();
        
        // Remove dangerous characters
        sanitized = DANGEROUS_CHARS.matcher(sanitized).replaceAll("");
        
        if (!NAME_PATTERN.matcher(sanitized).matches()) {
            throw new IllegalArgumentException("Invalid name format");
        }
        
        return sanitized;
    }

    /**
     * Sanitize URL parameter
     */
    public String sanitizeUrlParam(String param) {
        if (param == null) return null;
        
        return param
            .replace("..", "")
            .replace("./", "")
            .replace("//", "/")
            .replace("\0", "")
            .replace("\n", "")
            .replace("\r", "");
    }

    /**
     * Validate UUID format
     */
    public boolean isValidUUID(String uuid) {
        if (uuid == null) return false;
        return uuid.matches("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$");
    }

    /**
     * Validate numeric input
     */
    public boolean isValidNumber(String input) {
        if (input == null) return false;
        return input.matches("^-?\\d+(\\.\\d+)?$");
    }

    /**
     * Sanitize JSON input
     */
    public String sanitizeJson(String json) {
        if (json == null) return null;
        
        // Remove potential script injections in JSON
        return json
            .replace("</script>", "")
            .replace("<script>", "")
            .replace("javascript:", "")
            .replace("data:", "");
    }

    /**
     * Check if input contains potential injection
     */
    public boolean containsInjection(String input) {
        if (input == null) return false;
        
        String lower = input.toLowerCase();
        
        // SQL injection keywords
        if (lower.contains(" or ") || lower.contains(" and ") ||
            lower.contains("select ") || lower.contains("insert ") ||
            lower.contains("update ") || lower.contains("delete ") ||
            lower.contains("drop ") || lower.contains("union ") ||
            lower.contains("--") || lower.contains(";")) {
            return true;
        }
        
        // XSS keywords
        if (lower.contains("<script") || lower.contains("javascript:") ||
            lower.contains("onerror") || lower.contains("onload")) {
            return true;
        }
        
        return false;
    }
}
