import { test, expect } from "@playwright/test";
import { URLS, PUBLIC_URLS, PROTECTED_URLS } from "../fixtures/urls";
import { login } from "../helpers/auth";
import users from "../fixtures/users.json";

test.describe("07 - Link Crawl and Validation", () => {
  test.describe("Public Pages Link Validation", () => {
    test("All internal links on public pages are valid", async ({ page }) => {
      const brokenLinks: string[] = [];
      const checkedLinks = new Set<string>();

      for (const url of PUBLIC_URLS.slice(0, 5)) {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

        const links = await page.locator("a[href]").all();
        
        for (const link of links.slice(0, 15)) {
          const href = await link.getAttribute("href");
          if (!href) continue;
          
          // Skip external links, mailto, tel, anchors
          if (href.startsWith("mailto:") || href.startsWith("tel:") || href === "#") continue;
          if (href.startsWith("http") && !href.includes("studio-hardening-2.preview.emergentagent.com")) continue;

          const absoluteUrl = href.startsWith("http") ? href : new URL(href, url).toString();
          
          if (checkedLinks.has(absoluteUrl)) continue;
          checkedLinks.add(absoluteUrl);

          try {
            const resp = await page.request.get(absoluteUrl, { timeout: 10000 });
            if (resp.status() >= 400) {
              brokenLinks.push(`${url} -> ${absoluteUrl} (${resp.status()})`);
            }
          } catch (e) {
            // Timeout or network error
            brokenLinks.push(`${url} -> ${absoluteUrl} (error)`);
          }
        }
      }

      expect(brokenLinks.length, `Broken links:\n${brokenLinks.join("\n")}`).toBe(0);
    });
  });

  test.describe("Protected Pages Link Validation", () => {
    test("All internal links on app pages are valid", async ({ page }) => {
      await login(page, users.demoUser.email, users.demoUser.password);
      
      const brokenLinks: string[] = [];
      const checkedLinks = new Set<string>();
      const pagesToCheck = [URLS.app, URLS.billing, URLS.profile, URLS.genStudio, URLS.storyGen];

      for (const url of pagesToCheck) {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

        const links = await page.locator("a[href]").all();
        
        for (const link of links.slice(0, 15)) {
          const href = await link.getAttribute("href");
          if (!href) continue;
          
          if (href.startsWith("mailto:") || href.startsWith("tel:") || href === "#") continue;
          if (href.startsWith("http") && !href.includes("studio-hardening-2.preview.emergentagent.com")) continue;

          const absoluteUrl = href.startsWith("http") ? href : new URL(href, url).toString();
          
          if (checkedLinks.has(absoluteUrl)) continue;
          checkedLinks.add(absoluteUrl);

          try {
            const resp = await page.request.get(absoluteUrl, { timeout: 10000 });
            if (resp.status() >= 400) {
              brokenLinks.push(`${url} -> ${absoluteUrl} (${resp.status()})`);
            }
          } catch (e) {
            brokenLinks.push(`${url} -> ${absoluteUrl} (error)`);
          }
        }
      }

      expect(brokenLinks.length, `Broken links:\n${brokenLinks.join("\n")}`).toBe(0);
    });
  });

  test.describe("Navigation Flow", () => {
    test("Back navigation works correctly", async ({ page }) => {
      await page.goto(URLS.landing);
      await page.goto(URLS.pricing);
      await page.goBack();
      
      await expect(page).toHaveURL(URLS.landing);
    });

    test("Deep linking works", async ({ page }) => {
      await login(page, users.demoUser.email, users.demoUser.password);
      
      // Test deep links
      const deepLinks = [URLS.t2i, URLS.storyGen, URLS.subscription];
      
      for (const url of deepLinks) {
        await page.goto(url);
        
        // Should load the page, not redirect to login
        await expect(page).not.toHaveURL(/\/login/);
        
        // Page should have content
        const body = page.locator("body");
        const text = await body.textContent();
        expect(text?.length).toBeGreaterThan(50);
      }
    });

    test("404 page exists for invalid routes", async ({ page }) => {
      await page.goto(`${URLS.landing}this-page-does-not-exist-12345`);
      
      // Should show 404 or redirect
      const is404 = (await page.getByText(/404|not found|doesn't exist/i).isVisible()) ||
                    page.url().includes("404");
      const isRedirected = page.url() === URLS.landing || page.url().includes("login");
      
      expect(is404 || isRedirected).toBeTruthy();
    });
  });

  test.describe("Footer Links", () => {
    test("Footer links are accessible", async ({ page }) => {
      await page.goto(URLS.landing);
      
      // Check common footer links
      const footerLinks = page.locator("footer a[href]");
      const count = await footerLinks.count();
      
      if (count > 0) {
        for (let i = 0; i < Math.min(count, 5); i++) {
          const link = footerLinks.nth(i);
          const href = await link.getAttribute("href");
          
          if (href && !href.startsWith("mailto:") && !href.startsWith("tel:")) {
            const isExternal = href.startsWith("http") && !href.includes("studio-hardening-2");
            
            if (!isExternal) {
              const resp = await page.request.get(
                href.startsWith("http") ? href : new URL(href, URLS.landing).toString()
              );
              expect(resp.status(), `Footer link broken: ${href}`).toBeLessThan(400);
            }
          }
        }
      }
    });
  });

  test.describe("Social Links", () => {
    test("Social media links open correctly", async ({ page, context }) => {
      await page.goto(URLS.landing);
      
      // Find social links
      const socialLinks = page.locator('a[href*="twitter"], a[href*="facebook"], a[href*="instagram"], a[href*="linkedin"]');
      const count = await socialLinks.count();
      
      for (let i = 0; i < Math.min(count, 3); i++) {
        const link = socialLinks.nth(i);
        const href = await link.getAttribute("href");
        
        if (href) {
          // Check if it's a valid URL
          try {
            new URL(href);
          } catch {
            expect.fail(`Invalid social URL: ${href}`);
          }
        }
      }
    });
  });

  test.describe("API Endpoint Validation", () => {
    test("Health endpoint is accessible", async ({ request }) => {
      const response = await request.get(URLS.api.health);
      expect(response.status()).toBe(200);
      
      const data = await response.json();
      expect(data.status).toBe("healthy");
    });

    test("User Manual API is accessible", async ({ request }) => {
      const response = await request.get(URLS.api.userManual);
      expect(response.status()).toBe(200);
      
      const data = await response.json();
      expect(data.features).toBeDefined();
    });
  });
});
