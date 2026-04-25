# Design System Inspired by Apple

## 1. Visual Theme & Atmosphere
Apple's web presence is a masterclass in reverent product photography framed by near-invisible UI. The homepage is a stack of edge-to-edge product "tiles" — alternating light and dark canvases, each centered on a hero headline, a one-line tagline, two tiny blue pill CTAs, and an impossibly crisp product render. Nothing competes with the product. Typography is confident but quiet; color is either pure white, an off-white parchment, or a near-black tile; interactive elements are a single, quiet blue.

Density is unusually low even by contemporary SaaS standards. Each tile occupies roughly one viewport, and there is no decorative chrome.

**Key Characteristics:**
*   Photography-first presentation; UI recedes so the product can speak
*   Alternating full-bleed tile sections: white/parchment ↔ near-black
*   Single blue accent (#0066cc/#0071e3) carries every interactive element
*   Two button grammars: tiny blue pill CTAs (980px radius) and compact utility rects (8px radius)
*   SF Pro Display + SF Pro Text — negative letter-spacing at display sizes
*   Whisper-soft elevation used only when a product image needs to breathe

## 2. Color Palette & Roles
*   **Primary Action Blue (#0066cc):** All text links, all blue pill CTAs.
*   **Focus Blue (#0071e3):** Keyboard focus ring on buttons (outline: 2px solid).
*   **Near-Black Ink (#1d1d1f):** Primary heading + body color on light surfaces.
*   **Sky Link Blue (#2997ff):** Brighter blue used on dark surfaces for links.
*   **Pure White (#ffffff):** Dominant canvas.
*   **Parchment (#f5f5f7):** Signature Apple off-white.
*   **Near-Black Tile 1 (#272729):** Primary dark-tile surface.
*   **Paper White (#ffffff):** All text on dark tiles.

## 3. Typography Rules
*   **Display:** "SF Pro Display", "SF Pro Icons", "Helvetica Neue", Helvetica, Arial, sans-serif. Used for sizes ≥ 19px. Negative letter-spacing.
*   **Body / UI:** "SF Pro Text", "SF Pro Icons", "Helvetica Neue", Helvetica, Arial, sans-serif. Used for body copy, buttons, links below 20px.
*   **Hero Headline:** 56px, weight 600, line-height 1.07, letter-spacing -0.28px.
*   **H1 / Tile Headline:** 40px, weight 600, line-height 1.10.
*   **H2 / Section:** 34px, weight 600, line-height 1.47, letter-spacing -0.374px.
*   **Body:** 17px, weight 400, line-height 1.47, letter-spacing -0.374px.

## 4. Component Stylings
**Primary Blue Pill CTA**
*   Background: Action Blue (#0066cc)
*   Text: Paper White (#ffffff), SF Pro Text 17px, weight 400
*   Border: none
*   Radius: 980px
*   Padding: ~11px 22px
*   Active state: transform: scale(0.95)

**Global Nav Bar**
*   Background: Pure Black (#000000)
*   Height: ~44px
*   Text: Paper White (#ffffff), SF Pro Text 12px, weight 400, letter-spacing -0.12px

## 5. Layout Principles
*   **Base unit:** 8px.
*   **Section vertical padding:** ~64–80px inside a product tile.
*   **Max content width:** ~980px on text-heavy sections, full-bleed for product tiles.

## 6. Depth & Elevation
*   **Level 3:** `rgba(0, 0, 0, 0.22) 3px 5px 30px 0` — Product renders resting on a surface (the only true "shadow" in the system). No shadows on cards or text.

## 7. Do's and Don'ts
*   **Do:** Use Action Blue (#0066cc) for every interactive element.
*   **Do:** Set headlines in SF Pro Display with negative letter-spacing.
*   **Do:** Alternate light and dark full-bleed tiles.
*   **Don't:** Introduce a second accent color.
*   **Don't:** Add shadows to cards, buttons, or text.
*   **Don't:** Round full-bleed tiles.
