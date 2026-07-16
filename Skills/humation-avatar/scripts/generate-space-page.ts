#!/usr/bin/env bun

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

function help() {
  console.log(`Humation Avatar - zo.space route source helper

Usage:
  bun run Skills/humation-avatar/scripts/generate-space-page.ts [--output <path>]

Prints the internal Humation avatar builder TSX source saved in assets/humation-avatar-route.tsx.
Use the printed source with write_space_route() when creating a new zo.space route, or use edit_space_route() for updates to an existing route.
`);
}

const args = process.argv.slice(2);
if (args.includes("--help") || args.includes("-h")) {
  help();
  process.exit(0);
}

const here = dirname(fileURLToPath(import.meta.url));
const routeSourcePath = join(here, "..", "assets", "humation-avatar-route.tsx");
const source = readFileSync(routeSourcePath, "utf8");

const outputIndex = args.indexOf("--output");
if (outputIndex >= 0 && args[outputIndex + 1]) {
  await Bun.write(args[outputIndex + 1], source);
  console.log(args[outputIndex + 1]);
} else {
  console.log(source);
}
