import test from "node:test";
import assert from "node:assert/strict";

import {
  accountMatchesPlatformFilter,
  defaultPlatformForNewAccount,
  filterAccountsByPlatform,
  loginIdentityLabel,
  selectedAccountVisible,
  summarizeAccounts,
} from "./accountMatrix.js";

const accounts = [
  { id: "legacy", enabled: true },
  { id: "qn-1", platform: "qn", enabled: false },
  { id: "jd-1", platform: "jd", enabled: true },
  { id: "pdd-1", platform: "pdd", enabled: true },
];

test("filters accounts by platform and treats missing platform as qn", () => {
  assert.deepEqual(filterAccountsByPlatform(accounts, "all").map((item) => item.id), ["legacy", "qn-1", "jd-1", "pdd-1"]);
  assert.deepEqual(filterAccountsByPlatform(accounts, "qn").map((item) => item.id), ["legacy", "qn-1"]);
  assert.deepEqual(filterAccountsByPlatform(accounts, "jd").map((item) => item.id), ["jd-1"]);
  assert.deepEqual(filterAccountsByPlatform(accounts, "pdd").map((item) => item.id), ["pdd-1"]);
});

test("summarizes all accounts and selected platform accounts", () => {
  assert.equal(summarizeAccounts(accounts, "all"), "共 4 个账户，已启用 3 个");
  assert.equal(summarizeAccounts(accounts, "jd"), "京东 1 个账户，已启用 1 个");
  assert.equal(summarizeAccounts(accounts, "pdd"), "拼多多 1 个账户，已启用 1 个");
});

test("defaults new account platform from active filter", () => {
  assert.equal(defaultPlatformForNewAccount("jd"), "jd");
  assert.equal(defaultPlatformForNewAccount("pdd"), "pdd");
  assert.equal(defaultPlatformForNewAccount("all"), "qn");
  assert.equal(defaultPlatformForNewAccount("qn"), "qn");
});

test("detects whether selected account remains visible after filter change", () => {
  assert.equal(selectedAccountVisible(accounts[0], "qn"), true);
  assert.equal(selectedAccountVisible(accounts[0], "jd"), false);
  assert.equal(selectedAccountVisible(accounts[2], "jd"), true);
  assert.equal(selectedAccountVisible(accounts[3], "pdd"), true);
  assert.equal(selectedAccountVisible(null, "all"), false);
});

test("normalizes unsupported filters to all-matching behavior for safety", () => {
  assert.equal(accountMatchesPlatformFilter(accounts[0], "bad"), true);
});

test("shows detected login identity when manual hint is empty", () => {
  assert.equal(loginIdentityLabel({ loginHint: "manual-name", lastKnownLoginAccount: "detected-name" }), "manual-name");
  assert.equal(loginIdentityLabel({ loginHint: "", lastKnownLoginAccount: "detected-name" }), "detected-name");
  assert.equal(loginIdentityLabel({}), "--");
});
