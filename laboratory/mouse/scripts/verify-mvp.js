const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const pagePath = path.join(root, "index.html");
const fixturePath = path.join(root, "fixtures", "sample_parse_results.json");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function fileUrl(filePath) {
  return `file:///${filePath.replace(/\\/g, "/")}`;
}

function makeTinyPng() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "mouse-lims-"));
  const pngPath = path.join(tempDir, "card-photo.png");
  const pngBase64 =
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAGklEQVR4nGNk+M+ABzAOMoCJYQ3DhhQAAO8SARKa6CdmAAAAAElFTkSuQmCC";
  fs.writeFileSync(pngPath, Buffer.from(pngBase64, "base64"));
  return pngPath;
}

async function main() {
  assert(fs.existsSync(pagePath), "index.html is missing.");
  assert(fs.existsSync(fixturePath), "fixtures/sample_parse_results.json is missing.");

  const html = fs.readFileSync(pagePath, "utf8");
  const scriptMatch = html.match(/<script>([\s\S]*)<\/script>/);
  assert(scriptMatch, "index.html must contain an inline script.");
  new Function(scriptMatch[1]);

  const referencedIds = [...scriptMatch[1].matchAll(/getElementById\("([^"]+)"\)/g)].map((match) => match[1]);
  const missingIds = [...new Set(referencedIds)].filter((id) => !html.includes(`id="${id}"`));
  assert(!missingIds.length, `Missing DOM ids: ${missingIds.join(", ")}`);

  const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  assert(fixture.layer === "parsed or intermediate result", "Fixture layer must stay non-canonical.");
  assert(Array.isArray(fixture.records) && fixture.records.length >= 3, "Fixture must contain at least three parse records.");
  assert(
    fixture.records.some((record) => record.status === "review") &&
      fixture.records.some((record) => record.status === "conflict") &&
      fixture.records.some((record) => record.status === "auto"),
    "Fixture should cover review, conflict, and auto-filled states."
  );

  const uploadPath = makeTinyPng();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  const browserErrors = [];

  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      browserErrors.push(message.text());
    }
  });

  await page.goto(fileUrl(pagePath));
  await page.waitForSelector("#inboxRows tr");

  assert((await page.locator("#inboxRows tr").count()) >= 5, "Seed inbox rows did not render.");
  assert((await page.locator("#reviewSummary").textContent()).includes("3 pending"), "Initial review count is wrong.");

  await page.getByRole("button", { name: "Import Parse JSON" }).click();
  await page.setInputFiles("#parseInput", fixturePath);
  await page.waitForSelector("#reviewRows tr");
  assert((await page.locator("#inboxRows tr").filter({ hasText: "FIXTURE-LOW-STRAIN" }).count()) === 1, "Fixture import row missing.");
  assert((await page.locator("#reviewRows tr").filter({ hasText: "FIXTURE-MATING-CONFLICT" }).count()) === 1, "Fixture conflict row missing.");

  await page.getByRole("button", { name: "Colony Records" }).click();
  assert((await page.locator("#recordRows tr").filter({ hasText: "MT318" }).count()) >= 1, "Auto fixture mouse candidate missing.");
  assert((await page.locator("#recordRows tr").filter({ hasText: "Moved candidate" }).count()) >= 1, "Strike-through candidate status missing.");

  await page.getByRole("button", { name: "Review Queue" }).click();
  await page.locator("#reviewRows tr").first().click();
  const beforeReviewCount = await page.locator("#reviewRows tr").count();
  await page.locator("#afterValue").fill("Reviewed configured value");
  await page.getByRole("button", { name: "Apply Reviewed Changes" }).click();
  await page.waitForTimeout(50);
  assert((await page.locator("#reviewRows tr").count()) === beforeReviewCount - 1, "Reviewed correction did not leave the queue.");

  await page.getByRole("button", { name: "Colony Records" }).click();
  assert((await page.locator("#recordRows tr").filter({ hasText: "Reviewed configured value" }).count()) >= 1, "Reviewed record candidate missing.");

  await page.getByRole("button", { name: "Review Queue" }).click();
  await page.locator("#reviewRows tr").first().click();
  const dismissedSource = await page.locator("#drawerTitle").textContent();
  const dismissCountBeforeReason = await page.locator("#reviewRows tr").count();
  await page.getByRole("button", { name: "Dismiss With Reason" }).click();
  assert(
    (await page.locator("#reviewRows tr").count()) === dismissCountBeforeReason,
    "Dismissed review item without a required reason."
  );
  await page.locator("#dismissReason").fill("Not actionable for this MVP slice");
  await page.getByRole("button", { name: "Dismiss With Reason" }).click();
  await page.getByRole("button", { name: "Colony Records" }).click();
  assert(
    (await page.locator("#recordRows tr").filter({ hasText: dismissedSource }).count()) === 0,
    "Dismissed review item leaked into canonical candidates."
  );

  await page.getByRole("button", { name: "Photo Inbox" }).click();
  await page.setInputFiles("#photoInput", uploadPath);
  await page.waitForFunction(() => document.querySelector("#reviewSummary").textContent.includes("pending"));
  assert((await page.locator("#inboxRows tr").filter({ hasText: "UPLOAD-" }).count()) === 1, "Uploaded source photo row missing.");

  await page.reload();
  await page.waitForSelector("#inboxRows tr");
  assert((await page.locator("#inboxRows tr").filter({ hasText: "UPLOAD-" }).count()) === 1, "Local source photo session did not persist after reload.");
  assert((await page.locator("#inboxRows tr").filter({ hasText: "FIXTURE-AUTO-SEPARATED" }).count()) === 1, "Imported parse fixture did not persist after reload.");

  await page.getByRole("button", { name: "Exports" }).click();
  const blockedDetailRows = page.locator("#blockedExportRows tr[data-id]");
  assert(
    (await blockedDetailRows.count()) >= 1,
    "Blocked export detail rows missing."
  );
  const blockedSource = await blockedDetailRows.first().locator("td").first().textContent();
  await blockedDetailRows.first().click();
  assert((await page.locator("#drawerTitle").textContent()) === blockedSource, "Blocked export row did not open review evidence.");
  await page.getByRole("button", { name: "Exports" }).click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Generate Separation CSV" }).click()
  ]);
  assert(download.suggestedFilename() === "separation_export_preview.csv", "Unexpected export filename.");
  assert(
    (await page.locator("#exportLogRows tr").filter({ hasText: "Preview generated" }).count()) >= 1,
    "Export attempt log did not record the generated preview."
  );
  assert(
    (await page.locator("#exportLogRows tr").filter({ hasText: "blocked rows excluded" }).count()) >= 1,
    "Export log did not preserve blocked-row context."
  );

  assert(!browserErrors.length, `Browser errors: ${browserErrors.join(" | ")}`);
  await browser.close();
  console.log("MVP verification passed.");
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
