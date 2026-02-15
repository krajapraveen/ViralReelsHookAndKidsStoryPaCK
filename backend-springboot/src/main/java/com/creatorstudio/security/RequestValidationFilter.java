package com.creatorstudio.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;

/**
 * Request Validation Filter
 * Additional security checks for incoming requests
 */
@Component
@Order(2)
public class RequestValidationFilter implements Filter {

    private static final Logger logger = LoggerFactory.getLogger(RequestValidationFilter.class);

    // Allowed HTTP methods
    private static final List<String> ALLOWED_METHODS = Arrays.asList(
        "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"
    );

    // Max content length (10MB)
    private static final long MAX_CONTENT_LENGTH = 10 * 1024 * 1024;

    // Allowed content types for POST/PUT
    private static final List<String> ALLOWED_CONTENT_TYPES = Arrays.asList(
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain"
    );

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;

        // 1. Validate HTTP method
        String method = httpRequest.getMethod().toUpperCase();
        if (!ALLOWED_METHODS.contains(method)) {
            logger.warn("Invalid HTTP method: {} from {}", method, getClientIP(httpRequest));
            httpResponse.setStatus(HttpServletResponse.SC_METHOD_NOT_ALLOWED);
            httpResponse.getWriter().write("{\"success\":false,\"error\":\"Method not allowed\"}");
            return;
        }

        // 2. Validate Content-Length
        long contentLength = httpRequest.getContentLengthLong();
        if (contentLength > MAX_CONTENT_LENGTH) {
            logger.warn("Content too large: {} bytes from {}", contentLength, getClientIP(httpRequest));
            httpResponse.setStatus(HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE);
            httpResponse.getWriter().write("{\"success\":false,\"error\":\"Request too large\"}");
            return;
        }

        // 3. Validate Content-Type for data-modifying requests
        if (Arrays.asList("POST", "PUT", "PATCH").contains(method)) {
            String contentType = httpRequest.getContentType();
            if (contentType != null && !isValidContentType(contentType)) {
                logger.warn("Invalid content type: {} from {}", contentType, getClientIP(httpRequest));
                httpResponse.setStatus(HttpServletResponse.SC_UNSUPPORTED_MEDIA_TYPE);
                httpResponse.getWriter().write("{\"success\":false,\"error\":\"Unsupported content type\"}");
                return;
            }
        }

        // 4. Validate Host header (prevent host header injection)
        String host = httpRequest.getHeader("Host");
        if (host != null && !isValidHost(host)) {
            logger.warn("Invalid Host header: {} from {}", host, getClientIP(httpRequest));
            httpResponse.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            httpResponse.getWriter().write("{\"success\":false,\"error\":\"Invalid request\"}");
            return;
        }

        // 5. Check for null bytes in URL (null byte injection)
        String uri = httpRequest.getRequestURI();
        if (uri.contains("\0") || uri.contains("%00")) {
            logger.warn("Null byte injection attempt from {}", getClientIP(httpRequest));
            httpResponse.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            return;
        }

        // Continue with the request
        chain.doFilter(request, response);
    }

    private boolean isValidContentType(String contentType) {
        String lowerContentType = contentType.toLowerCase();
        return ALLOWED_CONTENT_TYPES.stream()
            .anyMatch(allowed -> lowerContentType.startsWith(allowed));
    }

    private boolean isValidHost(String host) {
        // Allow localhost and known domains
        return host.matches("^[a-zA-Z0-9.-]+(?::\\d+)?$") &&
               !host.contains("..") &&
               !host.startsWith(".") &&
               !host.endsWith(".");
    }

    private String getClientIP(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        logger.info("Request Validation Filter initialized");
    }

    @Override
    public void destroy() {}
}
