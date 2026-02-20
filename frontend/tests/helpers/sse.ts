import { Page, expect } from "@playwright/test";

/**
 * Wait for SSE connection to be established
 */
export async function waitForSSEConnection(
  page: Page,
  jobId: string,
  timeout: number = 60000
): Promise<void> {
  // Wait for the job status element to appear and show processing
  const statusElement = page.locator(`[data-job-id="${jobId}"], [data-testid="job-status"]`);
  await expect(statusElement).toBeVisible({ timeout });
}

/**
 * Wait for job completion via SSE
 */
export async function waitForJobCompletion(
  page: Page,
  timeout: number = 120000
): Promise<{ status: string; hasOutput: boolean }> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    // Check for success indicators
    const successElement = page.locator('[data-testid="job-success"], .job-success, [data-status="completed"]');
    if (await successElement.isVisible().catch(() => false)) {
      const outputElement = page.locator('[data-testid="job-output"], img[src*="blob:"], video[src*="blob:"], img[src*="http"]');
      const hasOutput = await outputElement.isVisible().catch(() => false);
      return { status: "completed", hasOutput };
    }

    // Check for failure indicators
    const failureElement = page.locator('[data-testid="job-failure"], .job-error, [data-status="failed"]');
    if (await failureElement.isVisible().catch(() => false)) {
      return { status: "failed", hasOutput: false };
    }

    // Check for processing state with result
    const processingWithResult = page.locator('[data-status="completed"] img, [data-status="completed"] video');
    if (await processingWithResult.isVisible().catch(() => false)) {
      return { status: "completed", hasOutput: true };
    }

    await page.waitForTimeout(1000);
  }

  throw new Error(`Job did not complete within ${timeout}ms`);
}

/**
 * Monitor SSE events
 */
export async function monitorSSEEvents(
  page: Page,
  duration: number = 5000
): Promise<string[]> {
  const events: string[] = [];

  // Inject event listener
  await page.evaluate((dur) => {
    return new Promise<void>((resolve) => {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === "childList" || mutation.type === "attributes") {
            const target = mutation.target as HTMLElement;
            if (target.dataset?.status) {
              (window as any).__sseEvents = (window as any).__sseEvents || [];
              (window as any).__sseEvents.push(target.dataset.status);
            }
          }
        });
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["data-status"],
      });

      setTimeout(() => {
        observer.disconnect();
        resolve();
      }, dur);
    });
  }, duration);

  // Get collected events
  const collected = await page.evaluate(() => (window as any).__sseEvents || []);
  events.push(...collected);

  return events;
}

/**
 * Verify SSE reconnection behavior
 */
export async function testSSEReconnection(page: Page): Promise<boolean> {
  // Simulate network disconnect
  await page.context().setOffline(true);
  await page.waitForTimeout(2000);

  // Reconnect
  await page.context().setOffline(false);
  await page.waitForTimeout(3000);

  // Check if app recovered
  const errorElement = page.locator('[data-testid="connection-error"], .connection-error');
  return !(await errorElement.isVisible().catch(() => false));
}
