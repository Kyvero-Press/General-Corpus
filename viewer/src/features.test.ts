import { describe, expect, it } from "vitest";

import { localSourceCacheEnabled } from "./features";

describe("localSourceCacheEnabled", () => {
  it("defaults local source-cache details to visible", () => {
    expect(localSourceCacheEnabled(undefined)).toBe(true);
    expect(localSourceCacheEnabled("")).toBe(true);
    expect(localSourceCacheEnabled("true")).toBe(true);
  });

  it("recognizes an explicit false value without case or whitespace sensitivity", () => {
    expect(localSourceCacheEnabled("false")).toBe(false);
    expect(localSourceCacheEnabled(" FALSE ")).toBe(false);
  });
});
