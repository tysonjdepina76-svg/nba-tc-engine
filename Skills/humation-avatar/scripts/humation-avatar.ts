#!/usr/bin/env bun

type Part = { id: string; previewUrl: string };
type Group = {
  id: string;
  label: string;
  control: "select" | "toggle";
  defaultPart: string;
  parts: Part[];
  onPart?: string;
  offPart?: string;
};
type ColorSpec = {
  id: string;
  label: string;
  queryKey: string;
  default: string;
  allowTransparent?: boolean;
};
type TemplateItems = {
  id: string;
  name: string;
  groups: Group[];
  colors: ColorSpec[];
  renderSvgUrl: string;
};

const API_ORIGIN = "https://humation.app";
const TEMPLATE_ID = "humation-1-zo";
const ITEMS_URL = `${API_ORIGIN}/api/v1/templates/${TEMPLATE_ID}/items`;
const TEMPLATES_URL = `${API_ORIGIN}/api/v1/templates`;

const fallbackItems: TemplateItems = {
  id: TEMPLATE_ID,
  name: "Humation 🤝 Zo",
  renderSvgUrl: `/api/v1/templates/${TEMPLATE_ID}/render.svg`,
  groups: [
    { id: "head", label: "Head", control: "select", defaultPart: "001", parts: Array.from({ length: 24 }, (_, i) => ({ id: String(i + 1).padStart(3, "0"), previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/head/${String(i + 1).padStart(3, "0")}` })) },
    { id: "body", label: "Body", control: "select", defaultPart: "001", parts: Array.from({ length: 8 }, (_, i) => ({ id: String(i + 1).padStart(3, "0"), previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/body/${String(i + 1).padStart(3, "0")}` })) },
    { id: "bottom", label: "Bottom", control: "select", defaultPart: "001", parts: Array.from({ length: 8 }, (_, i) => ({ id: String(i + 1).padStart(3, "0"), previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/bottom/${String(i + 1).padStart(3, "0")}` })) },
    { id: "item", label: "Item", control: "select", defaultPart: "000", parts: ["000", "009", "010", "015", "011", "012", "008", "007", "006", "005", "004", "003", "002", "001", "014"].map((id) => ({ id, previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/item/${id}` })) },
    { id: "glasses", label: "Glasses", control: "select", defaultPart: "000", parts: ["000", "001", "002"].map((id) => ({ id, previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/glasses/${id}` })) },
    { id: "cat", label: "Cat", control: "select", defaultPart: "000", parts: ["000", "001", "002", "003", "004", "005", "011", "006", "007", "008", "009", "010"].map((id) => ({ id, previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/cat/${id}` })) },
    { id: "zo", label: "Go Zo", control: "toggle", defaultPart: "on", onPart: "on", offPart: "off", parts: ["off", "on"].map((id) => ({ id, previewUrl: `/api/v1/templates/${TEMPLATE_ID}/parts/zo/${id}` })) },
  ],
  colors: [
    { id: "background", label: "Background", queryKey: "bg", default: "F6F5F4", allowTransparent: true },
    { id: "stroke", label: "Stroke", queryKey: "color.stroke", default: "000000" },
    { id: "skin", label: "Skin", queryKey: "color.skin", default: "FFFFFF" },
    { id: "head", label: "Head", queryKey: "color.head", default: "000000" },
    { id: "body", label: "Body", queryKey: "color.body", default: "FFFFFF" },
    { id: "bottom", label: "Bottom", queryKey: "color.bottom", default: "000000" },
    { id: "zo", label: "Go Zo", queryKey: "color.zo", default: "FF6600" },
  ],
};

function printHelp() {
  console.log(`Humation Avatar CLI

Internal helper for Humation SVG avatar API.

Usage:
  bun run Skills/humation-avatar/scripts/humation-avatar.ts <command> [options]

Commands:
  templates              Fetch and print template list JSON
  items                  Fetch and print humation-1-zo item settings JSON
  url                    Print SVG render URL
  html                   Print HTML <img> snippet
  markdown               Print Markdown image snippet
  download               Download SVG to a file

Options for url/html/markdown/download:
  --head <id>            Head part, e.g. 001
  --body <id>            Body part, e.g. 001
  --bottom <id>          Bottom part, e.g. 001
  --item <id>            Item part. Mutually exclusive with --cat. Use 000 for off
  --glasses <id>         Glasses part. Use 000 for off
  --cat <id>             Cat part. Mutually exclusive with --item. Use 000 for off
  --zo <on|off>          Zo flag. Default: on
  --bg <hex|transparent> Background. Alias for --color.background
  --color.<id> <value>   Color override. ids: stroke, skin, head, body, bottom, zo
  --output <path>        Output file for download command
  --pretty               Pretty-print JSON for templates/items
  --help, -h             Show help

Examples:
  bun run Skills/humation-avatar/scripts/humation-avatar.ts url --zo on --color.zo FF6600
  bun run Skills/humation-avatar/scripts/humation-avatar.ts html --cat 001 --bg transparent --color.zo FF6600
  bun run Skills/humation-avatar/scripts/humation-avatar.ts download --output /home/workspace/avatar.svg --item 009
`);
}

function normalizeHex(value: string) {
  if (value === "transparent") return value;
  return value.replace("#", "").trim().toUpperCase();
}

function isActiveOptionalPart(value?: string) {
  return Boolean(value && value !== "000" && value !== "off");
}

function enforceExclusiveItemCat(parts: Record<string, string>, preferred?: "item" | "cat") {
  const itemActive = isActiveOptionalPart(parts.item);
  const catActive = isActiveOptionalPart(parts.cat);
  if (preferred === "item" && itemActive) parts.cat = "000";
  else if (preferred === "cat" && catActive) parts.item = "000";
  else if (itemActive && catActive) parts.cat = "000";
  return parts;
}

function parseArgs(argv: string[]) {
  const command = argv[0] || "help";
  const options: Record<string, string | boolean> = {};
  const positionals: string[] = [];

  for (let i = 1; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith("--")) {
      positionals.push(arg);
      continue;
    }
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      options[key] = true;
    } else {
      options[key] = next;
      i++;
    }
  }

  return { command, options, positionals };
}

async function fetchJson(url: string) {
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "Zo Computer Humation Avatar Skill",
    },
  });
  if (!res.ok) throw new Error(`Humation API returned ${res.status} for ${url}`);
  return res.json();
}

async function fetchItems(): Promise<TemplateItems> {
  try {
    return await fetchJson(ITEMS_URL);
  } catch {
    return fallbackItems;
  }
}

function defaultParts(items: TemplateItems) {
  return Object.fromEntries(items.groups.map((group) => [group.id, group.id === "zo" ? "on" : group.defaultPart]));
}

function defaultColors(items: TemplateItems) {
  return Object.fromEntries(items.colors.map((color) => [color.id, color.id === "zo" ? "FF6600" : color.default]));
}

function resolveOptions(items: TemplateItems, options: Record<string, string | boolean>) {
  const parts = defaultParts(items);
  const colors = defaultColors(items);
  let preferred: "item" | "cat" | undefined;

  for (const group of items.groups) {
    const value = options[group.id];
    if (typeof value === "string") {
      parts[group.id] = value;
      if (group.id === "item" || group.id === "cat") preferred = group.id;
    }
  }

  for (const color of items.colors) {
    const direct = options[`color.${color.id}`];
    const query = options[color.queryKey];
    const bg = color.id === "background" ? options.bg : undefined;
    const value = direct || query || bg;
    if (typeof value === "string") colors[color.id] = normalizeHex(value);
  }

  for (const [key, value] of Object.entries(options)) {
    if (!key.startsWith("color.") || typeof value !== "string") continue;
    const colorId = key.slice("color.".length);
    if (colorId in colors) colors[colorId] = normalizeHex(value);
  }

  return { parts: enforceExclusiveItemCat(parts, preferred), colors };
}

function buildUrl(items: TemplateItems, parts: Record<string, string>, colors: Record<string, string>) {
  const params = new URLSearchParams();
  const effectiveParts = enforceExclusiveItemCat({ ...parts });

  for (const group of items.groups) {
    params.set(group.id, effectiveParts[group.id] || group.defaultPart);
  }
  for (const color of items.colors) {
    const value = colors[color.id] || color.default;
    params.set(color.queryKey, value === "transparent" ? "transparent" : normalizeHex(value));
  }

  return `${API_ORIGIN}${items.renderSvgUrl}?${params.toString()}`;
}

async function main() {
  const { command, options } = parseArgs(process.argv.slice(2));

  if (command === "help" || options.help || options.h) {
    printHelp();
    return;
  }

  if (command === "templates") {
    const data = await fetchJson(TEMPLATES_URL);
    console.log(options.pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data));
    return;
  }

  if (command === "items") {
    const data = await fetchItems();
    console.log(options.pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data));
    return;
  }

  if (!["url", "html", "markdown", "download"].includes(command)) {
    console.error(`Unknown command: ${command}\n`);
    printHelp();
    process.exit(1);
  }

  const items = await fetchItems();
  const { parts, colors } = resolveOptions(items, options);
  const url = buildUrl(items, parts, colors);

  if (command === "url") {
    console.log(url);
    return;
  }

  if (command === "html") {
    console.log(`<img src="${url}" alt="Humation Zo avatar" />`);
    return;
  }

  if (command === "markdown") {
    console.log(`![Humation Zo avatar](${url})`);
    return;
  }

  if (command === "download") {
    const output = typeof options.output === "string" ? options.output : "humation-avatar.svg";
    const res = await fetch(url, { headers: { "User-Agent": "Zo Computer Humation Avatar Skill" } });
    if (!res.ok) throw new Error(`SVG download failed: ${res.status}`);
    await Bun.write(output, await res.text());
    console.log(output);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
