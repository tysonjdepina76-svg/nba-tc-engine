# Humation OSS Notes

Humation OSS repo: https://github.com/humation-labs/humation

Humation is a hand-drawn deterministic SVG avatar engine. One seed in, one deterministic avatar out. Rendering is local: no AI generation and no Humation API call is required.

## Packages

| package | use |
| --- | --- |
| `@humation/core` | Manifest validation, SVG rendering, and UI helpers |
| `@humation/assets-humation-1` | Humation 1 manifest and embedded SVG assets |
| `@humation/react` | React `<Avatar>` component |
| `@humation/web-component` | `<humation-avatar>` custom element |

For normal Agent avatar/product integration, install the relevant npm packages into the target project. Keep `@humation/*` package versions in sync.

React UI:

```bash
npm install @humation/react @humation/assets-humation-1
```

Core / server / CLI / raw SVG:

```bash
npm install @humation/core @humation/assets-humation-1
```

## Zo skill setup

This skill has a local `package.json` and `bun.lock` so scripts can render Humation SVGs directly from Zo Computer:

```bash
cd /home/workspace/Skills/humation-avatar
bun install
```

Current package version checked on 2026-07-06: `1.0.1`.

## Local rendering

```ts
import { createAvatar } from '@humation/core';
import { humation1 } from '@humation/assets-humation-1';

const svg = createAvatar(humation1, {
  seed: 'support-agent',
  colors: { stroke: '#09111F', clothes: '#2F6BFF' },
  background: 'transparent',
}).toString();
```

## React rendering

```tsx
import { Avatar } from '@humation/react';
import { humation1 } from '@humation/assets-humation-1';

<Avatar assets={humation1} seed={user.id} size={96} />
```

`seed` generates deterministic selections. `selections` overrides any seeded slot.

```tsx
<Avatar
  assets={humation1}
  selections={{ head: 'braids', body: 'hoodie', item: 'calico-cat' }}
  colors={{ hair: '#4A3728', skin: '#F4C9A8' }}
/>
```

## Slots

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

Note: `bottom` is both a selection slot and a color slot. In the local CLI, selection uses `--bottom <part>` and color uses `--bottom-color <hex>` or `--color bottom=<hex>`.

## State persistence

Persist one of:

1. seed-based avatar: `seed`
2. manually customized avatar: `{ selections, colors, background, crop }`

Part names and aliases are accepted by `createAvatar`; canonical IDs are also supported. For long-term storage, canonical IDs are safest, while names are more human-readable.

## Picker helpers

```ts
import { createPartPreview, getPartsForSlot, getPartsForUiGroup } from '@humation/core';
import { humation1 } from '@humation/assets-humation-1';

const heads = getPartsForSlot(humation1, 'head');
const cats = getPartsForUiGroup(humation1, 'item').filter((part) => part.name?.includes('cat'));
const preview = createPartPreview(humation1, heads[0], {
  colors: { hair: '#4A3728' },
  background: 'transparent',
}).toDataUri();
```

## Official shadcn avatar builder

Install in a shadcn project:

```bash
npx shadcn@latest add humation-labs/humation/avatar-builder
```

Then:

```tsx
import { AvatarBuilder } from '@/components/humation/avatar-builder';

<AvatarBuilder onChange={(state) => saveAvatar(state)} />
```

Use this block as the starting point for production avatar creation UI instead of inventing a simplified picker from scratch. It includes responsive preview, part picker, color sheet, randomize, PNG/SVG export, and JSON state copy.

## zo.space note

zo.space page routes are the exception: do not install npm packages into zo.space. For zo.space **page routes**, use pinned browser ESM imports from `esm.sh`:

```tsx
import { createAvatar, createPartPreview, getPartsForSlot } from "https://esm.sh/@humation/core@1.0.1?bundle";
import { humation1 } from "https://esm.sh/@humation/assets-humation-1@1.0.1?bundle";
```

The current `https://yusuke.zo.space/humation-avatar` route uses this package-based renderer in the browser. It does not call the legacy Humation SVG API for rendering.

For zo.space **API routes**, do not use external URL ESM imports. If backend-side Humation npm dependencies are needed, use a Zo Site or User Service. If a static avatar is enough, generate SVG with `scripts/humation-local.ts`, upload it with `update_space_asset`, and render it as `<img src="/assets/...svg" />`.