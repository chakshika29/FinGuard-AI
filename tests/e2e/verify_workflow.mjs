import { chromium } from "../../frontend/node_modules/playwright-core/index.mjs";
import fs from "node:fs";
import path from "node:path";

const FRONTEND_URL = "http://127.0.0.1:5173";
const SCREENSHOT_DIR = path.resolve("docs/screenshots");
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function run() {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true,
  });

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  const failedRequests = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("response", (res) => {
    if (res.status() >= 500) failedRequests.push(`${res.status()} ${res.url()}`);
  });

  console.log("[1/10] Opening FinGuard AI Login Page...");
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Sign in to Workspace");
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "01_login.png") });

  console.log("[2/10] Logging in as Administrator...");
  await page.click("button[type='submit']");
  await page.waitForSelector("text=Total Curated Transactions", { timeout: 15000 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "02_overview.png") });

  console.log("[3/10] Verifying Transactions Explorer & Detail Drawer...");
  await page.click("nav >> text=Transactions");
  await page.waitForSelector("text=Export CSV", { timeout: 10000 });
  await page.waitForSelector("tbody tr", { timeout: 10000 });
  await page.click("tbody tr >> nth=0");
  await page.waitForSelector("text=Explainable Risk Indicators", { timeout: 10000 });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "03_transactions_drawer.png") });
  // Close drawer
  await page.click("div.fixed >> button");

  console.log("[4/10] Verifying Data Ingestion & Generating 10,000 Records...");
  await page.click("nav >> text=Data Ingestion");
  await page.waitForSelector("text=Generate & Ingest Synthetic Dataset", { timeout: 10000 });
  await page.click("text=Generate & Run ETL Pipeline");
  await page.waitForSelector("text=queued job", { timeout: 15000 });
  await page.waitForTimeout(3500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "04_ingestion.png") });

  console.log("[5/10] Verifying Data Quality & Running Quality Checks...");
  await page.click("nav >> text=Data Quality");
  await page.waitForSelector("text=7-Dimension Quality Breakdown", { timeout: 10000 });
  await page.click("text=Run Quality Checks");
  await page.waitForSelector("text=completed: Score", { timeout: 15000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "05_data_quality.png") });

  console.log("[6/10] Verifying Fraud Analytics & Alert Review...");
  await page.click("nav >> text=Fraud Analytics");
  await page.waitForSelector("text=IsolationForest Anomaly ML", { timeout: 10000 });
  await page.waitForSelector("text=Investigate", { timeout: 10000 });
  await page.click("text=Investigate >> nth=0");
  await page.waitForSelector("text=updated to INVESTIGATING", { timeout: 10000 });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "06_fraud_analytics.png") });

  console.log("[7/10] Verifying Credit Risk Analytics...");
  await page.click("nav >> text=Credit Risk");
  await page.waitForSelector("text=Portfolio Exposure", { timeout: 10000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "07_credit_risk.png") });

  console.log("[8/10] Verifying Data Catalog & Business Glossary...");
  await page.click("nav >> text=Data Catalog");
  await page.waitForSelector("text=finguard_curated.transactions", { timeout: 10000 });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "08_data_catalog.png") });

  console.log("[9/10] Verifying Data Lineage & Governance Policies & Audit Logs...");
  await page.click("nav >> text=Data Lineage");
  await page.waitForSelector("text=End-to-End Medallion Data Lineage", { timeout: 10000 });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "09_data_lineage.png") });

  await page.click("nav >> text=Governance Policies");
  await page.waitForSelector("text=POL-001", { timeout: 10000 });

  await page.click("nav >> text=Audit Logs");
  await page.waitForSelector("text=FRAUD_ALERT_REVIEWED", { timeout: 10000 });

  console.log("[10/10] Verifying Reports & Settings...");
  await page.click("nav >> text=Reports");
  await page.waitForSelector("text=BigQuery Sandbox CSV Export", { timeout: 10000 });
  await page.click("text=Export BigQuery Sandbox CSVs");
  await page.waitForSelector("text=Exported 5 BigQuery Sandbox CSVs", { timeout: 20000 });

  await page.click("nav >> text=Settings");
  await page.waitForSelector("text=LOCAL MODE (DUCKDB)", { timeout: 10000 });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "10_settings.png") });

  await browser.close();

  console.log("Console Errors:", consoleErrors.length);
  console.log("HTTP 5xx Responses:", failedRequests.length);
  if (consoleErrors.length > 0) console.error(consoleErrors);
  if (failedRequests.length > 0) console.error(failedRequests);
  if (consoleErrors.length > 0 || failedRequests.length > 0) {
    process.exit(1);
  }
  console.log("[PASS] Complete E2E Playwright workflow verified with 0 console/5xx errors.");
}

run().catch((err) => {
  console.error("[FAIL] E2E Error:", err);
  process.exit(1);
});
