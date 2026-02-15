package com.creatorstudio.exception;

/**
 * Exception thrown when a product is not found
 */
public class ProductNotFoundException extends PaymentException {
    
    public ProductNotFoundException(Long productId) {
        super("PRODUCT_NOT_FOUND", 
              String.format("Product with ID %d not found", productId),
              "The selected product is no longer available. Please refresh and try again.");
    }
}
