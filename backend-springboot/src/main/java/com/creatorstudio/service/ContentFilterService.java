package com.creatorstudio.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Content filtering service to block inappropriate content
 * Used for all user-generated text inputs
 */
@Service
public class ContentFilterService {

    private static final Logger logger = LoggerFactory.getLogger(ContentFilterService.class);

    // Blocked words list - comprehensive list for content safety
    private static final Set<String> BLOCKED_WORDS = new HashSet<>(Arrays.asList(
        // Adult/Sexual content
        "sex", "porn", "xxx", "nude", "naked", "erotic", "adult", "nsfw", "explicit",
        "orgasm", "masturbat", "penis", "vagina", "boob", "breast", "nipple", "genital",
        "prostitut", "escort", "stripper", "onlyfans", "fetish", "bdsm", "kinky",
        // Violence
        "kill", "murder", "blood", "gore", "violent", "torture", "abuse", "assault",
        "rape", "molest", "stab", "shoot", "bomb", "terrorist", "massacre", "genocide",
        "decapitat", "dismember", "mutilat", "brutal",
        // Hate/Discrimination
        "racist", "racism", "nazi", "hitler", "hate", "discriminat", "slur", "bigot",
        "homophob", "transphob", "sexist", "supremac", "extremist",
        // Drugs/Illegal
        "cocaine", "heroin", "meth", "crack", "ecstasy", "lsd", "overdose", "drug deal",
        // Self-harm
        "suicide", "self-harm", "cutting", "anorex", "bulimi",
        // Disturbing
        "pedophil", "incest", "bestiality", "necrophil", "cannibal",
        // Profanity (common)
        "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "dick", "cock", "whore",
        // Kids Story specific (additional blocked for kids content)
        "alcohol", "beer", "wine", "cigarette", "smoke", "gun", "weapon",
        "demon", "devil", "cult", "occult", "gambling", "casino", "betting",
        "bully", "harassment"
    ));

    // Pattern to find word boundaries (case insensitive)
    private static final Pattern WORD_PATTERN = Pattern.compile("\\b\\w+\\b");

    /**
     * Validates text content for inappropriate words
     * @param text The text to validate
     * @return ValidationResult with success status and message
     */
    public ValidationResult validateContent(String text) {
        if (text == null || text.trim().isEmpty()) {
            return new ValidationResult(true, "");
        }

        String lowerText = text.toLowerCase();

        // Check for blocked words (partial match for stems like "masturbat" -> "masturbation")
        for (String blockedWord : BLOCKED_WORDS) {
            if (lowerText.contains(blockedWord)) {
                logger.warn("Content filter blocked: Found '{}' in text", blockedWord);
                return new ValidationResult(false, 
                    "Your content contains inappropriate language. Please use family-friendly text.");
            }
        }

        return new ValidationResult(true, "");
    }

    /**
     * Validates content specifically for kids story generation
     * More strict filtering
     */
    public ValidationResult validateKidsContent(String text) {
        ValidationResult basicCheck = validateContent(text);
        if (!basicCheck.isValid()) {
            return basicCheck;
        }

        // Additional strict checks for kids content
        String lowerText = text.toLowerCase();
        
        // Check for scary/horror themes
        String[] kidsBlockedTerms = {"horror", "scary", "nightmare", "demon", "evil", "death", "dying"};
        for (String term : kidsBlockedTerms) {
            if (lowerText.contains(term)) {
                logger.warn("Kids content filter blocked: Found '{}' in text", term);
                return new ValidationResult(false,
                    "This content is not suitable for kids. Please choose a more family-friendly theme.");
            }
        }

        return new ValidationResult(true, "");
    }

    /**
     * Sanitizes text by removing potentially dangerous characters
     * Used for XSS prevention
     */
    public String sanitizeText(String text) {
        if (text == null) return null;
        
        return text
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#x27;")
            .replaceAll("/", "&#x2F;");
    }

    /**
     * Result class for validation
     */
    public static class ValidationResult {
        private final boolean valid;
        private final String message;

        public ValidationResult(boolean valid, String message) {
            this.valid = valid;
            this.message = message;
        }

        public boolean isValid() {
            return valid;
        }

        public String getMessage() {
            return message;
        }
    }
}
