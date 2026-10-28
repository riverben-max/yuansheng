from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from spider_core import (
    PageSnapshot,
    extract_number,
    infer_current_account,
    infer_record_date,
    merge_capture_payloads,
    normalize_login_account,
)

TABLE_METRIC_ROUNDS = [
    {
        "name": "第一阶段",
        "labels": [
            "咨询人数",
            "接待人数",
            "有效接待人数",
            "询单人数",
            "询单转化率",
            "首次响应时长（秒）",
        ],
        "fields": {
            "consultationCount": ["咨询人数"],
            "receiveCount": ["接待人数"],
            "validReceiveCount": ["有效接待人数"],
            "inquiryCount": ["询单人数"],
            "conversionRate": ["询单转化率"],
            "firstReplyTime": ["首次响应时长（秒）", "首次响应时长"],
        },
    },
    {
        "name": "第二阶段",
        "labels": [
            "平均响应时长（秒）",
            "旺旺回复率",
            "客户满意率",
        ],
        "fields": {
            "avgReplyTime": ["平均响应时长（秒）", "平均响应时长"],
            "wwReplyRate": ["旺旺回复率"],
            "satisfaction": ["客户满意率"],
        },
    },
]

ACCOUNT_HEADERS = (
    "客服",
    "客服姓名",
    "客服名称",
    "客服账号",
    "旺旺号",
    "子账号",
    "账号",
)
SUMMARY_ROW_MARKERS = ("全店", "汇总", "平均", "合计", "总计")

EMPTY_CAPTURE_PAYLOAD = {
    "loginAccount": None,
    "recordDate": None,
    "subAccount": None,
    "consultationCount": None,
    "receiveCount": None,
    "validReceiveCount": None,
    "inquiryCount": None,
    "conversionRate": None,
    "firstReplyTime": None,
    "avgReplyTime": None,
    "wwReplyRate": None,
    "satisfaction": None,
    "rawMetrics": {"rounds": []},
}


def build_switch_step_script(target_fields: Sequence[str]) -> str:
    targets = json.dumps(list(target_fields), ensure_ascii=False)
    return f"""
    (function(targets) {{
      function normalize(text) {{
        return (text || '')
          .replace(/[\\s\\u00a0]+/g, '')
          .replace(/\\(/g, '（')
          .replace(/\\)/g, '）')
          .trim();
      }}

      var inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
      var checkedItems = {{}};
      var uncheckedItems = {{}};
      var missingTargets = [];

      for (var i = 0; i < inputs.length; i += 1) {{
        var input = inputs[i];
        var label = input.closest('label') || input.parentElement || (input.parentElement && input.parentElement.parentElement);
        var text = normalize(label ? label.innerText : '');
        if (!text) {{
          continue;
        }}
        if (input.checked) {{
          checkedItems[text] = label || input;
        }} else {{
          uncheckedItems[text] = label || input;
        }}
      }}

      var normalizedTargets = targets.map(function(item) {{ return normalize(item); }});
      for (var j = 0; j < normalizedTargets.length; j += 1) {{
        if (!checkedItems[normalizedTargets[j]] && !uncheckedItems[normalizedTargets[j]]) {{
          missingTargets.push(targets[j]);
        }}
      }}

      var toCheck = normalizedTargets.filter(function(item) {{ return !!uncheckedItems[item]; }});
      var toUncheck = Object.keys(checkedItems).filter(function(item) {{
        return normalizedTargets.indexOf(item) < 0;
      }});
      var currentCount = Object.keys(checkedItems).length;

      function clickNode(node) {{
        if (!node) {{
          return false;
        }}
        if (typeof node.click === 'function') {{
          node.click();
          return true;
        }}
        return false;
      }}

      if (!toCheck.length && !toUncheck.length) {{
        return JSON.stringify({{
          done: true,
          currentCount: currentCount,
          missingTargets: missingTargets,
          checkedItems: Object.keys(checkedItems),
          uncheckedItems: Object.keys(uncheckedItems)
        }});
      }}

      if (toCheck.length && currentCount < 6) {{
        var checkField = toCheck[0];
        clickNode(uncheckedItems[checkField]);
        return JSON.stringify({{
          done: false,
          action: 'check',
          field: checkField,
          currentCount: currentCount,
          missingTargets: missingTargets,
          checkedItems: Object.keys(checkedItems),
          uncheckedItems: Object.keys(uncheckedItems)
        }});
      }}

      if (toUncheck.length && currentCount > 1) {{
        var uncheckField = toUncheck[0];
        clickNode(checkedItems[uncheckField]);
        return JSON.stringify({{
          done: false,
          action: 'uncheck',
          field: uncheckField,
          currentCount: currentCount,
          missingTargets: missingTargets,
          checkedItems: Object.keys(checkedItems),
          uncheckedItems: Object.keys(uncheckedItems)
        }});
      }}

      return JSON.stringify({{
        done: false,
        error: 'unable_to_switch',
        currentCount: currentCount,
        missingTargets: missingTargets,
        checkedItems: Object.keys(checkedItems),
        uncheckedItems: Object.keys(uncheckedItems)
      }});
    }})({targets});
    """


def build_extract_table_script() -> str:
    return """
    (function() {
      function clean(text) {
        return (text || '').replace(/\\n+/g, ' ').replace(/[\\s\\u00a0]+/g, ' ').trim();
      }

      var thead = document.querySelector('thead');
      var tbody = document.querySelector('tbody');
      if (!thead || !tbody) {
        return JSON.stringify({
          ok: false,
          error: 'table_not_found',
          currentNick: (window.QN_WORKBENCH_CFG && window.QN_WORKBENCH_CFG.user && window.QN_WORKBENCH_CFG.user.nick) || '',
          pageTitle: document.title || '',
          pageUrl: location.href || '',
          bodyText: (document.body && document.body.innerText) || ''
        });
      }

      var headers = Array.from(thead.querySelectorAll('th')).map(function(item) {
        return clean(item.innerText || item.textContent || '');
      }).filter(function(item) {
        return !!item;
      });

      var rows = Array.from(tbody.querySelectorAll('tr')).map(function(row) {
        return Array.from(row.querySelectorAll('td')).map(function(cell) {
          return clean(cell.innerText || cell.textContent || '');
        });
      }).filter(function(row) {
        return row.length > 1;
      });

      return JSON.stringify({
        ok: true,
        headers: headers,
        rows: rows,
        currentNick: (window.QN_WORKBENCH_CFG && window.QN_WORKBENCH_CFG.user && window.QN_WORKBENCH_CFG.user.nick) || '',
        pageTitle: document.title || '',
        pageUrl: location.href || '',
        bodyText: (document.body && document.body.innerText ? document.body.innerText.slice(0, 12000) : '')
      });
    })();
    """


def parse_json_payload(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def snapshot_from_table_result(result: Mapping[str, Any]) -> PageSnapshot:
    return PageSnapshot(
        title=str(result.get("pageTitle") or ""),
        url=str(result.get("pageUrl") or ""),
        text=str(result.get("bodyText") or ""),
    )


def table_result_to_payload(result: Mapping[str, Any], round_config: Mapping[str, Any]) -> Dict[str, Any]:
    if not result.get("ok"):
        raise ValueError(result.get("error") or "表格尚未可用")

    headers = [str(item).strip() for item in (result.get("headers") or []) if str(item).strip()]
    rows = result.get("rows") or []
    if not headers or not rows:
        raise ValueError("表头或表格内容为空")

    snapshot = snapshot_from_table_result(result)
    current_nick = str(result.get("currentNick") or "").strip()
    row_dicts = _table_rows_to_dicts(headers, rows)
    matched_row = _find_target_row(row_dicts, headers, current_nick, snapshot.text)
    account_value = _extract_row_account(matched_row, headers)
    if not account_value:
        raise ValueError("未识别到当前员工账号列")

    payload = dict(EMPTY_CAPTURE_PAYLOAD)
    payload["rawMetrics"] = {
        "rounds": [
            {
                "source": "table",
                "round": round_config.get("name"),
                "headers": headers,
                "rowData": matched_row,
            }
        ]
    }
    payload["loginAccount"] = normalize_login_account(current_nick, account_value)
    payload["recordDate"] = infer_record_date(snapshot)
    payload["subAccount"] = account_value

    for output_key, aliases in (round_config.get("fields") or {}).items():
        value = _first_row_value(matched_row, aliases)
        if value is not None:
            payload[output_key] = _convert_metric_value(output_key, value)

    return payload


def merge_table_round_payloads(payloads: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    return merge_capture_payloads(payloads)


def _table_rows_to_dicts(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for row in rows:
        row_values = [str(item).strip() for item in row]
        if len(row_values) < 2:
            continue
        mapped: Dict[str, str] = {}
        for index, header in enumerate(headers):
            mapped[header] = row_values[index] if index < len(row_values) else ""
        result.append(mapped)
    return result


def _find_target_row(
    rows: Sequence[Mapping[str, str]],
    headers: Sequence[str],
    current_nick: str,
    page_text: str,
) -> Mapping[str, str]:
    candidates = _candidate_accounts(current_nick, page_text)
    if candidates:
        candidate_set = {_normalize_header(item) for item in candidates if item}
        for row in rows:
            if _is_summary_row(row, headers):
                continue
            account_value = _extract_row_account(row, headers)
            if not account_value:
                continue
            normalized_value = _normalize_header(account_value)
            if normalized_value in candidate_set:
                return row
            if any(
                item and (item in normalized_value or normalized_value in item)
                for item in candidate_set
            ):
                return row
        raise ValueError(f"当前登录员工不在表格中：{', '.join(candidates)}")
    raise ValueError("未识别到当前登录员工账号，请确认页面右上角显示了当前客服账号。")


def _find_primary_customer_row(rows: Sequence[Mapping[str, str]], headers: Sequence[str]) -> Mapping[str, str]:
    for row in rows:
        if _is_summary_row(row, headers):
            continue
        account_value = _extract_row_account(row, headers)
        if account_value:
            return row
    raise ValueError("当前页面表格里没有可采集的客服行")


def _extract_row_account(row: Mapping[str, str], headers: Iterable[str]) -> str:
    for header in headers:
        header_text = str(header).strip()
        if header_text in ACCOUNT_HEADERS:
            value = str(row.get(header_text) or "").strip()
            if value:
                return value
    values = list(row.values())
    return str(values[1]).strip() if len(values) > 1 else ""


def _candidate_accounts(current_nick: str, page_text: str) -> List[str]:
    candidates: List[str] = []
    if current_nick:
        candidates.append(current_nick.strip())
        suffix = re.split(r"[:：]", current_nick, maxsplit=1)[-1].strip()
        if suffix and suffix not in candidates:
            candidates.append(suffix)
    try:
        inferred = infer_current_account(page_text.splitlines(), current_nick)
    except Exception:
        inferred = ""
    if inferred and inferred not in candidates:
        candidates.append(inferred)
    return candidates


def _is_summary_row(row: Mapping[str, str], headers: Sequence[str]) -> bool:
    account_value = _extract_row_account(row, headers)
    if any(marker in account_value for marker in SUMMARY_ROW_MARKERS):
        return True
    rank_value = str(row.get("排名") or row.get("序号") or "").strip()
    if any(marker in rank_value for marker in SUMMARY_ROW_MARKERS):
        return True
    return False


def _first_row_value(row: Mapping[str, str], aliases: Sequence[str]) -> Any:
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return value
    normalized_aliases = [_normalize_header(alias) for alias in aliases if alias]
    for header, value in row.items():
        if value in (None, ""):
            continue
        normalized_header = _normalize_header(header)
        if any(
            normalized_alias and (
                normalized_alias == normalized_header
                or normalized_alias in normalized_header
                or normalized_header in normalized_alias
            )
            for normalized_alias in normalized_aliases
        ):
            return value
    return None


def _normalize_header(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", "", text)
    return text.strip()


def _convert_metric_value(output_key: str, value: Any) -> Any:
    if value in (None, "", "-", {}):
        return None
    parsed = extract_number(value)
    if parsed is None:
        return None
    if output_key in {"consultationCount", "receiveCount", "validReceiveCount", "inquiryCount"}:
        return int(parsed)
    return round(parsed, 2)
