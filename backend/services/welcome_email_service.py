"""
Welcome Email & Onboarding Service
Sends automated welcome emails to new users
"""
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, HtmlContent
import logging

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "hello@visionary-suite.com")
WEBSITE_URL = "https://www.visionary-suite.com"


async def send_welcome_email(user_email: str, user_name: str, credits: int = 100):
    """Send welcome email to new user"""
    
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid not configured - skipping welcome email")
        return False
    
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
            .header {{ background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); padding: 40px 20px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 28px; }}
            .header p {{ color: rgba(255,255,255,0.9); margin: 10px 0 0 0; }}
            .content {{ padding: 40px 30px; }}
            .credit-box {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 16px; padding: 30px; text-align: center; margin: 20px 0; }}
            .credit-box h2 {{ color: white; font-size: 48px; margin: 0; }}
            .credit-box p {{ color: rgba(255,255,255,0.9); margin: 10px 0 0 0; }}
            .feature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 30px 0; }}
            .feature {{ background: #f8fafc; border-radius: 12px; padding: 20px; text-align: center; }}
            .feature-icon {{ font-size: 32px; margin-bottom: 10px; }}
            .feature h3 {{ margin: 0 0 5px 0; font-size: 16px; color: #1e293b; }}
            .feature p {{ margin: 0; font-size: 14px; color: #64748b; }}
            .cta-button {{ display: inline-block; background: linear-gradient(135deg, #f97316 0%, #ec4899 100%); color: white; padding: 16px 40px; border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 18px; margin: 20px 0; }}
            .cta-button:hover {{ opacity: 0.9; }}
            .tips {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
            .tips h4 {{ margin: 0 0 10px 0; color: #92400e; }}
            .tips ul {{ margin: 0; padding-left: 20px; color: #78350f; }}
            .footer {{ background: #1e293b; padding: 30px; text-align: center; color: #94a3b8; }}
            .footer a {{ color: #818cf8; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to CreatorStudio AI!</h1>
                <p>Hi {user_name}, your content creation journey starts now</p>
            </div>
            
            <div class="content">
                <div class="credit-box">
                    <h2>{credits}</h2>
                    <p>FREE CREDITS IN YOUR ACCOUNT</p>
                </div>
                
                <p style="font-size: 18px; color: #334155; line-height: 1.6;">
                    You now have everything you need to create viral content for Instagram, YouTube, TikTok and more. 
                    Let's get you started!
                </p>
                
                <div class="feature-grid">
                    <div class="feature">
                        <div class="feature-icon">🎬</div>
                        <h3>Viral Reel Scripts</h3>
                        <p>10 credits per reel</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📚</div>
                        <h3>Kids Story Packs</h3>
                        <p>6 credits per story</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🎨</div>
                        <h3>Photo to Comic</h3>
                        <p>15 credits per comic</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📅</div>
                        <h3>30-Day Calendar</h3>
                        <p>10 credits per calendar</p>
                    </div>
                </div>
                
                <div style="text-align: center;">
                    <a href="{WEBSITE_URL}/app" class="cta-button">Start Creating Now →</a>
                </div>
                
                <div class="tips">
                    <h4>💡 Pro Tips to Get Started:</h4>
                    <ul>
                        <li><strong>First:</strong> Generate a Reel Script to see how powerful the AI is</li>
                        <li><strong>Daily:</strong> Login every day to claim FREE bonus credits</li>
                        <li><strong>Share:</strong> Refer friends and earn 50 credits per signup</li>
                    </ul>
                </div>
                
                <p style="color: #64748b; font-size: 14px; margin-top: 30px;">
                    Need help? Check out our <a href="{WEBSITE_URL}/user-manual" style="color: #6366f1;">User Manual</a> 
                    or <a href="{WEBSITE_URL}/contact" style="color: #6366f1;">Contact Support</a>.
                </p>
            </div>
            
            <div class="footer">
                <p style="margin: 0 0 15px 0; color: white; font-weight: bold;">CreatorStudio AI</p>
                <p style="margin: 0 0 10px 0;">The AI-powered content creation platform</p>
                <p style="margin: 0; font-size: 12px;">
                    <a href="{WEBSITE_URL}/privacy-policy">Privacy Policy</a> • 
                    <a href="{WEBSITE_URL}/terms-of-service">Terms of Service</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = Mail(
            from_email=Email(SENDER_EMAIL, "CreatorStudio AI"),
            to_emails=To(user_email),
            subject=f"🎉 Welcome {user_name}! Your {credits} Free Credits Are Ready",
            html_content=HtmlContent(html_content)
        )
        
        response = sg.send(message)
        logger.info(f"Welcome email sent to {user_email}: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user_email}: {e}")
        return False


async def send_streak_reminder_email(user_email: str, user_name: str, current_streak: int, potential_reward: int):
    """Send email reminding user to maintain their streak"""
    
    if not SENDGRID_API_KEY:
        return False
    
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #f97316 0%, #ec4899 100%); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; }}
            .content {{ padding: 30px; text-align: center; }}
            .streak-box {{ background: #fef3c7; border-radius: 12px; padding: 20px; margin: 20px 0; }}
            .streak-number {{ font-size: 48px; font-weight: bold; color: #f59e0b; }}
            .cta {{ display: inline-block; background: linear-gradient(135deg, #f97316, #ec4899); color: white; padding: 15px 40px; border-radius: 50px; text-decoration: none; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔥 Don't Break Your Streak!</h1>
            </div>
            <div class="content">
                <p>Hey {user_name},</p>
                <div class="streak-box">
                    <div class="streak-number">{current_streak}</div>
                    <p>day streak</p>
                </div>
                <p>Login today to claim <strong>{potential_reward} free credits</strong> and keep your streak alive!</p>
                <a href="{WEBSITE_URL}/app" class="cta">Claim My Reward →</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = Mail(
            from_email=Email(SENDER_EMAIL, "CreatorStudio AI"),
            to_emails=To(user_email),
            subject=f"🔥 {user_name}, your {current_streak}-day streak is at risk!",
            html_content=HtmlContent(html_content)
        )
        
        response = sg.send(message)
        logger.info(f"Streak reminder sent to {user_email}: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send streak reminder to {user_email}: {e}")
        return False
