import * as fs from 'fs';
import * as path from 'path';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

/**
 * LOCAL VISUAL COMPARISON UTILITY
 * Compares screenshots to detect visual regressions
 */

const BASELINE_DIR = '/app/playwright-tests/visual-baselines';
const CURRENT_DIR = '/app/playwright-tests/mobile-screenshots';
const DIFF_DIR = '/app/playwright-tests/visual-diffs';

interface ComparisonResult {
  page: string;
  viewport: string;
  status: 'PASS' | 'FAIL' | 'NEW' | 'ERROR';
  diffPixels: number;
  diffPercentage: number;
  threshold: number;
  message: string;
}

export function ensureDirectories(): void {
  [BASELINE_DIR, CURRENT_DIR, DIFF_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });
}

export function compareScreenshots(
  baselinePath: string,
  currentPath: string,
  diffPath: string,
  threshold: number = 0.1
): ComparisonResult {
  const pageName = path.basename(currentPath, '.png');
  const [viewport, ...pageNameParts] = pageName.split('_');
  const page = pageNameParts.join('_');

  try {
    // Check if baseline exists
    if (!fs.existsSync(baselinePath)) {
      // No baseline - this is a new page
      // Copy current as baseline
      fs.copyFileSync(currentPath, baselinePath);
      return {
        page,
        viewport,
        status: 'NEW',
        diffPixels: 0,
        diffPercentage: 0,
        threshold,
        message: 'New baseline created'
      };
    }

    // Load images
    const baseline = PNG.sync.read(fs.readFileSync(baselinePath));
    const current = PNG.sync.read(fs.readFileSync(currentPath));

    // Check dimensions match
    if (baseline.width !== current.width || baseline.height !== current.height) {
      return {
        page,
        viewport,
        status: 'FAIL',
        diffPixels: -1,
        diffPercentage: 100,
        threshold,
        message: `Dimension mismatch: baseline(${baseline.width}x${baseline.height}) vs current(${current.width}x${current.height})`
      };
    }

    // Create diff image
    const diff = new PNG({ width: baseline.width, height: baseline.height });
    
    const diffPixels = pixelmatch(
      baseline.data,
      current.data,
      diff.data,
      baseline.width,
      baseline.height,
      { threshold }
    );

    const totalPixels = baseline.width * baseline.height;
    const diffPercentage = (diffPixels / totalPixels) * 100;

    // Save diff image
    fs.writeFileSync(diffPath, PNG.sync.write(diff));

    // 1% threshold for failure
    const status = diffPercentage > 1 ? 'FAIL' : 'PASS';

    return {
      page,
      viewport,
      status,
      diffPixels,
      diffPercentage: parseFloat(diffPercentage.toFixed(2)),
      threshold,
      message: status === 'PASS' 
        ? `Visual match (${diffPercentage.toFixed(2)}% diff)`
        : `Visual regression detected (${diffPercentage.toFixed(2)}% diff)`
    };
  } catch (error) {
    return {
      page,
      viewport,
      status: 'ERROR',
      diffPixels: -1,
      diffPercentage: -1,
      threshold,
      message: `Error comparing: ${error}`
    };
  }
}

export function runVisualComparison(): ComparisonResult[] {
  ensureDirectories();
  const results: ComparisonResult[] = [];

  // Get all current screenshots
  const currentScreenshots = fs.readdirSync(CURRENT_DIR)
    .filter(f => f.endsWith('.png'));

  for (const screenshot of currentScreenshots) {
    const currentPath = path.join(CURRENT_DIR, screenshot);
    const baselinePath = path.join(BASELINE_DIR, screenshot);
    const diffPath = path.join(DIFF_DIR, `diff_${screenshot}`);

    const result = compareScreenshots(baselinePath, currentPath, diffPath);
    results.push(result);
  }

  return results;
}

export function generateVisualReport(results: ComparisonResult[]): string {
  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  const newBaselines = results.filter(r => r.status === 'NEW').length;
  const errors = results.filter(r => r.status === 'ERROR').length;

  let report = `# Visual Regression Test Report\n\n`;
  report += `**Generated**: ${new Date().toISOString()}\n\n`;
  report += `## Summary\n\n`;
  report += `| Status | Count |\n`;
  report += `|--------|-------|\n`;
  report += `| ✅ Passed | ${passed} |\n`;
  report += `| ❌ Failed | ${failed} |\n`;
  report += `| 🆕 New Baselines | ${newBaselines} |\n`;
  report += `| ⚠️ Errors | ${errors} |\n\n`;

  // Group by viewport
  const viewports = [...new Set(results.map(r => r.viewport))];
  
  for (const viewport of viewports) {
    report += `## ${viewport}\n\n`;
    report += `| Page | Status | Diff % | Message |\n`;
    report += `|------|--------|--------|----------|\n`;
    
    const viewportResults = results.filter(r => r.viewport === viewport);
    for (const result of viewportResults) {
      const statusIcon = result.status === 'PASS' ? '✅' : 
                         result.status === 'FAIL' ? '❌' : 
                         result.status === 'NEW' ? '🆕' : '⚠️';
      report += `| ${result.page} | ${statusIcon} ${result.status} | ${result.diffPercentage}% | ${result.message} |\n`;
    }
    report += '\n';
  }

  // List failures
  const failures = results.filter(r => r.status === 'FAIL');
  if (failures.length > 0) {
    report += `## Failures (Require Review)\n\n`;
    for (const failure of failures) {
      report += `### ${failure.viewport}/${failure.page}\n`;
      report += `- Diff: ${failure.diffPercentage}%\n`;
      report += `- Message: ${failure.message}\n`;
      report += `- Diff image: \`${DIFF_DIR}/diff_${failure.viewport}_${failure.page}.png\`\n\n`;
    }
  }

  return report;
}

// CLI runner
if (require.main === module) {
  console.log('Running visual comparison...');
  const results = runVisualComparison();
  const report = generateVisualReport(results);
  
  const reportPath = '/app/playwright-tests/visual-regression-report.md';
  fs.writeFileSync(reportPath, report);
  
  console.log(report);
  console.log(`\nReport saved to: ${reportPath}`);
  
  // Exit with error if any failures
  const failures = results.filter(r => r.status === 'FAIL');
  process.exit(failures.length > 0 ? 1 : 0);
}
