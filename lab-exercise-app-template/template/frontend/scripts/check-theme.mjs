#!/usr/bin/env node
/*
 * Brand guard (spec §13): fail the build on any raw hex colour outside theme.css.
 *
 * The CPDSE identity lives entirely in src/theme.css; every other file must read the
 * CSS variables. This catches the most common drift — someone hard-coding "#3C5E3E"
 * (or an off-palette colour, or an invented error red) in a component.
 *
 * SVG assets are allowed to contain hex (the logos are brand artwork).
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, extname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const SRC = join(fileURLToPath(new URL(".", import.meta.url)), "..", "src");
const SCANNED_EXT = new Set([".ts", ".tsx", ".css", ".js", ".jsx", ".html"]);
const ALLOWLIST = new Set(["theme.css"]);
const HEX = /#[0-9a-fA-F]{3,8}\b/g;

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

const violations = [];
for (const file of walk(SRC)) {
  if (!SCANNED_EXT.has(extname(file))) continue;
  if (ALLOWLIST.has(basename(file))) continue;
  const text = readFileSync(file, "utf8");
  text.split(/\r?\n/).forEach((line, i) => {
    const matches = line.match(HEX);
    if (matches) {
      violations.push(`${relative(SRC, file)}:${i + 1}  ${matches.join(", ")}  ->  ${line.trim()}`);
    }
  });
}

if (violations.length) {
  console.error("\n✗ Raw hex colours found outside theme.css (spec §13):\n");
  for (const v of violations) console.error("  " + v);
  console.error(
    "\nUse a CSS variable from theme.css instead (e.g. var(--forest)). " +
      "Only the six approved fill/ink pairs are permitted; the palette has no red/amber.\n",
  );
  process.exit(1);
}
console.log("✓ theme check passed: no raw hex outside theme.css");
