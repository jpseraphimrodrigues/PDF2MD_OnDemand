const fs = require("node:fs");
const path = require("node:path");

const frontendRoot = path.resolve(__dirname, "..");
const output = path.join(frontendRoot, "dist", "licenses");
fs.mkdirSync(output, {recursive: true});

const lock = JSON.parse(fs.readFileSync(path.join(frontendRoot, "package-lock.json"), "utf8"));
const notices = [];

for (const [packagePath, metadata] of Object.entries(lock.packages)) {
  if (!packagePath.startsWith("node_modules/") || metadata.dev || metadata.devOptional) continue;
  const absolutePath = path.join(frontendRoot, packagePath);
  if (!fs.existsSync(path.join(absolutePath, "package.json"))) continue;
  const licenseFiles = fs.readdirSync(absolutePath)
    .filter(file => /^(license|licence|copying)([-_.].*)?$/i.test(file))
    .sort();
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(absolutePath, "package.json"), "utf8"),
  );
  const heading = `${packageJson.name}@${packageJson.version}`;
  if (licenseFiles.length) {
    notices.push(`===== ${heading} (${packageJson.license || "license files"}) =====\n`);
    for (const licenseFile of licenseFiles) {
      notices.push(`--- ${licenseFile} ---\n`);
      notices.push(fs.readFileSync(path.join(absolutePath, licenseFile), "utf8"));
    }
  } else {
    notices.push(`===== ${heading} (${packageJson.license || "license file missing"}) =====\n`);
  }
  notices.push("\n");
}

fs.writeFileSync(
  path.join(output, "THIRD_PARTY_NOTICES.txt"),
  notices.join(""),
  "utf8",
);
