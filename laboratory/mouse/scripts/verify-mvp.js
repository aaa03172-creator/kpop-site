const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const pagePath = path.join(root, "index.html");
const fixturePath = path.join(root, "fixtures", "sample_parse_results.json");
const distributionFixturePath = path.join(root, "fixtures", "sample_distribution_import.json");
const distributionParserPath = path.join(root, "scripts", "parse_distribution_workbook.py");

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

function pythonExecutable() {
  const bundled = path.join(
    os.homedir(),
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "python",
    process.platform === "win32" ? "python.exe" : "bin/python"
  );
  return fs.existsSync(bundled) ? bundled : "python";
}

function runPython(args, options = {}) {
  const result = spawnSync(pythonExecutable(), args, {
    cwd: root,
    encoding: "utf8",
    ...options
  });
  if (result.status !== 0) {
    throw new Error(`Python command failed: ${args.join(" ")}\n${result.stdout}\n${result.stderr}`);
  }
  return result;
}

function verifyDistributionParser() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "mouse-distribution-"));
  const workbookPath = path.join(tempDir, "distribution.xlsx");
  const parsedPath = path.join(tempDir, "distribution-parsed.json");
  const workbookScript = `
from pathlib import Path
from openpyxl import Workbook

workbook_path = Path(${JSON.stringify(workbookPath)})

wb = Workbook()
ws = wb.active
ws.title = "Mating"
ws.append(["Vet Med", "mating type", "Cage count", "mating cage count", "", "Medicine", "mating type", "Cage count", "mating cage count"])
ws.append(["Jang S.", "ApoMtg/tg", "6", "", "", "Kim S.", "GFAP Cre; S1PR1 fl/fl", "8", ""])
ws.append([None, "TAStg/+; TPMtg/+; ApoMtg/+", "16", "16", "", None, "Lyz2-cre+/-; S565Afl/fl", "8", ""])
wb.save(workbook_path)
`;
  runPython(["-c", workbookScript]);
  runPython([distributionParserPath, workbookPath, "--sheet", "Mating", "--out", parsedPath]);

  const parsed = JSON.parse(fs.readFileSync(parsedPath, "utf8"));
  assert(parsed.layer === "parsed or intermediate result", "Parsed distribution output must stay non-canonical.");
  assert(parsed.sheet_name === "Mating", "Distribution parser used the wrong sheet.");
  assert(parsed.detected_blocks.length === 2, "Distribution parser did not detect both column blocks.");
  assert(parsed.rows.some((row) => row.mating_type_raw === "ApoMtg/tg"), "Distribution parser missed the ApoMtg/tg row.");
  assert(
    parsed.rows.some((row) => row.responsible_person_raw === "Jang S." && row.mating_type_raw.startsWith("TAStg")),
    "Distribution parser did not carry down merged/person context."
  );
  assert(
    parsed.rows.every((row) => row.source_row_number && row.source_cells),
    "Distribution parser rows must preserve source row and cell traceability."
  );
  return parsedPath;
}

async function main() {
  assert(fs.existsSync(pagePath), "index.html is missing.");
  assert(fs.existsSync(fixturePath), "fixtures/sample_parse_results.json is missing.");
  assert(fs.existsSync(distributionFixturePath), "fixtures/sample_distribution_import.json is missing.");
  assert(fs.existsSync(distributionParserPath), "Distribution workbook parser is missing.");
  const generatedDistributionPath = verifyDistributionParser();

  const html = fs.readFileSync(pagePath, "utf8");
  const scriptMatch = html.match(/<script>([\s\S]*)<\/script>/);
  assert(scriptMatch, "index.html must contain an inline script.");
  new Function(scriptMatch[1]);

  const referencedIds = [...scriptMatch[1].matchAll(/getElementById\("([^"]+)"\)/g)].map((match) => match[1]);
  const missingIds = [...new Set(referencedIds)].filter((id) => !html.includes(`id="${id}"`));
  assert(!missingIds.length, `Missing DOM ids: ${missingIds.join(", ")}`);

  const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const distributionFixture = JSON.parse(fs.readFileSync(distributionFixturePath, "utf8"));
  assert(fixture.layer === "parsed or intermediate result", "Fixture layer must stay non-canonical.");
  assert(Array.isArray(fixture.records) && fixture.records.length >= 3, "Fixture must contain at least three parse records.");
  assert(
    fixture.records.some((record) => record.status === "review") &&
      fixture.records.some((record) => record.status === "conflict") &&
      fixture.records.some((record) => record.status === "auto"),
    "Fixture should cover review, conflict, and auto-filled states."
  );
  assert(distributionFixture.layer === "parsed or intermediate result", "Distribution fixture must stay non-canonical.");
  assert(Array.isArray(distributionFixture.rows) && distributionFixture.rows.length >= 3, "Distribution fixture should contain parsed assignment rows.");

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
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await page.waitForSelector("#inboxRows tr");

  assert((await page.locator("#inboxRows tr").count()) >= 5, "Seed inbox rows did not render.");
  assert((await page.locator("#reviewSummary").textContent()).includes("3 pending"), "Initial review count is wrong.");
  assert(
    (await page.locator("#assignedStrainRows tr").filter({ hasText: "ApoM Tg/Tg" }).filter({ hasText: "Canonical scope" }).count()) === 1,
    "My Assigned Strains seed scope missing."
  );

  await page.getByRole("button", { name: "Load Distribution Fixture" }).click();
  assert(
    (await page.locator("#distributionSummary").textContent()).includes("20260407"),
    "Distribution fixture did not update settings summary."
  );
  assert(
    (await page.locator("#distributionRows tr").filter({ hasText: "ApoMtg/tg" }).count()) === 1,
    "Distribution fixture assignment row missing."
  );
  assert(
    (await page.locator("#distributionSuggestionRows tr").filter({ hasText: "ApoMtg/tg" }).filter({ hasText: "Possible alias for ApoM Tg/Tg" }).count()) === 1,
    "Distribution fixture did not create a reviewable strain candidate suggestion."
  );
  assert(
    (await page.locator("#recordRows tr").filter({ hasText: "ApoMtg/tg" }).count()) === 0,
    "Distribution assignment leaked into canonical mouse records."
  );
  await page.reload();
  await page.waitForFunction(() => document.querySelector("#distributionRows")?.textContent.includes("TAStg/+; TPMtg/+; ApoMtg/+"));
  assert(
    (await page.locator("#distributionRows tr").filter({ hasText: "TAStg/+; TPMtg/+; ApoMtg/+" }).count()) === 1,
    "Distribution import did not persist after reload."
  );

  await page.getByRole("button", { name: "Load Sample Fixture" }).click();
  await page.waitForSelector("#reviewRows tr");
  assert((await page.locator("#inboxRows tr").filter({ hasText: "FIXTURE-AUTO-MATING" }).count()) === 1, "Embedded fixture mating row missing.");
  assert((await page.locator("#reviewRows tr").filter({ hasText: "Count mismatch" }).count()) >= 1, "Embedded fixture did not route count mismatch to review.");
  assert((await page.locator("#reviewRows tr").filter({ hasText: "FIXTURE-DUPLICATE-ACTIVE" }).count()) === 1, "Embedded fixture did not route duplicate active mouse to review.");
  await page.getByRole("button", { name: "Reset Local" }).click();
  await page.waitForSelector("#inboxRows tr");
  assert((await page.locator("#inboxRows tr").filter({ hasText: "FIXTURE-AUTO-MATING" }).count()) === 0, "Reset did not remove embedded fixture rows.");
  assert((await page.locator("#distributionRows tr").filter({ hasText: "ApoMtg/tg" }).count()) === 0, "Reset did not remove distribution assignment rows.");

  const outsideScopeFixturePath = path.join(os.tmpdir(), `outside-scope-${Date.now()}.json`);
  fs.writeFileSync(outsideScopeFixturePath, JSON.stringify({
    layer: "parsed or intermediate result",
    records: [
      {
        id: "FIXTURE-OUTSIDE-SCOPE",
        uploaded: "Fixture import",
        type: "Separated",
        rawStrain: "GFAP Cre; S1PR1 fl/fl",
        matchedStrain: "GFAP Cre; S1PR1 fl/fl",
        dobRaw: "26.01.01",
        dobNormalized: "2026-01-01",
        mouseCount: "2 total",
        confidence: 96,
        status: "auto",
        issue: "Fixture auto-filled by policy",
        severity: "Low",
        reviewField: "matchedStrain",
        currentValue: "GFAP Cre; S1PR1 fl/fl",
        suggestedValue: "GFAP Cre; S1PR1 fl/fl",
        reviewReason: "Tests assigned scope validation.",
        notes: [
          { raw: "GF101 R'", meaning: "Mouse GF101, right prime ear label (R_PRIME)", strike: "none" },
          { raw: "GF102 L'", meaning: "Mouse GF102, left prime ear label (L_PRIME)", strike: "none" }
        ],
        actions: ["Import as parsed result."]
      }
    ]
  }), "utf8");
  await page.getByRole("button", { name: "Import Parse JSON" }).click();
  await page.setInputFiles("#parseInput", outsideScopeFixturePath);
  await page.waitForSelector("#reviewRows tr");
  assert(
    (await page.locator("#reviewRows tr").filter({ hasText: "FIXTURE-OUTSIDE-SCOPE" }).filter({ hasText: "Outside assigned strain scope" }).count()) === 1,
    "Outside assigned strain scope fixture was not routed to review."
  );
  assert(
    (await page.locator("#recordRows tr").filter({ hasText: "FIXTURE-OUTSIDE-SCOPE" }).count()) === 0,
    "Outside assigned strain scope fixture leaked into canonical candidates."
  );
  await page.getByRole("button", { name: "Reset Local" }).click();
  await page.waitForSelector("#inboxRows tr");

  await page.getByRole("button", { name: "Import Distribution JSON" }).click();
  await page.setInputFiles("#distributionInput", generatedDistributionPath);
  await page.waitForFunction(() => document.querySelector("#distributionRows")?.textContent.includes("TAStg/+; TPMtg/+; ApoMtg/+"));
  assert(
    (await page.locator("#distributionRows tr").filter({ hasText: "ApoMtg/tg" }).count()) === 1,
    "Distribution parser JSON import row missing."
  );
  assert(
    (await page.locator("#distributionSuggestionRows tr").filter({ hasText: "GFAP Cre; S1PR1 fl/fl" }).filter({ hasText: "New candidate" }).count()) === 1,
    "Distribution parser JSON import did not create a new candidate review signal."
  );
  assert(
    (await page.locator("#recordRows tr").filter({ hasText: "ApoMtg/tg" }).count()) === 0,
    "Distribution parser JSON import leaked into canonical mouse records."
  );
  await page.getByRole("button", { name: "Reset Local" }).click();
  await page.waitForSelector("#inboxRows tr");

  await page.getByRole("button", { name: "Import Parse JSON" }).click();
  await page.setInputFiles("#parseInput", fixturePath);
  await page.waitForSelector("#reviewRows tr");
  assert((await page.locator("#inboxRows tr").filter({ hasText: "FIXTURE-LOW-STRAIN" }).count()) === 1, "Fixture import row missing.");
  assert((await page.locator("#reviewRows tr").filter({ hasText: "FIXTURE-MATING-CONFLICT" }).count()) === 1, "Fixture conflict row missing.");
  assert((await page.locator("#reviewRows tr").filter({ hasText: "Count mismatch" }).count()) >= 1, "Count mismatch validation did not create a review item.");
  assert((await page.locator("#reviewRows tr").filter({ hasText: "FIXTURE-DUPLICATE-ACTIVE" }).count()) === 1, "Duplicate active mouse validation did not create a review item.");

  await page.getByRole("button", { name: "Colony Records" }).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll("#recordRows tr")].some((row) => row.textContent.includes("FIXTURE-AUTO-SEPARATED"))
  );
  assert((await page.locator("#recordRows tr").filter({ hasText: "MT321" }).count()) >= 1, "Auto fixture mouse candidate missing.");
  assert((await page.locator("#recordRows tr").filter({ hasText: "Moved candidate" }).count()) >= 1, "Strike-through candidate status missing.");
  assert((await page.locator("#recordRows tr").filter({ hasText: "MT401" }).count()) === 0, "Count mismatch fixture leaked into canonical candidates.");
  assert((await page.locator("#recordRows tr").filter({ hasText: "FIXTURE-DUPLICATE-ACTIVE" }).count()) === 0, "Duplicate active fixture leaked into canonical candidates.");

  await page.getByRole("button", { name: "Review Queue" }).click();
  await page.locator("#reviewRows tr").filter({ hasText: "FIXTURE-DUPLICATE-ACTIVE" }).click();
  const duplicateReviewCount = await page.locator("#reviewRows tr").count();
  await page.locator("#afterValue").fill("Reviewed duplicate without movement");
  await page.getByRole("button", { name: "Apply Reviewed Changes" }).click();
  await page.waitForTimeout(50);
  assert((await page.locator("#reviewRows tr").count()) === duplicateReviewCount, "Duplicate active mouse was accepted without movement review.");
  await page.locator("#movementReason").fill("Reviewed card evidence closes the previous active snapshot before accepting this source.");
  await page.getByRole("button", { name: "Resolve Mouse Movement" }).click();
  await page.waitForTimeout(50);
  assert((await page.locator("#reviewRows tr").count()) === duplicateReviewCount - 1, "Duplicate active mouse resolution did not leave the review queue.");
  await page.getByRole("button", { name: "Colony Records" }).click();
  assert((await page.locator("#recordRows tr").filter({ hasText: "FIXTURE-DUPLICATE-ACTIVE" }).count()) >= 1, "Resolved duplicate source did not create reviewed canonical candidates.");
  assert((await page.locator("#recordRows tr").filter({ hasText: "Closed by movement review" }).count()) >= 1, "Previous active source was not marked closed by movement review.");

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
  await page.waitForFunction(() =>
    [...document.querySelectorAll("#inboxRows tr")].some((row) => row.textContent.includes("UPLOAD-"))
  );
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
  assert(await page.locator("#exportStrainSelect").isEnabled(), "Export strain selector should be enabled when accepted strains exist.");
  assert(
    (await page.locator("#exportStrainSelect option", { hasText: "ApoM Tg/Tg" }).count()) === 1,
    "Export strain selector did not list the accepted separation strain."
  );
  assert(
    (await page.locator("#separationFilenamePreview").textContent()).endsWith("분리 현황표.xlsx"),
    "Separation filename preview is missing the lab filename pattern."
  );
  assert((await page.locator("#separationExportStatus").textContent()).includes("row"), "Separation export status did not show ready rows.");
  assert(await page.locator("#downloadSeparationXlsx").isEnabled(), "Separation XLSX button should be enabled when accepted rows exist.");
  assert(
    (await page.locator("#animalsheetFilenamePreview").textContent()).endsWith("animal sheet.xlsx"),
    "Animal sheet filename preview is missing the lab filename pattern."
  );
  assert((await page.locator("#animalsheetExportStatus").textContent()).includes("row"), "Animal sheet export status did not show ready rows.");
  assert(await page.locator("#downloadAnimalsheetXlsx").isEnabled(), "Animal sheet XLSX button should be enabled when accepted rows exist.");
  assert((await page.locator("#workbookPreviewTitle").textContent()) === "Separation workbook preview", "Separation workbook preview title missing.");
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "Sampling point" }).count()) === 1,
    "Separation preview is missing the Sampling point template column."
  );
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "FIXTURE-AUTO-SEPARATED" }).count()) === 1,
    "Accepted separated fixture missing from separation workbook preview."
  );
  await page.getByRole("button", { name: "Preview Animalsheet" }).click();
  assert(
    (await page.locator("#exportStrainSelect option", { hasText: "ApoM Tg/Tg" }).count()) === 1,
    "Export strain selector did not list the accepted mating strain."
  );
  assert((await page.locator("#workbookPreviewTitle").textContent()) === "Animal sheet preview", "Animalsheet preview title missing.");
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "Cage No." }).count()) === 1,
    "Animalsheet preview is missing the Cage No. template column."
  );
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "FIXTURE-AUTO-MATING" }).count()) === 1,
    "Accepted mating fixture missing from animalsheet preview."
  );
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "F1" }).count()) === 1,
    "Accepted mating fixture did not render a litter row."
  );
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "Source evidence" }).count()) === 1,
    "Animalsheet preview is missing source evidence column."
  );
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "MT321" }).count()) >= 1 &&
      (await page.locator("#workbookPreviewTable").filter({ hasText: "MT322" }).count()) >= 1,
    "Animalsheet preview did not split parent IDs into rows."
  );
  assert(
    (await page.locator("#workbookPreviewTable tr").filter({ hasText: "Litter" }).filter({ hasText: "10" }).count()) >= 1,
    "Animalsheet preview did not map pup count into the Pubs column."
  );
  assert(
    (await page.locator("#workbookPreviewTable").filter({ hasText: "26.04.13 - 10p" }).count()) === 1,
    "Litter note evidence missing from animalsheet preview."
  );
  const downloadDir = fs.mkdtempSync(path.join(os.tmpdir(), "mouse-xlsx-"));
  const [separationXlsx] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download Separation XLSX" }).click()
  ]);
  const separationXlsxPath = path.join(downloadDir, separationXlsx.suggestedFilename());
  await separationXlsx.saveAs(separationXlsxPath);
  assert(separationXlsx.suggestedFilename().endsWith(".xlsx"), "Unexpected separation XLSX filename.");
  const separationWorkbook = fs.readFileSync(separationXlsxPath);
  const separationWorkbookText = separationWorkbook.toString("utf8");
  assert(separationWorkbook.subarray(0, 4).toString("hex") === "504b0304", "Separation XLSX is not a ZIP-based workbook.");
  assert(separationWorkbookText.includes("Sampling point"), "Separation XLSX is missing the template header.");
  assert(separationWorkbookText.includes("FIXTURE-AUTO-SEPARATED"), "Separation XLSX is missing accepted source traceability.");
  assert(!separationWorkbookText.includes("FIXTURE-COUNT-MISMATCH"), "Separation XLSX included a count mismatch review item.");
  assert(!separationWorkbookText.includes("FIXTURE-MATING-CONFLICT"), "Separation XLSX included a blocked mating conflict.");
  const [animalsheetXlsx] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download Animal Sheet XLSX" }).click()
  ]);
  const animalsheetXlsxPath = path.join(downloadDir, animalsheetXlsx.suggestedFilename());
  await animalsheetXlsx.saveAs(animalsheetXlsxPath);
  assert(animalsheetXlsx.suggestedFilename().endsWith("animal sheet.xlsx"), "Unexpected animal sheet XLSX filename.");
  const animalsheetWorkbook = fs.readFileSync(animalsheetXlsxPath);
  const animalsheetWorkbookText = animalsheetWorkbook.toString("utf8");
  assert(animalsheetWorkbook.subarray(0, 4).toString("hex") === "504b0304", "Animal sheet XLSX is not a ZIP-based workbook.");
  assert(animalsheetWorkbookText.includes("Source evidence"), "Animal sheet XLSX is missing the evidence header.");
  assert(animalsheetWorkbookText.includes("MT321") && animalsheetWorkbookText.includes("MT322"), "Animal sheet XLSX is missing parsed parent IDs.");
  assert(animalsheetWorkbookText.includes("26.04.13 - 10p"), "Animal sheet XLSX is missing litter note evidence.");
  assert(!animalsheetWorkbookText.includes("FIXTURE-MATING-CONFLICT"), "Animal sheet XLSX included a blocked mating conflict.");
  assert(
    (await page.locator("#exportLogRows tr").filter({ hasText: "XLSX generated from workbook preview" }).count()) >= 1,
    "XLSX exports were not recorded in the export log."
  );
  const blockedSource = await blockedDetailRows.first().locator("td").first().textContent();
  await blockedDetailRows.first().evaluate((row) => row.click());
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
