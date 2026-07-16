#!/usr/bin/env bun

import { createAvatar, createPartPreview, getPartsForSlot, getPartsForUiGroup, resolvePartId } from "@humation/core";
import { humation1 } from "@humation/assets-humation-1";
import type { HumationManifest } from "@humation/core";

const manifest = humation1 as HumationManifest;

type Options = Record<string, string | boolean>;

type ParsedArgs = {
  command: string;
  options: Options;
  positionals: string[];
};

const colorSlots = new Set(manifest.colors.map((color) => color.id));
const selectionSlots = new Set(manifest.selectionSlots.map((slot) => slot.id));
const outputFormats = new Set(["svg", "data-uri", "json", "html", "markdown"]);

function printHelp() {
  console.log(`Humation Local CLI

Local renderer for the OSS Humation avatar engine. No Humation API call is required.

Usage:
  bun run Skills/humation-avatar/scripts/humation-local.ts <command> [options]

Commands:
  render                 Render an avatar from seed and/or explicit selections
  parts                  List selectable parts
  preview                Render a single part preview
  manifest               Print manifest summary or full manifest
  agent-face             Create a ready-to-use SVG face for a Zo agent product

Options:
  --seed <text>          Deterministic seed. Same seed renders the same avatar
  --select <slot=part>   Explicit part selection. Repeatable. Example: --select head=braids
  --head <part>          Shortcut for --select head=<part>
  --body <part>          Shortcut for --select body=<part>
  --bottom <part>        Shortcut for --select bottom=<part>
  --bottom-color <hex>  Shortcut for --color bottom=<hex>
  --item <part>          Shortcut for --select item=<part>
  --glasses <part>       Shortcut for --select glasses=<part>
  --color <slot=hex>     Color override. Repeatable. Example: --color hair=4A3728
  --hair <hex>           Shortcut for --color hair=<hex>
  --skin <hex>           Shortcut for --color skin=<hex>
  --clothes <hex>        Shortcut for --color clothes=<hex>
  --stroke <hex>         Shortcut for --color stroke=<hex>
  --background <hex|transparent> Background color. Default: manifest default
  --crop <id>            Crop id. Default: avatar
  --format <type>        svg | data-uri | json | html | markdown. Default: svg
  --output <path>        Save output to a file instead of stdout
  --size <px>            HTML/Markdown display size. Default: 96
  --title <text>         HTML alt/title text. Default: Humation avatar
  --slot <id>            parts/preview slot filter
  --group <id>           parts/preview UI group filter
  --part <id|name>       preview part by id/name/alias
  --full                 manifest: print full manifest JSON
  --pretty               Pretty JSON output
  --help, -h             Show help

Examples:
  bun run Skills/humation-avatar/scripts/humation-local.ts render --seed user-123 --output /home/workspace/avatar.svg
  bun run Skills/humation-avatar/scripts/humation-local.ts render --head braids --body hoodie --item calico-cat --hair 4A3728 --format html
  bun run Skills/humation-avatar/scripts/humation-local.ts parts --slot head --pretty
  bun run Skills/humation-avatar/scripts/humation-local.ts preview --slot item --part black-cat --output /home/workspace/item-preview.svg
  bun run Skills/humation-avatar/scripts/humation-local.ts agent-face --seed support-agent --output /home/workspace/support-agent-face.svg
`);
}

function parseArgs(argv: string[]): ParsedArgs {
  const command = argv[0] || "help";
  const options: Options = {};
  const positionals: string[] = [];

  for (let i = 1; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith("--")) {
      positionals.push(arg);
      continue;
    }

    const eq = arg.indexOf("=");
    if (eq > 2) {
      const key = arg.slice(2, eq);
      const value = arg.slice(eq + 1);
      pushOption(options, key, value);
      continue;
    }

    const key = arg.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      pushOption(options, key, true);
    } else {
      pushOption(options, key, next);
      i++;
    }
  }

  return { command, options, positionals };
}

function pushOption(options: Options, key: string, value: string | boolean) {
  if (key === "select" || key === "color") {
    const existing = options[key];
    if (Array.isArray(existing)) {
      existing.push(value);
    } else if (existing !== undefined) {
      options[key] = [existing, value] as unknown as string;
    } else {
      options[key] = [value] as unknown as string;
    }
    return;
  }
  options[key] = value;
}

function valuesOf(option: string | boolean | string[] | undefined): string[] {
  if (Array.isArray(option)) return option.filter((value): value is string => typeof value === "string");
  return typeof option === "string" ? [option] : [];
}

function parsePairs(values: string[], label: string) {
  const pairs: Record<string, string> = {};
  for (const value of values) {
    const index = value.indexOf("=");
    if (index < 1) throw new Error(`${label} must use key=value format: ${value}`);
    pairs[value.slice(0, index)] = value.slice(index + 1);
  }
  return pairs;
}

function normalizeHex(value: string) {
  if (value === "transparent") return value;
  return value.replace(/^#/, "").trim().toUpperCase();
}

function titleCase(value: string) {
  return value.replace(/[-_]/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function getSelections(options: Options) {
  const selections = parsePairs(valuesOf(options.select as string | string[] | boolean | undefined), "--select");
  for (const slot of selectionSlots) {
    const value = options[slot];
    if (typeof value === "string") selections[slot] = value;
  }
  return selections;
}

function getColors(options: Options) {
  const colors = parsePairs(valuesOf(options.color as string | string[] | boolean | undefined), "--color");
  for (const slot of colorSlots) {
    if (selectionSlots.has(slot)) continue;
    const value = options[slot];
    if (typeof value === "string") colors[slot] = normalizeHex(value);
  }
  const bottomColor = options["bottom-color"] || options.bottomColor || options["color.bottom"];
  if (typeof bottomColor === "string") colors.bottom = normalizeHex(bottomColor);
  return colors;
}

function createAvatarOutput(options: Options) {
  const avatar = createAvatar(manifest, {
    seed: typeof options.seed === "string" ? options.seed : undefined,
    selections: getSelections(options),
    colors: getColors(options),
    background: typeof options.background === "string" ? normalizeHex(options.background) : undefined,
    crop: typeof options.crop === "string" ? options.crop : undefined,
  });

  const format = typeof options.format === "string" ? options.format : "svg";
  if (!outputFormats.has(format)) throw new Error(`Unknown format: ${format}`);

  if (format === "svg") return avatar.toString();
  if (format === "data-uri") return avatar.toDataUri();
  if (format === "json") return JSON.stringify(avatar.toJSON(), null, options.pretty ? 2 : 0);

  const title = typeof options.title === "string" ? options.title : "Humation avatar";
  const size = typeof options.size === "string" ? Number(options.size) : 96;
  const src = avatar.toDataUri();

  if (format === "html") {
    return `<img src="${src}" width="${size}" height="${size}" alt="${escapeAttr(title)}" title="${escapeAttr(title)}" />`;
  }

  return `![${title}](${src})`;
}

function listParts(options: Options) {
  const slot = typeof options.slot === "string" ? options.slot : undefined;
  const group = typeof options.group === "string" ? options.group : undefined;
  let parts = manifest.parts.filter((part) => !part.deprecated);
  if (slot) parts = getPartsForSlot(manifest, slot);
  if (group) parts = getPartsForUiGroup(manifest, group);

  const rows = parts.map((part) => ({
    id: part.id,
    slot: part.selectionSlot,
    name: part.name || "",
    label: part.name ? titleCase(part.name) : part.id,
    aliases: part.aliases || [],
    source: part.source,
    uiGroups: part.uiGroups,
  }));

  return JSON.stringify(rows, null, options.pretty ? 2 : 0);
}

function previewPart(options: Options) {
  const partInput = typeof options.part === "string" ? options.part : undefined;
  const slot = typeof options.slot === "string" ? options.slot : undefined;
  const group = typeof options.group === "string" ? options.group : undefined;

  let partId: string | undefined;
  if (partInput) {
    partId = resolvePartId(partInput, manifest, slot);
  } else if (slot) {
    partId = getPartsForSlot(manifest, slot)[0]?.id;
  } else if (group) {
    partId = getPartsForUiGroup(manifest, group)[0]?.id;
  } else {
    partId = manifest.parts[0]?.id;
  }

  if (!partId) throw new Error("No part found for preview");

  return createPartPreview(manifest, partId, {
    colors: getColors(options),
    background: typeof options.background === "string" ? normalizeHex(options.background) : "transparent",
  }).toString();
}

function manifestOutput(options: Options) {
  if (options.full) return JSON.stringify(manifest, null, options.pretty ? 2 : 0);
  return JSON.stringify({
    template: manifest.template,
    defaults: manifest.defaults,
    selectionSlots: manifest.selectionSlots,
    colors: manifest.colors,
    uiGroups: manifest.uiGroups,
    crops: manifest.crops,
    partCount: manifest.parts.length,
    aliases: manifest.aliases.length,
  }, null, options.pretty ? 2 : 0);
}

function agentFace(options: Options) {
  const seed = typeof options.seed === "string" ? options.seed : "zo-agent";
  const defaults: Options = {
    seed,
    background: typeof options.background === "string" ? options.background : "transparent",
    stroke: typeof options.stroke === "string" ? options.stroke : "09111F",
    hair: typeof options.hair === "string" ? options.hair : "101827",
    skin: typeof options.skin === "string" ? options.skin : "F8D7BD",
    clothes: typeof options.clothes === "string" ? options.clothes : "2F6BFF",
    color: [
      `bottom=${typeof options["bottom-color"] === "string" ? options["bottom-color"] : "101827"}`,
    ] as unknown as string,
    format: typeof options.format === "string" ? options.format : "svg",
    title: typeof options.title === "string" ? options.title : `${seed} face`,
    size: typeof options.size === "string" ? options.size : "128",
  };

  for (const key of ["head", "body", "item", "glasses", "select", "color", "crop", "output", "pretty"] as const) {
    if (options[key] !== undefined) defaults[key] = options[key];
  }

  return createAvatarOutput(defaults);
}

async function writeOrPrint(output: string, options: Options) {
  const path = typeof options.output === "string" ? options.output : undefined;
  if (!path) {
    console.log(output);
    return;
  }
  await Bun.write(path, output);
  console.log(path);
}

function escapeAttr(value: string) {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

async function main() {
  const { command, options } = parseArgs(process.argv.slice(2));

  if (command === "help" || command === "--help" || command === "-h" || options.help || options.h) {
    printHelp();
    return;
  }

  if (command === "render") {
    await writeOrPrint(createAvatarOutput(options), options);
    return;
  }

  if (command === "agent-face") {
    await writeOrPrint(agentFace(options), options);
    return;
  }

  if (command === "parts") {
    await writeOrPrint(listParts(options), options);
    return;
  }

  if (command === "preview") {
    await writeOrPrint(previewPart(options), options);
    return;
  }

  if (command === "manifest") {
    await writeOrPrint(manifestOutput(options), options);
    return;
  }

  console.error(`Unknown command: ${command}\n`);
  printHelp();
  process.exit(1);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
