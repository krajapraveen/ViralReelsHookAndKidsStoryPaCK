package com.creatorstudio.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.math.BigDecimal;
import java.util.Properties;

@Service
public class EmailService {

    private static final Logger logger = LoggerFactory.getLogger(EmailService.class);

    @Value("${spring.mail.username:}")
    private String mailUsername;

    @Value("${spring.mail.password:}")
    private String mailPassword;

    @Value("${spring.mail.host:smtp.gmail.com}")
    private String mailHost;

    @Value("${spring.mail.port:587}")
    private int mailPort;

    private JavaMailSender mailSender;

    @PostConstruct
    public void init() {
        if (mailUsername != null && !mailUsername.isEmpty()) {
            JavaMailSenderImpl sender = new JavaMailSenderImpl();
            sender.setHost(mailHost);
            sender.setPort(mailPort);
            sender.setUsername(mailUsername);
            sender.setPassword(mailPassword);

            Properties props = sender.getJavaMailProperties();
            props.put("mail.transport.protocol", "smtp");
            props.put("mail.smtp.auth", "true");
            props.put("mail.smtp.starttls.enable", "true");
            props.put("mail.smtp.ssl.trust", "smtp.gmail.com");

            this.mailSender = sender;
            logger.info("Email service initialized with Gmail SMTP");
        } else {
            logger.warn("Email service not configured - no username provided");
        }
    }

    @Async
    public void sendPaymentSuccessEmail(String toEmail, String userName, String productName, 
                                         BigDecimal amount, int credits, String transactionId) {
        if (mailSender == null) {
            logger.warn("Email not sent - service not configured");
            return;
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            helper.setFrom(mailUsername);
            helper.setTo(toEmail);
            helper.setSubject("✅ Payment Successful - CreatorStudio AI");

            String htmlContent = buildPaymentSuccessEmail(userName, productName, amount, credits, transactionId);
            helper.setText(htmlContent, true);

            mailSender.send(message);
            logger.info("Payment success email sent to: {}", toEmail);
        } catch (MessagingException e) {
            logger.error("Failed to send payment success email: {}", e.getMessage());
        }
    }

    @Async
    public void sendWelcomeEmail(String toEmail, String userName) {
        if (mailSender == null) {
            logger.warn("Email not sent - service not configured");
            return;
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            helper.setFrom(mailUsername);
            helper.setTo(toEmail);
            helper.setSubject("🎉 Welcome to CreatorStudio AI!");

            String htmlContent = buildWelcomeEmail(userName);
            helper.setText(htmlContent, true);

            mailSender.send(message);
            logger.info("Welcome email sent to: {}", toEmail);
        } catch (MessagingException e) {
            logger.error("Failed to send welcome email: {}", e.getMessage());
        }
    }

    @Async
    public void sendLowCreditsEmail(String toEmail, String userName, int remainingCredits) {
        if (mailSender == null) {
            logger.warn("Email not sent - service not configured");
            return;
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            helper.setFrom(mailUsername);
            helper.setTo(toEmail);
            helper.setSubject("⚠️ Low Credits Alert - CreatorStudio AI");

            String htmlContent = buildLowCreditsEmail(userName, remainingCredits);
            helper.setText(htmlContent, true);

            mailSender.send(message);
            logger.info("Low credits email sent to: {}", toEmail);
        } catch (MessagingException e) {
            logger.error("Failed to send low credits email: {}", e.getMessage());
        }
    }

    private String buildPaymentSuccessEmail(String userName, String productName, 
                                            BigDecimal amount, int credits, String transactionId) {
        return """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }
                    .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .header { background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center; }
                    .header h1 { color: white; margin: 0; font-size: 24px; }
                    .content { padding: 30px; }
                    .success-badge { background: #10b981; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: bold; margin-bottom: 20px; }
                    .details { background: #f8fafc; border-radius: 12px; padding: 20px; margin: 20px 0; }
                    .detail-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }
                    .detail-row:last-child { border-bottom: none; }
                    .detail-label { color: #64748b; }
                    .detail-value { font-weight: 600; color: #1e293b; }
                    .credits-box { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
                    .credits-number { font-size: 36px; font-weight: bold; }
                    .cta-button { display: block; background: #6366f1; color: white; text-decoration: none; padding: 14px 28px; border-radius: 8px; text-align: center; font-weight: 600; margin-top: 20px; }
                    .footer { text-align: center; padding: 20px; color: #64748b; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✨ CreatorStudio AI</h1>
                    </div>
                    <div class="content">
                        <span class="success-badge">✅ Payment Successful</span>
                        <h2 style="color: #1e293b; margin-top: 10px;">Thank you, %s!</h2>
                        <p style="color: #64748b;">Your payment has been processed successfully. Your credits have been added to your account.</p>
                        
                        <div class="credits-box">
                            <div style="font-size: 14px; opacity: 0.9;">Credits Added</div>
                            <div class="credits-number">+%d</div>
                        </div>
                        
                        <div class="details">
                            <div class="detail-row">
                                <span class="detail-label">Product</span>
                                <span class="detail-value">%s</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Amount Paid</span>
                                <span class="detail-value">₹%s</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Transaction ID</span>
                                <span class="detail-value">%s</span>
                            </div>
                        </div>
                        
                        <a href="https://sre-platform-2.preview.emergentagent.com/app" class="cta-button">
                            Start Creating →
                        </a>
                    </div>
                    <div class="footer">
                        <p>© 2026 CreatorStudio AI. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """.formatted(userName, credits, productName, amount.toString(), transactionId);
    }

    private String buildWelcomeEmail(String userName) {
        return """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }
                    .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .header { background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center; }
                    .header h1 { color: white; margin: 0; font-size: 24px; }
                    .content { padding: 30px; }
                    .welcome-badge { background: #10b981; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: bold; margin-bottom: 20px; }
                    .feature-box { background: #f8fafc; border-radius: 12px; padding: 20px; margin: 15px 0; }
                    .feature-title { font-weight: 600; color: #1e293b; margin-bottom: 5px; }
                    .feature-desc { color: #64748b; font-size: 14px; }
                    .credits-box { background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
                    .cta-button { display: block; background: #6366f1; color: white; text-decoration: none; padding: 14px 28px; border-radius: 8px; text-align: center; font-weight: 600; margin-top: 20px; }
                    .footer { text-align: center; padding: 20px; color: #64748b; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✨ CreatorStudio AI</h1>
                    </div>
                    <div class="content">
                        <span class="welcome-badge">🎉 Welcome!</span>
                        <h2 style="color: #1e293b; margin-top: 10px;">Hey %s!</h2>
                        <p style="color: #64748b;">Welcome to CreatorStudio AI! You're all set to create viral content in minutes.</p>
                        
                        <div class="credits-box">
                            <div style="font-size: 14px; opacity: 0.9;">Your Free Credits</div>
                            <div style="font-size: 36px; font-weight: bold;">54</div>
                        </div>
                        
                        <div class="feature-box">
                            <div class="feature-title">🎬 AI Reel Generator</div>
                            <div class="feature-desc">Generate viral Instagram reel scripts with hooks, captions, and hashtags (1 credit)</div>
                        </div>
                        
                        <div class="feature-box">
                            <div class="feature-title">📚 Kids Story Video Pack</div>
                            <div class="feature-desc">Create complete story video packages with scenes, narration, and YouTube metadata (6-8 credits)</div>
                        </div>
                        
                        <a href="https://sre-platform-2.preview.emergentagent.com/app" class="cta-button">
                            Start Creating →
                        </a>
                    </div>
                    <div class="footer">
                        <p>© 2026 CreatorStudio AI. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """.formatted(userName);
    }

    private String buildLowCreditsEmail(String userName, int remainingCredits) {
        return """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }
                    .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .header { background: linear-gradient(135deg, #f59e0b, #d97706); padding: 30px; text-align: center; }
                    .header h1 { color: white; margin: 0; font-size: 24px; }
                    .content { padding: 30px; }
                    .alert-badge { background: #fef3c7; color: #92400e; padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: bold; margin-bottom: 20px; }
                    .credits-box { background: #fef3c7; color: #92400e; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
                    .cta-button { display: block; background: #6366f1; color: white; text-decoration: none; padding: 14px 28px; border-radius: 8px; text-align: center; font-weight: 600; margin-top: 20px; }
                    .footer { text-align: center; padding: 20px; color: #64748b; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>⚠️ Low Credits Alert</h1>
                    </div>
                    <div class="content">
                        <span class="alert-badge">⚠️ Running Low</span>
                        <h2 style="color: #1e293b; margin-top: 10px;">Hey %s!</h2>
                        <p style="color: #64748b;">Your CreatorStudio AI credits are running low. Top up now to keep creating amazing content!</p>
                        
                        <div class="credits-box">
                            <div style="font-size: 14px;">Remaining Credits</div>
                            <div style="font-size: 36px; font-weight: bold;">%d</div>
                        </div>
                        
                        <a href="https://sre-platform-2.preview.emergentagent.com/pricing" class="cta-button">
                            Get More Credits →
                        </a>
                    </div>
                    <div class="footer">
                        <p>© 2026 CreatorStudio AI. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """.formatted(userName, remainingCredits);
    }

    @Async
    public void sendContactNotification(String name, String email, String subject, String messageContent) {
        if (mailSender == null) {
            logger.warn("Email not sent - service not configured");
            return;
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            helper.setFrom(mailUsername);
            helper.setTo("krajapraveen@visionary-suite.com");
            helper.setSubject("📬 New Contact Form: " + subject);

            String htmlContent = """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }
                        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                        .header { background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center; }
                        .header h1 { color: white; margin: 0; font-size: 24px; }
                        .content { padding: 30px; }
                        .info-box { background: #f8fafc; border-radius: 12px; padding: 20px; margin: 20px 0; }
                        .label { color: #64748b; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; }
                        .value { color: #1e293b; font-weight: 600; }
                        .message-box { background: #f1f5f9; border-left: 4px solid #6366f1; padding: 15px; margin-top: 20px; }
                        .footer { text-align: center; padding: 20px; color: #64748b; font-size: 14px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>📬 New Contact Form Submission</h1>
                        </div>
                        <div class="content">
                            <div class="info-box">
                                <div style="margin-bottom: 15px;">
                                    <div class="label">From</div>
                                    <div class="value">%s</div>
                                </div>
                                <div style="margin-bottom: 15px;">
                                    <div class="label">Email</div>
                                    <div class="value">%s</div>
                                </div>
                                <div>
                                    <div class="label">Subject</div>
                                    <div class="value">%s</div>
                                </div>
                            </div>
                            <div class="message-box">
                                <div class="label">Message</div>
                                <p style="color: #1e293b; white-space: pre-wrap;">%s</p>
                            </div>
                        </div>
                        <div class="footer">
                            <p>CreatorStudio AI Contact Form</p>
                        </div>
                    </div>
                </body>
                </html>
                """.formatted(name, email, subject, messageContent);

            helper.setText(htmlContent, true);
            mailSender.send(message);
            logger.info("Contact notification sent for: {}", email);
        } catch (MessagingException e) {
            logger.error("Failed to send contact notification: {}", e.getMessage());
        }
    }
}
