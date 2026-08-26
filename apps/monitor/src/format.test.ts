import { describe, expect, it } from "vitest";

import { formatNativeChips, formatStack } from "./format";

describe("native-chip formatting", () => {
  it("keeps exact grouped values without K or M abbreviations", () => {
    expect(formatNativeChips(10_000)).toBe("10,000");
    expect(formatNativeChips(200_000)).toBe("200,000");
    expect(formatNativeChips(1_000_000)).toBe("1,000,000");
  });

  it("formats canonical stack amounts directly as native chips", () => {
    expect(formatStack("200000")).toBe("200,000");
  });
});
