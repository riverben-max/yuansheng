export const ACCOUNT_PLATFORM_OPTIONS = [
  { value: "qn", label: "千牛" },
  { value: "jd", label: "京东" },
];

export const PLATFORM_FILTER_OPTIONS = [{ value: "all", label: "全部" }, ...ACCOUNT_PLATFORM_OPTIONS];

const ACCOUNT_PLATFORMS = new Set(ACCOUNT_PLATFORM_OPTIONS.map((item) => item.value));
const PLATFORM_FILTERS = new Set(PLATFORM_FILTER_OPTIONS.map((item) => item.value));

export function normalizePlatform(platform) {
  return ACCOUNT_PLATFORMS.has(platform) ? platform : "qn";
}

export function normalizePlatformFilter(filter) {
  return PLATFORM_FILTERS.has(filter) ? filter : "all";
}

export function platformLabel(platform) {
  return ACCOUNT_PLATFORM_OPTIONS.find((item) => item.value === normalizePlatform(platform))?.label || "千牛";
}

export function accountMatchesPlatformFilter(account, filter) {
  const normalizedFilter = normalizePlatformFilter(filter);
  if (normalizedFilter === "all") return true;
  return normalizePlatform(account?.platform) === normalizedFilter;
}

export function filterAccountsByPlatform(accounts, filter) {
  const source = Array.isArray(accounts) ? accounts : [];
  return source.filter((account) => accountMatchesPlatformFilter(account, filter));
}

export function enabledFilteredAccountCount(accounts, filter) {
  return filterAccountsByPlatform(accounts, filter).filter((account) => account.enabled).length;
}

export function summarizeAccounts(accounts, filter) {
  const normalizedFilter = normalizePlatformFilter(filter);
  const filtered = filterAccountsByPlatform(accounts, normalizedFilter);
  const enabledCount = filtered.filter((account) => account.enabled).length;
  if (normalizedFilter === "all") {
    return `共 ${filtered.length} 个账户，已启用 ${enabledCount} 个`;
  }
  return `${platformLabel(normalizedFilter)} ${filtered.length} 个账户，已启用 ${enabledCount} 个`;
}

export function defaultPlatformForNewAccount(filter) {
  return normalizePlatformFilter(filter) === "jd" ? "jd" : "qn";
}

export function selectedAccountVisible(account, filter) {
  if (!account) return false;
  return accountMatchesPlatformFilter(account, filter);
}
