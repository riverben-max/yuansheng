export const PLATFORMS = [
  { value: "qn", label: "千牛", tagType: "success", supportsCapture: true },
  { value: "jd", label: "京东", tagType: "info", supportsCapture: true },
  // 预留: { value: "dy", label: "抖音", tagType: "", supportsCapture: false },
];

export const DEFAULT_PLATFORM = "qn";

const PLATFORM_MAP = Object.fromEntries(PLATFORMS.map((p) => [p.value, p]));
const PLATFORM_VALUES = new Set(PLATFORMS.map((p) => p.value));

export function normalizePlatform(raw) {
  return raw && PLATFORM_VALUES.has(raw) ? raw : DEFAULT_PLATFORM;
}

export function platformLabel(platform) {
  return PLATFORM_MAP[normalizePlatform(platform)]?.label || PLATFORM_MAP[DEFAULT_PLATFORM].label;
}

export function platformTagType(platform) {
  return PLATFORM_MAP[normalizePlatform(platform)]?.tagType || "";
}

export function platformSupportsCapture(platform) {
  const cfg = PLATFORM_MAP[normalizePlatform(platform)];
  return cfg ? cfg.supportsCapture !== false : false;
}

export function platformList() {
  return PLATFORMS.map((p) => ({ value: p.value, label: p.label }));
}

export function platformFilterOptions() {
  return [{ value: "all", label: "全部" }, ...platformList()];
}
