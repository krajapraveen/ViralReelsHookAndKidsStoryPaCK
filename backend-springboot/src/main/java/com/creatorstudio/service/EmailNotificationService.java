package com.creatorstudio.service;

import com.creatorstudio.entity.User;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Email Notification Service for important events
 * Sends notifications for payments, generation completion, and account alerts
 */
@Service
public class EmailNotificationService {

    private static final Logger logger = LoggerFactory.getLogger(EmailNotificationService.class);

    @Autowired(required = false)
    private JavaMailSender mailSender;

    @Value("${spring.mail.username:noreply@creatorstudio.ai}")
    private String fromEmail;

    @Value("${app.name:CreatorStudio AI}")
    private String appName;

    private static final String LOGO_URL = "https://blog-seo-posts.preview.emergentagent.com/logo.png";

    /**
     * Send payment confirmation email
     */
    @Async
    public void sendPaymentConfirmation(User user, String productName, BigDecimal amount, String currency, int creditsAdded, String transactionId) {
        String subject = "✅ Payment Confirmed - " + productName;
        
        String htmlContent = buildEmailTemplate(
            user.getName(),
            "Payment Successful!",
            String.format("""
                <p style="font-size: 16px; color: #333;">Thank you for your purchase! Your payment has been successfully processed.</p>
                
                <div style="background: linear-gradient(135deg, #667eea 0%%, #764ba2 100%%); border-radius: 12px; padding: 24px; margin: 24px 0; color: white;">
                    <h3 style="margin: 0 0 16px 0; font-size: 18px;">Transaction Details</h3>
                    <table style="width: 100%%; color: white;">
                        <tr><td style="padding: 8px 0;">Product:</td><td style="text-align: right; font-weight: bold;">%s</td></tr>
                        <tr><td style="padding: 8px 0;">Amount:</td><td style="text-align: right; font-weight: bold;">%s %s</td></tr>
                        <tr><td style="padding: 8px 0;">Credits Added:</td><td style="text-align: right; font-weight: bold;">%d credits</td></tr>
                        <tr><td style="padding: 8px 0;">Transaction ID:</td><td style="text-align: right; font-size: 12px;">%s</td></tr>
                    </table>
                </div>
                
                <p style="font-size: 14px; color: #666;">Your credits are now available in your account. Start creating amazing content!</p>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="https://blog-seo-posts.preview.emergentagent.com/app" 
                       style="display: inline-block; background: #6366f1; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Start Creating →
                    </a>
                </div>
                """,
                productName, getCurrencySymbol(currency), amount, creditsAdded, transactionId
            ),
            "Thank you for choosing CreatorStudio AI!"
        );

        sendEmail(user.getEmail(), subject, htmlContent);
    }

    /**
     * Send reel generation completion email
     */
    @Async
    public void sendReelGenerationComplete(User user, String topic, int creditsUsed) {
        String subject = "🎬 Your Reel Script is Ready!";
        
        String htmlContent = buildEmailTemplate(
            user.getName(),
            "Reel Script Generated!",
            String.format("""
                <p style="font-size: 16px; color: #333;">Great news! Your AI-generated reel script is ready.</p>
                
                <div style="background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 16px; margin: 24px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; color: #1e40af;"><strong>Topic:</strong> %s</p>
                    <p style="margin: 8px 0 0 0; color: #64748b; font-size: 14px;">Credits used: %d</p>
                </div>
                
                <p style="font-size: 14px; color: #666;">Your script includes:</p>
                <ul style="color: #666;">
                    <li>3 attention-grabbing hooks</li>
                    <li>Complete video script</li>
                    <li>Caption options</li>
                    <li>Trending hashtags</li>
                    <li>Best posting tips</li>
                </ul>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="https://blog-seo-posts.preview.emergentagent.com/app/history" 
                       style="display: inline-block; background: #6366f1; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        View Your Script →
                    </a>
                </div>
                """,
                topic, creditsUsed
            ),
            "Happy creating! 🎉"
        );

        sendEmail(user.getEmail(), subject, htmlContent);
    }

    /**
     * Send story generation completion email
     */
    @Async
    public void sendStoryGenerationComplete(User user, String genre, String ageGroup, int sceneCount, int creditsUsed) {
        String subject = "📚 Your Kids Story Pack is Ready!";
        
        String htmlContent = buildEmailTemplate(
            user.getName(),
            "Story Pack Generated!",
            String.format("""
                <p style="font-size: 16px; color: #333;">Wonderful news! Your AI-generated kids story pack is complete and ready for download.</p>
                
                <div style="background: linear-gradient(135deg, #a855f7 0%%, #6366f1 100%%); border-radius: 12px; padding: 24px; margin: 24px 0; color: white;">
                    <h3 style="margin: 0 0 16px 0; font-size: 18px;">📖 Story Details</h3>
                    <table style="width: 100%%; color: white;">
                        <tr><td style="padding: 8px 0;">Genre:</td><td style="text-align: right; font-weight: bold;">%s</td></tr>
                        <tr><td style="padding: 8px 0;">Age Group:</td><td style="text-align: right; font-weight: bold;">%s</td></tr>
                        <tr><td style="padding: 8px 0;">Scenes:</td><td style="text-align: right; font-weight: bold;">%d scenes</td></tr>
                        <tr><td style="padding: 8px 0;">Credits Used:</td><td style="text-align: right; font-weight: bold;">%d credits</td></tr>
                    </table>
                </div>
                
                <p style="font-size: 14px; color: #666;">Your story pack includes:</p>
                <ul style="color: #666;">
                    <li>Complete story with %d scenes</li>
                    <li>Narration text for each scene</li>
                    <li>Visual prompts for illustrations</li>
                    <li>YouTube-ready metadata</li>
                    <li>PDF download available</li>
                </ul>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="https://blog-seo-posts.preview.emergentagent.com/app/history" 
                       style="display: inline-block; background: #a855f7; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Download Story Pack →
                    </a>
                </div>
                """,
                genre, ageGroup, sceneCount, creditsUsed, sceneCount
            ),
            "Create magical stories! ✨"
        );

        sendEmail(user.getEmail(), subject, htmlContent);
    }

    /**
     * Send low credit alert
     */
    @Async
    public void sendLowCreditAlert(User user, BigDecimal remainingCredits) {
        String subject = "⚠️ Low Credit Balance Alert";
        
        String htmlContent = buildEmailTemplate(
            user.getName(),
            "Low Credit Balance",
            String.format("""
                <p style="font-size: 16px; color: #333;">Your CreatorStudio AI credit balance is running low.</p>
                
                <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin: 24px 0; text-align: center;">
                    <p style="margin: 0; font-size: 14px; color: #92400e;">Current Balance</p>
                    <p style="margin: 8px 0 0 0; font-size: 36px; font-weight: bold; color: #d97706;">%s credits</p>
                </div>
                
                <p style="font-size: 14px; color: #666;">Don't let your creativity stop! Top up your credits to continue generating amazing content.</p>
                
                <div style="background: #f8fafc; border-radius: 8px; padding: 16px; margin: 24px 0;">
                    <p style="margin: 0 0 12px 0; font-weight: bold; color: #334155;">Quick Reminder:</p>
                    <ul style="margin: 0; padding-left: 20px; color: #64748b;">
                        <li>Reel Script = 1 credit</li>
                        <li>Kids Story Pack = 6-8 credits</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="https://blog-seo-posts.preview.emergentagent.com/pricing" 
                       style="display: inline-block; background: #f59e0b; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Buy More Credits →
                    </a>
                </div>
                """,
                remainingCredits.stripTrailingZeros().toPlainString()
            ),
            "Keep creating amazing content!"
        );

        sendEmail(user.getEmail(), subject, htmlContent);
    }

    /**
     * Send welcome email to new users
     */
    @Async
    public void sendWelcomeEmail(User user) {
        String subject = "🎉 Welcome to CreatorStudio AI!";
        
        String htmlContent = buildEmailTemplate(
            user.getName(),
            "Welcome to CreatorStudio AI!",
            """
                <p style="font-size: 16px; color: #333;">Thank you for joining CreatorStudio AI! We're excited to have you on board.</p>
                
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 24px; margin: 24px 0; color: white; text-align: center;">
                    <p style="margin: 0; font-size: 14px; opacity: 0.9;">Your Welcome Bonus</p>
                    <p style="margin: 8px 0 0 0; font-size: 48px; font-weight: bold;">54 Credits</p>
                    <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">Start creating right away!</p>
                </div>
                
                <h3 style="color: #334155; margin-top: 32px;">What You Can Create:</h3>
                
                <div style="display: flex; gap: 16px; margin: 24px 0;">
                    <div style="flex: 1; background: #f0f9ff; border-radius: 8px; padding: 16px;">
                        <p style="margin: 0; font-weight: bold; color: #1e40af;">🎬 Reel Scripts</p>
                        <p style="margin: 8px 0 0 0; font-size: 14px; color: #64748b;">AI-generated Instagram reel scripts with hooks, captions & hashtags</p>
                    </div>
                </div>
                <div style="display: flex; gap: 16px; margin: 24px 0;">
                    <div style="flex: 1; background: #faf5ff; border-radius: 8px; padding: 16px;">
                        <p style="margin: 0; font-weight: bold; color: #7c3aed;">📚 Kids Story Packs</p>
                        <p style="margin: 8px 0 0 0; font-size: 14px; color: #64748b;">Complete story packages with scenes, narration & YouTube metadata</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="https://blog-seo-posts.preview.emergentagent.com/app" 
                       style="display: inline-block; background: #6366f1; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Start Creating Now →
                    </a>
                </div>
                """,
            "Let's create something amazing together!"
        );

        sendEmail(user.getEmail(), subject, htmlContent);
    }

    /**
     * Send account deletion confirmation
     */
    @Async
    public void sendAccountDeletionScheduled(User user, String reason) {
        String subject = "⚠️ Account Deletion Scheduled";
        
        String htmlContent = buildEmailTemplate(
            user.getName(),
            "Account Deletion Scheduled",
            String.format("""
                <p style="font-size: 16px; color: #333;">We've received your request to delete your CreatorStudio AI account.</p>
                
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 20px; margin: 24px 0;">
                    <p style="margin: 0; font-weight: bold; color: #b91c1c;">⏳ 30-Day Grace Period</p>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #7f1d1d;">Your account will be permanently deleted in 30 days. You can cancel this request anytime before then.</p>
                </div>
                
                <p style="font-size: 14px; color: #666;"><strong>Reason provided:</strong> %s</p>
                
                <p style="font-size: 14px; color: #666;">If you change your mind, simply log in to your account and go to Privacy Settings to cancel the deletion.</p>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="https://blog-seo-posts.preview.emergentagent.com/app/privacy" 
                       style="display: inline-block; background: #6366f1; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Cancel Deletion →
                    </a>
                </div>
                """,
                reason
            ),
            "We're sorry to see you go."
        );

        sendEmail(user.getEmail(), subject, htmlContent);
    }

    /**
     * Build email template with consistent styling
     */
    private String buildEmailTemplate(String userName, String title, String content, String footer) {
        String currentDate = LocalDateTime.now().format(DateTimeFormatter.ofPattern("MMMM d, yyyy"));
        
        return String.format("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f1f5f9;">
                <table cellpadding="0" cellspacing="0" border="0" width="100%%" style="background-color: #f1f5f9; padding: 40px 20px;">
                    <tr>
                        <td align="center">
                            <table cellpadding="0" cellspacing="0" border="0" width="600" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #6366f1 0%%, #8b5cf6 100%%); padding: 32px; text-align: center;">
                                        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: bold;">CreatorStudio AI</h1>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <p style="margin: 0 0 8px 0; color: #64748b; font-size: 14px;">%s</p>
                                        <h2 style="margin: 0 0 24px 0; color: #1e293b; font-size: 28px;">Hi %s! 👋</h2>
                                        <h3 style="margin: 0 0 24px 0; color: #334155; font-size: 20px;">%s</h3>
                                        
                                        %s
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
                                        <p style="margin: 0 0 8px 0; color: #64748b; font-size: 14px;">%s</p>
                                        <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                                            © 2025 CreatorStudio AI. All rights reserved.<br>
                                            <a href="https://blog-seo-posts.preview.emergentagent.com/privacy-policy" style="color: #6366f1; text-decoration: none;">Privacy Policy</a> • 
                                            <a href="https://blog-seo-posts.preview.emergentagent.com/contact" style="color: #6366f1; text-decoration: none;">Contact Us</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """,
            currentDate, userName, title, content, footer
        );
    }

    /**
     * Send email using JavaMailSender
     */
    private void sendEmail(String to, String subject, String htmlContent) {
        if (mailSender == null) {
            logger.warn("Mail sender not configured. Email to {} with subject '{}' not sent.", to, subject);
            return;
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            
            helper.setFrom(fromEmail, appName);
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(htmlContent, true);
            
            mailSender.send(message);
            logger.info("Email sent successfully to: {} - Subject: {}", to, subject);
        } catch (Exception e) {
            logger.error("Failed to send email to {}: {}", to, e.getMessage());
        }
    }

    private String getCurrencySymbol(String currency) {
        return switch (currency.toUpperCase()) {
            case "INR" -> "₹";
            case "USD" -> "$";
            case "EUR" -> "€";
            case "GBP" -> "£";
            default -> currency;
        };
    }
}
