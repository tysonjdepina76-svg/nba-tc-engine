---
name: humation-avatar
description: A Zo Computer skill for adding Humation avatars to agent products. It covers installing Humation npm packages into target projects, React integration, Core SVG rendering, static SVG generation, browser ESM usage in zo.space page routes, and legacy Humation SVG API compatibility.
compatibility: Created for Zo Computer
metadata:
  author: yusuke.zo.computer
  status: zo-user-ready
  version: 0.4.1
  created: 2026-05-16
  updated: 2026-07-06
  language: en
---
# Humation Avatar

Use this skill to add Humation avatars to Zo Computer agent products, web apps, UI prototypes, and static assets.

Humation is a hand-drawn deterministic SVG avatar engine. The same seed produces the same face, which makes it a good fit for stable agent identities, persona identities, user avatars, and product characters.

## What this skill does

When a Zo user wants to use Humation, first identify the target surface and choose the matching workflow.

| User goal | Default action |
| --- | --- |
| Show an agent avatar in a React / Vite / Next / Zo Site UI | Install `@humation/react` and `@humation/assets-humation-1` into the target project, then add an `<Avatar />` component |
| Generate SVG strings from an API route, CLI, worker, or server-side code | Install `@humation/core` and `@humation/assets-humation-1` into the target project, then use `createAvatar()` |
| Create a standalone SVG file | Use this skill's bundled CLI: `file scripts/humation-local.ts` |
| Use Humation in a zo.space page route | Do not install packages into zo.space. Use pinned browser ESM imports from `file esm.sh` inside the page route |
| Keep compatibility with the old Humation public SVG API URL | Use `file scripts/humation-avatar.ts` or the legacy API notes. Do this only when URL compatibility is required |

## Core rules

- For normal agent products, install Humation npm packages into the target project.
- Use `@humation/react` + `@humation/assets-humation-1` for React UI.
- Use `@humation/core` + `@humation/assets-humation-1` for raw SVG, backend, CLI, and worker code.
- Keep all `@humation/*` package versions aligned.
- zo.space page routes are the exception: do not run `npm install` or `bun add` in zo.space. Use pinned `file esm.sh` browser ESM imports instead.
- Use stable IDs as seeds: agent ID, persona ID, product slug, account ID, or user ID. Do not use display names as seeds.
- Save manually customized avatars as `{ seed, selections, colors, background }`.
- Use the legacy public SVG API only when backward compatibility is required. New work should use npm packages.

## Workflow 1: Add Humation to a React / Zo Site / web app

### 1. Inspect the target project

At the project root, check `file package.json`, lockfiles, README, and any project-level `file AGENTS.md`.

Choose the existing package manager:

- `bun.lock` -&gt; `bun add`
- `file pnpm-lock.yaml` -&gt; `pnpm add`
- `file package-lock.json` -&gt; `npm install`
- If unclear, inspect project docs or ask the user before installing

### 2. Install packages

For React UI:

```bash
npm install @humation/react @humation/assets-humation-1
# or
bun add @humation/react @humation/assets-humation-1
# or
pnpm add @humation/react @humation/assets-humation-1
```

### 3. Add an agent avatar component

```tsx
import { Avatar } from '@humation/react';
import { humation1 } from '@humation/assets-humation-1';

type AgentAvatarProps = {
  agentId: string;
  size?: number;
};

export function AgentAvatar({ agentId, size = 96 }: AgentAvatarProps) {
  return (
    <Avatar
      assets={humation1}
      seed={agentId}
      size={size}
      colors={{
        stroke: '#09111F',
        clothes: '#2F6BFF',
      }}
      background="transparent"
      title="Agent avatar"
    />
  );
}
```

### 4. Place it where the agent identity matters

Good locations:

- chat header
- agent card
- onboarding screen
- profile settings
- conversation participant list
- loading / empty state
- agent marketplace or directory cards

## Workflow 2: Generate SVG with Core

Use Core for API routes, servers, CLIs, workers, and non-React environments.

```bash
npm install @humation/core @humation/assets-humation-1
# or
bun add @humation/core @humation/assets-humation-1
# or
pnpm add @humation/core @humation/assets-humation-1
```

```ts
import { createAvatar } from '@humation/core';
import { humation1 } from '@humation/assets-humation-1';

export function renderAgentAvatarSvg(agentId: string) {
  return createAvatar(humation1, {
    seed: agentId,
    colors: {
      stroke: '#09111F',
      clothes: '#2F6BFF',
    },
    background: 'transparent',
  }).toString();
}
```

Return SVG from an HTTP endpoint:

```ts
const svg = renderAgentAvatarSvg(agentId);
return new Response(svg, {
  headers: {
    'content-type': 'image/svg+xml; charset=utf-8',
    'cache-control': 'public, max-age=31536000, immutable',
  },
});
```

## Workflow 3: Create static SVG files with the bundled CLI

Use the bundled CLI when the user only needs an SVG file, or when you want to prototype an agent face before integrating it into a project.

Create a ready-to-use agent face:

```bash
bun run Skills/humation-avatar/scripts/humation-local.ts agent-face 
  --seed support-agent 
  --output /home/workspace/support-agent-face.svg
```

Render from a seed:

```bash
bun run Skills/humation-avatar/scripts/humation-local.ts render 
  --seed user-123 
  --output /home/workspace/user-123-avatar.svg
```

Render explicit parts and colors:

```bash
bun run Skills/humation-avatar/scripts/humation-local.ts render 
  --head braids 
  --body hoodie 
  --item calico-cat 
  --hair 4A3728 
  --skin F4C9A8 
  --background transparent 
  --output /home/workspace/custom-avatar.svg
```

Inspect JSON state:

```bash
bun run Skills/humation-avatar/scripts/humation-local.ts render 
  --seed product-agent 
  --format json 
  --pretty
```

List parts and create a part preview:

```bash
bun run Skills/humation-avatar/scripts/humation-local.ts manifest --pretty
bun run Skills/humation-avatar/scripts/humation-local.ts parts --slot head --pretty
bun run Skills/humation-avatar/scripts/humation-local.ts preview 
  --slot item 
  --part black-cat 
  --output /home/workspace/item-preview.svg
```

## Workflow 4: Use Humation in a zo.space page route

zo.space routes have a fixed dependency environment. Do not install npm packages there. For page routes, use pinned browser ESM imports from `file esm.sh`.

```tsx
import { createAvatar, createPartPreview, getPartsForSlot } from 'https://esm.sh/@humation/core@1.0.1?bundle';
import { humation1 } from 'https://esm.sh/@humation/assets-humation-1@1.0.1?bundle';

const avatar = createAvatar(humation1, {
  seed: 'zo-agent-product',
  colors: { stroke: '#09111F', clothes: '#2F6BFF' },
  background: 'transparent',
});

const dataUri = avatar.toDataUri();
```

Rules for zo.space:

- URL ESM imports are OK in page routes.
- Do not use URL ESM imports in API routes.
- If backend-side Humation dependencies are needed, use a Zo Site or User Service instead.
- If a static avatar is enough, generate an SVG with the CLI, upload it with `update_space_asset()`, and render it as `<img src="/assets/...svg" />`.

Current demos:

- `https://yusuke.zo.space/humation-avatar` — package-based Humation builder
- `https://yusuke.zo.space/humation-agent` — example agent product page using Humation as the agent face

Both are public zo.space pages and use browser-side package rendering rather than the legacy public SVG API.

## Workflow 5: Add the official Avatar Builder UI

If the user needs a polished avatar builder in a shadcn project, use the official Humation block.

```bash
npx shadcn@latest add humation-labs/humation/avatar-builder
```

```tsx
import { AvatarBuilder } from '@/components/humation/avatar-builder';

<AvatarBuilder onChange={(state) => saveAvatar(state)} />
```

The block includes responsive preview, part picker, color sheet, randomize, PNG/SVG export, and JSON state copy. Prefer this block over inventing a simplified picker from scratch.

## State to persist

For seed-based avatars, persist the seed.

```ts
type SeedAvatarState = {
  seed: string;
};
```

For customized avatars, persist the full avatar state.

```ts
type HumationAvatarState = {
  seed?: string;
  selections: {
    head?: string;
    body?: string;
    bottom?: string;
    item?: string;
    glasses?: string;
  };
  colors: {
    stroke?: string;
    hair?: string;
    skin?: string;
    clothes?: string;
    bottom?: string;
  };
  background?: string | 'transparent';
};
```

## Common slots

Selection slots:

- `head`
- `body`
- `bottom`
- `item`
- `glasses`

Color slots:

- `stroke`
- `hair`
- `skin`
- `clothes`
- `bottom`
- `background`

Note: `bottom` is both a selection slot and a color slot. In the CLI, selection uses `--bottom <part>` and color uses `--bottom-color <hex>`.

## Implementation checklist

After implementing Humation, verify:

- The package manager matched the target project
- All `@humation/*` package versions are aligned
- The seed uses a stable ID
- The avatar renders correctly
- The avatar remains visible on dark and light backgrounds
- SVG/data URI/API response content types are correct
- The integration does not cause large layout shifts
- For zo.space routes, `get_space_errors()` is clean and `agent-browser` preview works

## Legacy Humation SVG API compatibility

Use the legacy API path only when an existing public SVG URL contract must be preserved.

```bash
bun run Skills/humation-avatar/scripts/humation-avatar.ts templates
bun run Skills/humation-avatar/scripts/humation-avatar.ts items
bun run Skills/humation-avatar/scripts/humation-avatar.ts url --zo on --color.zo FF6600
bun run Skills/humation-avatar/scripts/humation-avatar.ts download 
  --output /home/workspace/avatar.svg 
  --cat 001 
  --color.zo FF6600
```

Legacy API prototype rule: `item` and `cat` are mutually exclusive.

- If `item` is active, set `cat=000`
- If `cat` is active, set `item=000`
- Random generation must never enable both
- Apply the exclusivity rule again immediately before generating the final URL

## Skill files

- `file scripts/humation-local.ts` — npm-package-based Humation local renderer CLI
- `file scripts/humation-avatar.ts` — legacy Humation SVG API CLI
- `file references/oss-notes.md` — npm package / OSS Humation integration notes
- `file references/api-notes.md` — legacy API structure and query notes
- `file assets/example-zo-agent-face.svg` — agent-face example
- `file assets/example-seed-user-123.svg` — seed render example
- `file assets/example-black-cat-preview.svg` — part preview example
- `file SKILL.ja.md` — Japanese backup of the skill instructions

## Anti-patterns

Do not:

- Use the legacy public SVG API as the first choice for new work
- Run `npm install` or `bun add` inside a zo.space route
- Import `https://esm.sh/...` from a zo.space API route
- Use mutable display names as seeds
- Mix different versions of `@humation/core`, `@humation/react`, and `@humation/assets-humation-1`