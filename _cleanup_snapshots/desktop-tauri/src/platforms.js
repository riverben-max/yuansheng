export const PLATFORM_QN = "qn";
export const PLATFORM_JD = "jd";
export const PLATFORM_PDD = "pdd";
export const PLATFORM_DOUYIN = "douyin";

export const PLATFORM_META = {
  [PLATFORM_QN]: {
    value: PLATFORM_QN,
    label: "千牛",
    color: "#2563eb",
    tagType: "",
    captureSupported: true,
  },
  [PLATFORM_JD]: {
    value: PLATFORM_JD,
    label: "京东",
    color: "#dc2626",
    tagType: "danger",
    captureSupported: true,
  },
  [PLATFORM_PDD]: {
    value: PLATFORM_PDD,
    label: "拼多多",
    color: "#e84393",
    tagType: "warning",
    captureSupported: true,
  },
  [PLATFORM_DOUYIN]: {
    value: PLATFORM_DOUYIN,
    label: "抖店",
    color: "#111827",
    tagType: "info",
    captureSupported: true,
  },
};

export const PLATFORM_VALUES = Object.keys(PLATFORM_META);

export const ENABLED_PLATFORMS = PLATFORM_VALUES.filter(
  (key) => PLATFORM_META[key].enabled !== false,
);

export const CAPTURE_PLATFORMS = ENABLED_PLATFORMS.filter(
  (key) => PLATFORM_META[key].captureSupported,
);

export const DEFAULT_PLATFORM = PLATFORM_QN;

export function platformMeta(platform) {
  return PLATFORM_META[platform] || null;
}

export function platformLabel(platform) {
  const meta = platformMeta(platform);
  return meta ? meta.label : platform || "--";
}

export function platformTagType(platform) {
  const meta = platformMeta(platform);
  return meta?.tagType || "info";
}

export function platformColor(platform) {
  const meta = platformMeta(platform);
  return meta?.color || "#6b7280";
}

export function isCaptureSupported(platform) {
  const meta = platformMeta(platform);
  return meta?.captureSupported === true;
}

export const PLATFORM_FILTER_OPTIONS = [
  { value: "", label: "全部" },
  ...ENABLED_PLATFORMS.map((key) => ({
    value: key,
    label: PLATFORM_META[key].label,
  })),
];
