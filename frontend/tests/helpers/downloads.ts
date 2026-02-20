import { Page, Download, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

/**
 * Wait for and validate a download
 */
export async function waitForDownload(
  page: Page,
  triggerAction: () => Promise<void>,
  expectedExtensions: string[] = [".pdf", ".zip", ".json", ".csv", ".png", ".jpg", ".mp4"]
): Promise<{ download: Download; path: string; filename: string }> {
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 60000 }),
    triggerAction(),
  ]);

  const downloadPath = await download.path();
  expect(downloadPath).toBeTruthy();

  const filename = download.suggestedFilename();
  const extension = path.extname(filename).toLowerCase();

  // Validate extension
  const validExtension = expectedExtensions.some((ext) =>
    extension.includes(ext.replace(".", ""))
  );
  expect(validExtension, `Invalid extension: ${extension}`).toBeTruthy();

  // Validate file size > 0
  const stats = fs.statSync(downloadPath!);
  expect(stats.size, `Downloaded file is empty: ${filename}`).toBeGreaterThan(0);

  return { download, path: downloadPath!, filename };
}

/**
 * Validate PDF file
 */
export async function validatePDF(filePath: string): Promise<boolean> {
  const buffer = fs.readFileSync(filePath);
  // PDF files start with %PDF
  return buffer.slice(0, 4).toString() === "%PDF";
}

/**
 * Validate image file
 */
export async function validateImage(filePath: string): Promise<boolean> {
  const buffer = fs.readFileSync(filePath);
  // Check for common image signatures
  const pngSignature = buffer.slice(0, 8).toString("hex") === "89504e470d0a1a0a";
  const jpgSignature = buffer.slice(0, 2).toString("hex") === "ffd8";
  const webpSignature = buffer.slice(8, 12).toString() === "WEBP";

  return pngSignature || jpgSignature || webpSignature;
}

/**
 * Validate video file
 */
export async function validateVideo(filePath: string): Promise<boolean> {
  const buffer = fs.readFileSync(filePath);
  // Check for MP4 signature (ftyp)
  const ftypStart = buffer.slice(4, 8).toString();
  return ftypStart === "ftyp";
}

/**
 * Clean up download directory
 */
export function cleanupDownloads(dir: string): void {
  if (fs.existsSync(dir)) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
      fs.unlinkSync(path.join(dir, file));
    }
  }
}
