# Humation SVG API Notes

Internal notes for `Skills/humation-avatar`.

## Base

- Origin: `https://humation.app`
- Template: `humation-1-zo`

## Endpoints

### Templates

```txt
GET https://humation.app/api/v1/templates
```

Returns available templates. As of 2026-05-16:

- `humation-1`
- `humation-1-zo`

### Items

```txt
GET https://humation.app/api/v1/templates/humation-1-zo/items
```

Returns groups, parts, colors, crops, and render URL for the Zo collaboration avatar.

Known groups:

| group | type | default | notes |
|---|---:|---:|---|
| `head` | select | `001` | 001–024 observed |
| `body` | select | `001` | 001–008 observed |
| `bottom` | select | `001` | 001–008 observed |
| `item` | select | `000` | optional; mutually exclusive with `cat` |
| `glasses` | select | `000` | optional |
| `cat` | select | `000` | optional; mutually exclusive with `item` |
| `zo` | toggle | `on` | `on` / `off` |

Known colors:

| id | query key | default-ish |
|---|---|---|
| background | `bg` | `F6F5F4` or `transparent` |
| stroke | `color.stroke` | `000000` |
| skin | `color.skin` | `FFFFFF` |
| head | `color.head` | `000000` |
| body | `color.body` | `FFFFFF` |
| bottom | `color.bottom` | `000000` |
| zo | `color.zo` | `FF6600` |

### Render SVG

```txt
GET https://humation.app/api/v1/templates/humation-1-zo/render.svg?<query>
```

Minimal example:

```txt
https://humation.app/api/v1/templates/humation-1-zo/render.svg?zo=on&color.zo=FF6600
```

Full-ish example:

```txt
https://humation.app/api/v1/templates/humation-1-zo/render.svg?head=001&body=001&bottom=001&item=000&glasses=000&cat=001&zo=on&bg=transparent&color.zo=FF6600
```

## Query rules

- Hex colors can be passed without `#`, e.g. `FF6600`.
- Background accepts `transparent`.
- `item` and `cat` must not both be active.
  - Active means a value other than `000` / `off` / empty.
  - If both are active, prefer the most recently selected one in UI.
  - In final URL generation, sanitize as a safety net. Current default safety behavior: if both are active and no preference is known, keep `item` and set `cat=000`.

## Browser/embed behavior

The render endpoint returns SVG and can be used directly in HTML:

```html
<img src="https://humation.app/api/v1/templates/humation-1-zo/render.svg?zo=on&color.zo=FF6600" alt="Humation avatar" />
```

## Fetch notes

`read_webpage` can fetch the JSON endpoints. Direct Python `urllib` may receive `403`; `curl` with a browser-like `User-Agent` works. The zo.space page fetches from the browser and worked during prototype verification.
