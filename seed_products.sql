-- Insert product data
INSERT INTO products (name, type, price_inr, credits, razorpay_plan_id, active) VALUES
('Starter Monthly', 'SUBSCRIPTION', 299.00, 60, NULL, true),
('Creator Monthly', 'SUBSCRIPTION', 699.00, 200, NULL, true),
('Pro Monthly', 'SUBSCRIPTION', 1499.00, 600, NULL, true),
('30 Credits Pack', 'CREDIT_PACK', 199.00, 30, NULL, true),
('90 Credits Pack', 'CREDIT_PACK', 499.00, 90, NULL, true),
('220 Credits Pack', 'CREDIT_PACK', 999.00, 220, NULL, true)
ON CONFLICT DO NOTHING;
