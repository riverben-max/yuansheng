export function captureMessageState(data = {}) {
  const results = Array.isArray(data.results) ? data.results : [];
  if (!results.length) {
    return { type: "success", message: "采集完成" };
  }

  const skippedCount = results.filter((item) => item?.skipped).length;
  if (skippedCount === results.length) {
    return { type: "info", message: results[0]?.message || "采集暂未接入" };
  }

  const cleanSuccessCount = results.filter((item) => item?.ok && !itemFailureReason(item)).length;
  const issueResults = results.filter((item) => !item?.ok || itemFailureReason(item));
  if (!issueResults.length && cleanSuccessCount > 0) {
    return { type: "success", message: "采集完成" };
  }
  if (cleanSuccessCount > 0) {
    return { type: "warning", message: "部分账号采集失败" };
  }
  if (issueResults.length === 1) {
    return { type: "warning", message: itemFailureReason(issueResults[0]) || issueResults[0]?.message || "采集失败" };
  }
  return { type: "error", message: "采集失败" };
}

function itemFailureReason(item) {
  return String(item?.lastFailureReason || "").trim();
}
