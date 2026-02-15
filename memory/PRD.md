# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

## Tech Stack
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** Spring Boot (Java 17) on port 8001
- **Database:** PostgreSQL
- **Message Queue:** RabbitMQ
- **AI Worker:** Python/Flask on port 5000 (GPT-5.2)
- **Cache:** Redis

## Security Features Implemented ✅

### Web Application Firewall (WAF) 🛡️
- **SQL Injection Protection** - Blocks UNION, SELECT, DROP, etc.
- **XSS Protection** - Blocks <script>, javascript:, onerror, etc.
- **Path Traversal Protection** - Blocks ../, %2e%2e, etc.
- **Command Injection Protection** - Blocks system(), exec(), etc.
- **LDAP Injection Protection** - Blocks special LDAP characters

### Request Validation
- **HTTP Method Validation** - Only allows GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD
- **Content-Length Validation** - Max 10MB requests
- **Content-Type Validation** - Only JSON, form data allowed
- **Host Header Validation** - Prevents host header injection
- **Null Byte Protection** - Blocks null byte injection

### Rate Limiting & Anti-Bot
- **Global Rate Limit** - 50 requests/second per IP
- **Login Rate Limit** - 5 attempts per minute per IP
- **Auto IP Blocking** - Blocks after 100 suspicious requests
- **Block Duration** - 5 minutes temporary, permanent for repeat offenders

### Blocked Hacking Tools (User Agents)
- sqlmap, nikto, nmap, masscan, dirbuster, gobuster
- wfuzz, ffuf, burp, owasp zap, acunetix, nessus
- w3af, skipfish, arachni, vega, wpscan, joomscan
- havij, pangolin, sqlninja, xerxes, hulk, slowloris

### Blocked File Extensions
- .php, .asp, .aspx, .jsp, .cgi, .pl, .py, .rb
- .sh, .bash, .exe, .dll, .bat, .cmd, .ps1
- .htaccess, .htpasswd, .git, .svn, .env, .config

### Blocked Suspicious Paths
- /wp-admin, /wp-content (WordPress)
- /phpmyadmin, /pma (Database tools)
- /admin/config, /administrator
- /.git/, /.svn/, /.env
- /actuator (except /health), /metrics, /dump

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000
- Content-Security-Policy (CSP)
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(), microphone=(), geolocation=()

### Input Sanitization
- HTML encoding for special characters
- SQL escaping for database queries
- Email and name format validation
- UUID format validation
- JSON sanitization

### Security Monitoring
- Real-time attack logging
- Hourly security reports
- Attack statistics dashboard
- Automatic IP blocking after multiple attacks
- Admin security dashboard endpoint

## Admin Security Dashboard
- GET /api/admin/security/stats - Security statistics
- GET /api/admin/security/attacks - Recent attack attempts
- GET /api/admin/security/overview - Full security overview

## All Other Features
- [x] AI Reel Script Generator
- [x] Kids Story Video Pack Generator
- [x] AI Chatbot (GPT-5.2)
- [x] Credit System (54 free credits)
- [x] Razorpay Payments (TEST MODE)
- [x] International Currency (Live rates)
- [x] Email Notifications
- [x] Circuit Breaker (Resilience4j)
- [x] Privacy/GDPR Compliance
- [x] Automation System

## Test Credentials
- **Admin:** admin@creatorstudio.ai / Admin@123
- **Test User:** corstest1771172193@example.com / CorsTest123!

## Security Status
- WAF: ✅ ACTIVE
- Rate Limiting: ✅ ACTIVE
- Input Sanitization: ✅ ACTIVE
- Security Headers: ✅ ACTIVE
- Attack Monitoring: ✅ ACTIVE
