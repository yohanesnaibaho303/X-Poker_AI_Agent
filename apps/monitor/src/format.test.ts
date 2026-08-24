import { describe, expect, it } from "vitest";
import { formatNativeChips, formatStack } from "./format";

describe("native chip formatting", () => {
  it.each([
    [10_000, "10,000"],
    [99_999, "99,999"],
    [100_000, "100K"],
    [200_000, "200K"],
    [1_000_000, "1M"],
    [1_500_000, "1.5M"],
  ])("formats %s as %s", (value, expected) => {
    expect(formatNativeChips(value)).toBe(expected);
  });

  it("keeps BB mode independent of a native blind", () => {
    expect(formatStack("100", "BB", null)).toBe("100BB");
  });

  it("requires a blind before converting BB state to native chips", () => {
    expect(formatStack("100", "native", null)).toBe("blind required");
    expect(formatStack("100", "native", 2_000)).toBe("200K");
  });
});
