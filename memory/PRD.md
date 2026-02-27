# Visionary Suite - PRODUCTION CONFIGURATION

## LIVE DOMAIN: https://www.visionary-suite.com

---

## CASHFREE WEBHOOK CONFIGURATION

### Webhook URL (Configure in Cashfree Dashboard)
```
URL: https://www.visionary-suite.com/api/cashfree/webhook
Secret: bzpvyga4m362do0eyvmb
```

### How to Configure in Cashfree:
1. Log in to Cashfree Dashboard: https://merchant.cashfree.com
2. Go to **Settings** → **Webhooks**
3. Click **Add Webhook**
4. Enter URL: `https://www.visionary-suite.com/api/cashfree/webhook`
5. Enter Secret Key: `bzpvyga4m362do0eyvmb`
6. Select Events:
   - `PAYMENT_SUCCESS_WEBHOOK`
   - `PAYMENT_FAILED_WEBHOOK`
   - `REFUND_STATUS_WEBHOOK`
7. Click **Save**

---

## PRODUCTION CREDENTIALS

### Cashfree (PRODUCTION - LIVE)
```
App ID: 121040799e195173f36345748ee7040121
Secret Key: cfsk_ma_prod_d10df27fffebb66ac2dde79fc9c1e8bd_fdc77ff6
Webhook Secret: bzpvyga4m362do0eyvmb
Environment: PRODUCTION
```

### User Accounts (All with UNLIMITED Credits)

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@creatorstudio.ai | Cr3@t0rStud!o#2026 |
| **Demo** | demo@example.com | Password123! |
| **QA** | qa@creatorstudio.ai | QATester@2026! |

### New User Signup
- **100 FREE credits** automatically granted

---

## IMPORTANT ADMIN DASHBOARDS

| Dashboard | URL |
|-----------|-----|
| Admin Panel | https://www.visionary-suite.com/app/admin |
| System Resilience | https://www.visionary-suite.com/app/admin/system-resilience |
| Template Analytics | https://www.visionary-suite.com/app/admin/template-analytics |
| Audit Logs | https://www.visionary-suite.com/app/admin/audit-logs |
| User Management | https://www.visionary-suite.com/app/admin/users |

---

## POST-DEPLOYMENT CHECKLIST

- [ ] Configure Cashfree webhook in dashboard
- [ ] Test a small real payment (₹1 test)
- [ ] Verify webhook receives payment notification
- [ ] Check System Resilience Dashboard shows healthy status
- [ ] Verify new user signup gives 100 credits

---

## SUPPORT CONTACTS

For any production issues:
- Check System Resilience Dashboard for health status
- Review Audit Logs for recent activities
- Monitor payment webhook logs

---

**Domain:** www.visionary-suite.com  
**Production Date:** 2026-02-27
