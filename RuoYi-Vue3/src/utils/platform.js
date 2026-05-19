/**
 * 平台常量映射表
 * 统一管理平台类型值、标签、颜色和 Element UI tag 样式
 */
export const PLATFORM_TYPE = {
  TAOBAO: 1,
  JD: 2,
  PDD: 3,
}

export const PLATFORM_CONFIG = {
  [PLATFORM_TYPE.TAOBAO]: {
    label: "淘宝",
    color: "#FF6900",
    tagType: "warning",
  },
  [PLATFORM_TYPE.JD]: {
    label: "京东",
    color: "#E2231A",
    tagType: "primary",
  },
  [PLATFORM_TYPE.PDD]: {
    label: "拼多多",
    color: "#C0392B",
    tagType: "danger",
  },
}

const DEFAULT_CONFIG = PLATFORM_CONFIG[PLATFORM_TYPE.TAOBAO]

export function platformLabel(type) {
  return PLATFORM_CONFIG[type]?.label || DEFAULT_CONFIG.label
}

export function platformColor(type) {
  return PLATFORM_CONFIG[type]?.color || DEFAULT_CONFIG.color
}

export function platformTagType(type) {
  return PLATFORM_CONFIG[type]?.tagType || DEFAULT_CONFIG.tagType
}

export function platformOptions() {
  return Object.entries(PLATFORM_CONFIG).map(([value, cfg]) => ({
    value: Number(value),
    label: cfg.label,
  }))
}
