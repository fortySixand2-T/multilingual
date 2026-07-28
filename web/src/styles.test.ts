import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// Regression test for qa-530: at 320px the topbar `.nav` row (Learn/Review/
// Mock/Group) overflowed the viewport because the phone media query moved
// `.nav` to its own row without ever giving it a wrap/scroll fallback, so
// the last tab ("Group") got clipped and the whole page gained unwanted
// horizontal scroll. Rather than asserting real layout geometry (jsdom
// doesn't do CSS layout), assert the phone media query actually contains an
// overflow-safe rule for `.nav` so a future edit can't silently drop it.
const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "styles.css"), "utf8");

describe("styles.css phone nav overflow fix", () => {
  it("keeps the .nav row overflow-safe inside the phone media query", () => {
    const mediaBlockMatch = css.match(/@media \(max-width: 640px\) \{([\s\S]*)\}\s*$/);
    expect(mediaBlockMatch).not.toBeNull();
    const mediaBlock = mediaBlockMatch![1];

    const navRuleMatch = mediaBlock.match(/\.nav\s*\{([^}]*)\}/);
    expect(navRuleMatch).not.toBeNull();
    const navRule = navRuleMatch![1];

    // Must not be left at the default `nowrap` overflow behaviour with no
    // fallback: either wrap onto extra lines, or contain overflow within a
    // scrollable strip.
    const wraps = /flex-wrap:\s*wrap/.test(navRule);
    const scrolls = /overflow-x:\s*auto/.test(navRule);
    expect(wraps || scrolls).toBe(true);
  });
});
