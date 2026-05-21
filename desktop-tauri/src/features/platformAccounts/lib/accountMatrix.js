import {
  normalizePlatform,
  platformLabel,
  PLATFORMS,
  platformFilterOptions,
  DEFAULT_PLATFORM,
} from "./platforms.js";

export const ACCOUNT_PLATFORM_OPTIONS = PLATFORMS.map((p) => ({ value: p.value, label: p.label }));
export const PLATFORM_FILTER_OPTIONS = platformFilterOptions();

const ACCOUNT_PLATFORMS = new Set(PLATFORMS.map((p) => p.value));
const PLATFORM_FILTERS = new Set(PLATFORM_FILTER_OPTIONS.map((item) => item.value));

export { normalizePlatform, platformLabel };

export function normalizePlatformFilter(filter) {
  return PLATFORM_FILTERS.has(filter) ? filter : "all";
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
  const normalized = normalizePlatformFilter(filter);
  return ACCOUNT_PLATFORMS.has(normalized) ? normalized : DEFAULT_PLATFORM;
}

export function loginIdentityLabel(account) {
  return String(account?.loginHint || account?.lastKnownLoginAccount || "").trim() || "--";
}

export function selectedAccountVisible(account, filter) {
  if (!account) return false;
  return accountMatchesPlatformFilter(account, filter);
}
