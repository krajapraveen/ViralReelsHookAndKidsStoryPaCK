package com.creatorstudio.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Pattern;

/**
 * Web Application Firewall (WAF) Filter
 * Blocks common hacking attempts and malicious requests
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class WebApplicationFirewall implements Filter {

    private static final Logger logger = LoggerFactory.getLogger(WebApplicationFirewall.class);

    // IP-based rate limiting and blocking
    private final ConcurrentHashMap<String, AtomicInteger> requestCounts = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> blockedIPs = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> lastRequestTime = new ConcurrentHashMap<>();
    
    // Configuration
    private static final int MAX_REQUESTS_PER_SECOND = 50;
    private static final int BLOCK_THRESHOLD = 100; // requests before temporary block
    private static final long BLOCK_DURATION_MS = 300000; // 5 minutes
    private static final long RATE_WINDOW_MS = 1000; // 1 second

    // SQL Injection patterns
    private static final List<Pattern> SQL_INJECTION_PATTERNS = Arrays.asList(
        Pattern.compile("(?i)(\\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|UNION|DECLARE)\\b)"),
        Pattern.compile("(?i)('\\s*(OR|AND)\\s*'?\\d*'?\\s*=\\s*'?\\d*|'\\s*(OR|AND)\\s*'[^']*'\\s*=\\s*'[^']*')"),
        Pattern.compile("(?i)(--\\s*$|#\\s*$|/\\*.*\\*/)"),
        Pattern.compile("(?i)(;\\s*(DROP|DELETE|UPDATE|INSERT))"),
        Pattern.compile("(?i)(WAITFOR\\s+DELAY|BENCHMARK\\s*\\()"),
        Pattern.compile("(?i)(LOAD_FILE|INTO\\s+OUTFILE|INTO\\s+DUMPFILE)"),
        Pattern.compile("(?i)(\\bEXEC\\s*\\(|\\bEXECUTE\\s*\\()"),
        Pattern.compile("0x[0-9a-fA-F]+"),
        Pattern.compile("(?i)(CHAR\\s*\\(|ASCII\\s*\\(|ORD\\s*\\()"),
        Pattern.compile("(?i)(SLEEP\\s*\\(|PG_SLEEP\\s*\\()")
    );

    // XSS patterns
    private static final List<Pattern> XSS_PATTERNS = Arrays.asList(
        Pattern.compile("(?i)<\\s*script[^>]*>"),
        Pattern.compile("(?i)<\\s*/\\s*script\\s*>"),
        Pattern.compile("(?i)javascript\\s*:"),
        Pattern.compile("(?i)on\\w+\\s*="),
        Pattern.compile("(?i)<\\s*iframe[^>]*>"),
        Pattern.compile("(?i)<\\s*object[^>]*>"),
        Pattern.compile("(?i)<\\s*embed[^>]*>"),
        Pattern.compile("(?i)<\\s*svg[^>]*onload"),
        Pattern.compile("(?i)<\\s*img[^>]*onerror"),
        Pattern.compile("(?i)expression\\s*\\("),
        Pattern.compile("(?i)vbscript\\s*:"),
        Pattern.compile("(?i)data\\s*:.*base64")
    );

    // Path traversal patterns
    private static final List<Pattern> PATH_TRAVERSAL_PATTERNS = Arrays.asList(
        Pattern.compile("\\.\\.[\\\\/]"),
        Pattern.compile("(?i)%2e%2e[\\\\/]"),
        Pattern.compile("(?i)%252e%252e[\\\\/]"),
        Pattern.compile("(?i)\\.\\.\\/"),
        Pattern.compile("(?i)\\.\\.\\\\")
    );

    // Command injection patterns
    private static final List<Pattern> COMMAND_INJECTION_PATTERNS = Arrays.asList(
        Pattern.compile("(?i)(;|\\||`|\\$\\(|\\&\\&|\\|\\|)\\s*(cat|ls|dir|rm|wget|curl|bash|sh|cmd|powershell)"),
        Pattern.compile("(?i)/etc/(passwd|shadow|hosts)"),
        Pattern.compile("(?i)/proc/self"),
        Pattern.compile("(?i)\\beval\\s*\\("),
        Pattern.compile("(?i)\\bsystem\\s*\\("),
        Pattern.compile("(?i)\\bexec\\s*\\("),
        Pattern.compile("(?i)\\bshell_exec\\s*\\(")
    );

    // LDAP injection patterns
    private static final List<Pattern> LDAP_INJECTION_PATTERNS = Arrays.asList(
        Pattern.compile("(?i)[)(|*\\\\]"),
        Pattern.compile("(?i)\\x00|\\x0a|\\x0d")
    );

    // Malicious User Agents (common hacking tools)
    private static final List<String> BLOCKED_USER_AGENTS = Arrays.asList(
        "sqlmap", "nikto", "nmap", "masscan", "dirbuster", "gobuster",
        "wfuzz", "ffuf", "burp", "owasp", "zap", "acunetix", "nessus",
        "w3af", "skipfish", "arachni", "vega", "wpscan", "joomscan",
        "havij", "pangolin", "sqlninja", "bbqsql", "xerxes", "hulk",
        "slowloris", "goldeneye", "torshammer", "pyloris", "httpflooder"
    );

    // Blocked file extensions
    private static final List<String> BLOCKED_EXTENSIONS = Arrays.asList(
        ".php", ".asp", ".aspx", ".jsp", ".cgi", ".pl", ".py", ".rb",
        ".sh", ".bash", ".exe", ".dll", ".bat", ".cmd", ".ps1",
        ".htaccess", ".htpasswd", ".git", ".svn", ".env", ".config"
    );

    // Suspicious request patterns
    private static final List<Pattern> SUSPICIOUS_PATTERNS = Arrays.asList(
        Pattern.compile("(?i)(\\/wp-admin|\\/wp-content|\\/wp-includes)"),
        Pattern.compile("(?i)(\\/phpmyadmin|\\/pma|\\/myadmin)"),
        Pattern.compile("(?i)(\\/admin\\/config|\\/administrator)"),
        Pattern.compile("(?i)(\\.git\\/|\\.svn\\/|\\.env)"),
        Pattern.compile("(?i)(\\/_profiler|\\/_wdt)"),
        Pattern.compile("(?i)(\\/actuator(?!\\/health)|\\/metrics|\\/dump)"),
        Pattern.compile("(?i)(\\/console|\\/manager\\/html)"),
        Pattern.compile("(?i)(\\/api\\/v1\\/debug|\\/debug\\/)")
    );

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        
        String clientIP = getClientIP(httpRequest);
        String requestURI = httpRequest.getRequestURI();
        String queryString = httpRequest.getQueryString();
        String userAgent = httpRequest.getHeader("User-Agent");
        String fullURL = requestURI + (queryString != null ? "?" + queryString : "");

        // 1. Check if IP is blocked
        if (isIPBlocked(clientIP)) {
            logger.warn("BLOCKED IP attempt: {} - {}", clientIP, requestURI);
            sendBlockedResponse(httpResponse, "Access denied. Your IP has been temporarily blocked.");
            return;
        }

        // 2. Rate limiting
        if (!checkRateLimit(clientIP)) {
            logger.warn("RATE LIMIT exceeded: {} - {}", clientIP, requestURI);
            sendRateLimitResponse(httpResponse);
            return;
        }

        // 3. Check User-Agent for hacking tools
        if (isBlockedUserAgent(userAgent)) {
            logger.warn("BLOCKED USER-AGENT: {} from {} - {}", userAgent, clientIP, requestURI);
            blockIP(clientIP, "Malicious user agent detected");
            sendBlockedResponse(httpResponse, "Access denied.");
            return;
        }

        // 4. Check for blocked file extensions
        if (hasBlockedExtension(requestURI)) {
            logger.warn("BLOCKED EXTENSION access: {} from {}", requestURI, clientIP);
            sendNotFoundResponse(httpResponse);
            return;
        }

        // 5. Check for suspicious paths
        if (isSuspiciousPath(requestURI)) {
            logger.warn("SUSPICIOUS PATH access: {} from {}", requestURI, clientIP);
            incrementSuspicionScore(clientIP);
            sendNotFoundResponse(httpResponse);
            return;
        }

        // 6. Check for SQL Injection
        if (containsSQLInjection(fullURL) || containsSQLInjection(getRequestBody(httpRequest))) {
            logger.warn("SQL INJECTION attempt from {}: {}", clientIP, fullURL);
            blockIP(clientIP, "SQL injection attempt");
            sendBlockedResponse(httpResponse, "Malicious request detected.");
            return;
        }

        // 7. Check for XSS
        if (containsXSS(fullURL) || containsXSS(getRequestBody(httpRequest))) {
            logger.warn("XSS attempt from {}: {}", clientIP, fullURL);
            blockIP(clientIP, "XSS attempt");
            sendBlockedResponse(httpResponse, "Malicious request detected.");
            return;
        }

        // 8. Check for Path Traversal
        if (containsPathTraversal(fullURL)) {
            logger.warn("PATH TRAVERSAL attempt from {}: {}", clientIP, fullURL);
            blockIP(clientIP, "Path traversal attempt");
            sendBlockedResponse(httpResponse, "Malicious request detected.");
            return;
        }

        // 9. Check for Command Injection
        if (containsCommandInjection(fullURL) || containsCommandInjection(getRequestBody(httpRequest))) {
            logger.warn("COMMAND INJECTION attempt from {}: {}", clientIP, fullURL);
            blockIP(clientIP, "Command injection attempt");
            sendBlockedResponse(httpResponse, "Malicious request detected.");
            return;
        }

        // 10. Add security headers to response
        addSecurityHeaders(httpResponse);

        // Continue with the request
        chain.doFilter(request, response);
    }

    private String getClientIP(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        String xRealIP = request.getHeader("X-Real-IP");
        if (xRealIP != null && !xRealIP.isEmpty()) {
            return xRealIP;
        }
        return request.getRemoteAddr();
    }

    private boolean isIPBlocked(String ip) {
        Long blockedUntil = blockedIPs.get(ip);
        if (blockedUntil != null) {
            if (System.currentTimeMillis() < blockedUntil) {
                return true;
            } else {
                blockedIPs.remove(ip);
                requestCounts.remove(ip);
            }
        }
        return false;
    }

    private void blockIP(String ip, String reason) {
        blockedIPs.put(ip, System.currentTimeMillis() + BLOCK_DURATION_MS);
        logger.warn("IP BLOCKED: {} - Reason: {} - Duration: {} minutes", ip, reason, BLOCK_DURATION_MS / 60000);
    }

    private boolean checkRateLimit(String ip) {
        long currentTime = System.currentTimeMillis();
        Long lastTime = lastRequestTime.get(ip);
        
        if (lastTime != null && currentTime - lastTime > RATE_WINDOW_MS) {
            requestCounts.remove(ip);
        }
        
        lastRequestTime.put(ip, currentTime);
        AtomicInteger count = requestCounts.computeIfAbsent(ip, k -> new AtomicInteger(0));
        int requests = count.incrementAndGet();
        
        if (requests > BLOCK_THRESHOLD) {
            blockIP(ip, "Rate limit exceeded");
            return false;
        }
        
        return requests <= MAX_REQUESTS_PER_SECOND;
    }

    private void incrementSuspicionScore(String ip) {
        AtomicInteger count = requestCounts.computeIfAbsent(ip, k -> new AtomicInteger(0));
        if (count.addAndGet(10) > BLOCK_THRESHOLD) {
            blockIP(ip, "Suspicious activity");
        }
    }

    private boolean isBlockedUserAgent(String userAgent) {
        if (userAgent == null || userAgent.isEmpty()) {
            return false; // Allow empty user agents (some legitimate clients)
        }
        String lowerUA = userAgent.toLowerCase();
        return BLOCKED_USER_AGENTS.stream().anyMatch(lowerUA::contains);
    }

    private boolean hasBlockedExtension(String uri) {
        String lowerURI = uri.toLowerCase();
        return BLOCKED_EXTENSIONS.stream().anyMatch(lowerURI::endsWith);
    }

    private boolean isSuspiciousPath(String uri) {
        return SUSPICIOUS_PATTERNS.stream().anyMatch(p -> p.matcher(uri).find());
    }

    private boolean containsSQLInjection(String input) {
        if (input == null || input.isEmpty()) return false;
        String decoded = decodeInput(input);
        return SQL_INJECTION_PATTERNS.stream().anyMatch(p -> p.matcher(decoded).find());
    }

    private boolean containsXSS(String input) {
        if (input == null || input.isEmpty()) return false;
        String decoded = decodeInput(input);
        return XSS_PATTERNS.stream().anyMatch(p -> p.matcher(decoded).find());
    }

    private boolean containsPathTraversal(String input) {
        if (input == null || input.isEmpty()) return false;
        String decoded = decodeInput(input);
        return PATH_TRAVERSAL_PATTERNS.stream().anyMatch(p -> p.matcher(decoded).find());
    }

    private boolean containsCommandInjection(String input) {
        if (input == null || input.isEmpty()) return false;
        String decoded = decodeInput(input);
        return COMMAND_INJECTION_PATTERNS.stream().anyMatch(p -> p.matcher(decoded).find());
    }

    private String decodeInput(String input) {
        try {
            String decoded = java.net.URLDecoder.decode(input, "UTF-8");
            // Double decode to catch encoded attacks
            decoded = java.net.URLDecoder.decode(decoded, "UTF-8");
            return decoded;
        } catch (Exception e) {
            return input;
        }
    }

    private String getRequestBody(HttpServletRequest request) {
        // For POST requests, we'd need to wrap the request to read the body
        // This is a simplified version that checks parameters
        StringBuilder params = new StringBuilder();
        request.getParameterMap().forEach((key, values) -> {
            params.append(key).append("=");
            for (String value : values) {
                params.append(value).append("&");
            }
        });
        return params.toString();
    }

    private void addSecurityHeaders(HttpServletResponse response) {
        response.setHeader("X-Content-Type-Options", "nosniff");
        response.setHeader("X-Frame-Options", "SAMEORIGIN");
        response.setHeader("X-XSS-Protection", "1; mode=block");
        response.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
        response.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
        response.setHeader("Pragma", "no-cache");
        response.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
        response.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    }

    private void sendBlockedResponse(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.setContentType("application/json");
        response.getWriter().write("{\"success\":false,\"error\":\"" + message + "\",\"errorCode\":\"ACCESS_DENIED\"}");
    }

    private void sendRateLimitResponse(HttpServletResponse response) throws IOException {
        response.setStatus(429);
        response.setContentType("application/json");
        response.setHeader("Retry-After", "60");
        response.getWriter().write("{\"success\":false,\"error\":\"Too many requests. Please slow down.\",\"errorCode\":\"RATE_LIMIT_EXCEEDED\",\"retryAfterSeconds\":60}");
    }

    private void sendNotFoundResponse(HttpServletResponse response) throws IOException {
        response.setStatus(HttpServletResponse.SC_NOT_FOUND);
        response.setContentType("application/json");
        response.getWriter().write("{\"success\":false,\"error\":\"Not found\"}");
    }

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        logger.info("Web Application Firewall initialized - Protection active");
    }

    @Override
    public void destroy() {
        logger.info("Web Application Firewall destroyed");
    }
}
