import test from "node:test";
import assert from "node:assert/strict";

import {
  PLATFORMS,
  DEFAULT_PLATFORM,
  normalizePlatform,
  platformLabel,
  platformTagType,
  platformSupportsCapture,
  platformList,
  platformFilterOptions,
} from "./platforms.js";

test("PLATFORMS contains qn, jd and pdd in display order", () => {
  assert.equal(PLATFORMS.length, 3);
  assert.deepEqual(PLATFORMS.map((p) => p.value), ["qn", "jd", "pdd"]);
});

test("DEFAULT_PLATFORM is qn", () => {
  assert.equal(DEFAULT_PLATFORM, "qn");
});

test("normalizePlatform returns known platform or defaults to qn", () => {
  assert.equal(normalizePlatform("qn"), "qn");
  assert.equal(normalizePlatform("jd"), "jd");
  assert.equal(normalizePlatform("pdd"), "pdd");
  assert.equal(normalizePlatform(undefined), "qn");
  assert.equal(normalizePlatform(null), "qn");
  assert.equal(normalizePlatform("bad"), "qn");
});

test("platformLabel returns Chinese label", () => {
  assert.equal(platformLabel("qn"), "千牛");
  assert.equal(platformLabel("jd"), "京东");
  assert.equal(platformLabel("pdd"), "拼多多");
  assert.equal(platformLabel(undefined), "千牛");
  assert.equal(platformLabel("bad"), "千牛");
});

test("platformTagType returns configured tag type", () => {
  assert.equal(platformTagType("qn"), "success");
  assert.equal(platformTagType("jd"), "info");
  assert.equal(platformTagType("pdd"), "warning");
  // unknown platforms normalize to qn, inheriting its tag type
  assert.equal(platformTagType("bad"), "success");
});

test("platformSupportsCapture checks capture support flag", () => {
  assert.equal(platformSupportsCapture("qn"), true);
  assert.equal(platformSupportsCapture("jd"), true);
  assert.equal(platformSupportsCapture("pdd"), true);
  // unknown platforms normalize to qn, inheriting its capture support
  assert.equal(platformSupportsCapture("bad"), true);
});

test("platformList returns value-label pairs", () => {
  assert.deepEqual(platformList(), [
    { value: "qn", label: "千牛" },
    { value: "jd", label: "京东" },
    { value: "pdd", label: "拼多多" },
  ]);
});

test("platformFilterOptions includes 'all' option", () => {
  assert.deepEqual(platformFilterOptions(), [
    { value: "all", label: "全部" },
    { value: "qn", label: "千牛" },
    { value: "jd", label: "京东" },
    { value: "pdd", label: "拼多多" },
  ]);
});
