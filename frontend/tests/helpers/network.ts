import { Page, Route, Request } from "@playwright/test";

/**
 * Intercept and log all API requests
 */
export async function setupNetworkLogger(page: Page): Promise<Request[]> {
  const requests: Request[] = [];

  page.on("request", (request) => {
    if (request.url().includes("/api/")) {
      requests.push(request);
    }
  });

  return requests;
}

/**
 * Mock a specific API endpoint
 */
export async function mockAPI(
  page: Page,
  urlPattern: string | RegExp,
  responseData: object,
  statusCode: number = 200
): Promise<void> {
  await page.route(urlPattern, async (route: Route) => {
    await route.fulfill({
      status: statusCode,
      contentType: "application/json",
      body: JSON.stringify(responseData),
    });
  });
}

/**
 * Simulate slow network
 */
export async function simulateSlowNetwork(page: Page, latencyMs: number = 2000): Promise<void> {
  await page.route("**/*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, latencyMs));
    await route.continue();
  });
}

/**
 * Simulate network failure
 */
export async function simulateNetworkFailure(page: Page, urlPattern: string | RegExp): Promise<void> {
  await page.route(urlPattern, async (route) => {
    await route.abort("failed");
  });
}

/**
 * Wait for specific API call
 */
export async function waitForAPI(
  page: Page,
  urlPattern: string | RegExp,
  timeout: number = 30000
): Promise<Request> {
  return page.waitForRequest(urlPattern, { timeout });
}

/**
 * Wait for API response
 */
export async function waitForAPIResponse(
  page: Page,
  urlPattern: string | RegExp,
  timeout: number = 30000
): Promise<{ status: number; body: any }> {
  const response = await page.waitForResponse(urlPattern, { timeout });
  return {
    status: response.status(),
    body: await response.json().catch(() => null),
  };
}

/**
 * Capture all console errors
 */
export function captureConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  });
  return errors;
}

/**
 * Check for broken images
 */
export async function findBrokenImages(page: Page): Promise<string[]> {
  const brokenImages: string[] = [];

  const images = await page.locator("img").all();
  for (const img of images) {
    const src = await img.getAttribute("src");
    if (!src) continue;

    const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
    if (naturalWidth === 0) {
      brokenImages.push(src);
    }
  }

  return brokenImages;
}
