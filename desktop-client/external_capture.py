from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Mapping
from urllib.parse import unquote

from shadow_browser import ShadowBrowserError, attach_or_recover_shadow_browser, ensure_shadow_browser
from spider_core import EMPLOYEE_TARGET_URL, PageSnapshot, normalize_account_for_match, snapshot_requires_login
from table_capture import merge_table_round_payloads, parse_json_payload, table_result_to_payload


class LoginRequiredError(RuntimeError):
    """Raised when the external browser is connected but the user is not logged in."""


EXTERNAL_TABLE_ROUNDS = [
    {
        "name": "第一阶段",
        "labels": [
            "咨询人数",
            "接待人数",
            "询单人数",
            "询单转化率",
            "首次响应时长（秒）",
            "平均响应时长（秒）",
        ],
        "fields": {
            "consultationCount": ["咨询人数"],
            "receiveCount": ["接待人数"],
            "inquiryCount": ["询单人数", "延询单人数"],
            "conversionRate": ["询单转化率", "延询单转化率"],
            "firstReplyTime": ["首次响应时长（秒）", "首次响应时长"],
            "avgReplyTime": ["平均响应时长（秒）", "平均响应时长"],
        },
    },
    {
        "name": "第二阶段",
        "labels": [
            "旺旺回复率",
            "客户满意率",
            "销售额",
            "个人销售额占比",
        ],
        "fields": {
            "wwReplyRate": ["旺旺回复率"],
            "satisfaction": ["客户满意率"],
        },
    },
]

GET_PAGE_STATE_SCRIPT = """
JSON.stringify({
  currentNick: (
    (window.QN_WORKBENCH_CFG && window.QN_WORKBENCH_CFG.user && (window.QN_WORKBENCH_CFG.user.nick || window.QN_WORKBENCH_CFG.user.displayNick || window.QN_WORKBENCH_CFG.user.name)) ||
    ''
  ),
  pageTitle: document.title || '',
  pageUrl: location.href || '',
  bodyText: (document.body && document.body.innerText ? document.body.innerText.slice(0, 12000) : '')
})
"""


def inspect_external_page_state(
    config: Mapping[str, Any],
    log: Callable[[str], None],
    ensure_browser: bool = False,
) -> Dict[str, Any]:
    session = (
        ensure_shadow_browser(config, log)
        if ensure_browser
        else attach_or_recover_shadow_browser(
            config=config,
            log=log,
            auto_launch=False,
        )
    )
    page = session.page
    _open_target_page(page)
    state = _read_page_state(page)
    state["loggedIn"] = not snapshot_requires_login(_snapshot_from_state(state))
    state["shadowChromePid"] = session.pid
    state["chromePath"] = session.chrome_path
    state["shadowChromeProfileDir"] = session.profile_dir
    return state


def capture_with_external_chrome(config: Mapping[str, Any], log: Callable[[str], None]) -> Dict[str, Any]:
    try:
        session = ensure_shadow_browser(config, log)
    except ShadowBrowserError:
        raise

    page = session.page
    log(f"已接管影子 Chrome（PID={session.pid or '--'}，当前标题：{page.title}）。")
    _open_target_page(page)
    state = _read_page_state(page)
    if not state.get("loggedIn"):
        raise LoginRequiredError("影子浏览器当前未登录千牛，请重新扫码后再采集。")

    current_identity = _resolve_current_identity(config, state) or _read_identity_from_cookies(page)
    if not current_identity:
        raise RuntimeError("未从页面或 Cookie 识别到当前登录员工账号。")
    log(f"当前登录员工识别为：{current_identity}，匹配名：{normalize_account_for_match(current_identity)}。")

    payloads: List[Dict[str, Any]] = []
    for round_config in EXTERNAL_TABLE_ROUNDS:
        log(f"{round_config['name']}开始，准备切换指标：{'、'.join(round_config['labels'])}")
        _switch_metrics(page, round_config, log)
        result = _extract_table_result(page, current_identity)
        payload = table_result_to_payload(result, round_config)
        payloads.append(payload)
        log(f"{round_config['name']}表格采集成功。")

    return merge_table_round_payloads(payloads)


def _resolve_current_identity(config: Mapping[str, Any], state: Mapping[str, Any]) -> str:
    for source in (
        state.get("currentNick"),
        config.get("currentAccount"),
        config.get("lastKnownLoginAccount"),
        config.get("loginAccount"),
        config.get("subAccount"),
    ):
        text = str(source or "").strip()
        if text:
            return text
    return ""


def _read_identity_from_cookies(page: Any) -> str:
    try:
        cookies = page.cookies(all_domains=True)
    except Exception:
        return ""

    cookie_map: Dict[str, str] = {}
    for cookie in cookies:
        if not isinstance(cookie, Mapping):
            continue
        name = str(cookie.get("name") or "").strip()
        value = str(cookie.get("value") or "").strip()
        if name and value:
            cookie_map[name] = value

    for name in ("sn", "_nk_", "tracknick", "lgc"):
        value = cookie_map.get(name)
        if not value:
            continue
        decoded = unquote(value).strip()
        if decoded:
            return decoded
    return ""


def _switch_metrics(page: Any, round_config: Mapping[str, Any], log: Callable[[str], None]) -> None:
    target_fields = list(round_config.get("labels") or [])
    _wait_for_checkbox_panel(page, target_fields)

    while True:
        checked_items, unchecked_items = _collect_checkbox_groups(page)
        to_check = [field for field in target_fields if field in unchecked_items]
        to_uncheck = [field for field in checked_items if field not in target_fields]

        if not to_check and not to_uncheck:
            log(f"{round_config['name']}指标切换完成。")
            time.sleep(3)
            return

        current_count = len(checked_items)
        if to_check and current_count < 6:
            field = to_check[0]
            log(f"{round_config['name']}勾选指标：{field}")
            unchecked_items[field].click()
            time.sleep(0.4)
            continue

        if to_uncheck and current_count > 1:
            field = to_uncheck[0]
            log(f"{round_config['name']}取消指标：{field}")
            checked_items[field].click()
            time.sleep(0.4)
            continue

        raise RuntimeError(f"{round_config['name']}指标切换失败：当前勾选数量={current_count}，无法继续置换")


def _wait_for_checkbox_panel(page: Any, labels: List[str], timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        checked_items, unchecked_items = _collect_checkbox_groups(page)
        if any(field in checked_items or field in unchecked_items for field in labels):
            return
        time.sleep(0.3)
    raise RuntimeError(f"未等到指标选择区域加载完成：{'、'.join(labels)}")


def _collect_checkbox_groups(page: Any) -> tuple[Dict[str, Any], Dict[str, Any]]:
    checked_items: Dict[str, Any] = {}
    unchecked_items: Dict[str, Any] = {}
    for input_ele in page.eles("tag:input@type=checkbox"):
        label_ele = input_ele.parent("tag:label")
        if not label_ele:
            label_ele = input_ele.parent(2)
        if not label_ele:
            continue
        text = str(label_ele.text or "").replace("\n", "").strip()
        if not text:
            continue
        if input_ele.property("checked"):
            checked_items[text] = label_ele
        else:
            unchecked_items[text] = label_ele
    return checked_items, unchecked_items


def _extract_table_result(page: Any, current_identity: str) -> Dict[str, Any]:
    state = _read_page_state(page)
    thead = page.ele("tag:thead")
    tbody = page.ele("tag:tbody")
    if not thead or not tbody:
        raise RuntimeError("当前页面未找到绩效表格。")

    headers = [str(item.text or "").replace("\n", "").strip() for item in thead.eles("tag:th")]
    headers = [item for item in headers if item]
    rows: List[List[str]] = []
    for row in tbody.eles("tag:tr"):
        cells = [str(cell.text or "").replace("\n", "").strip() for cell in row.eles("tag:td")]
        if len(cells) > 1:
            rows.append(cells)
    return {
        "ok": True,
        "headers": headers,
        "rows": rows,
        "currentNick": current_identity or state.get("currentNick") or "",
        "pageTitle": state.get("pageTitle") or "",
        "pageUrl": state.get("pageUrl") or "",
        "bodyText": state.get("bodyText") or "",
    }


def _open_target_page(page: Any) -> None:
    page.get(EMPLOYEE_TARGET_URL)
    time.sleep(2)


def _read_page_state(page: Any) -> Dict[str, Any]:
    state = parse_json_payload(page.run_js(GET_PAGE_STATE_SCRIPT))
    if not isinstance(state, dict):
        state = {}
    state.setdefault("pageTitle", page.title or "")
    state.setdefault("pageUrl", getattr(page, "url", "") or "")
    state.setdefault("bodyText", _read_body_text(page))
    state["loggedIn"] = not snapshot_requires_login(_snapshot_from_state(state))
    return state


def _snapshot_from_state(state: Mapping[str, Any]) -> PageSnapshot:
    return PageSnapshot(
        title=str(state.get("pageTitle") or ""),
        url=str(state.get("pageUrl") or ""),
        text=str(state.get("bodyText") or ""),
    )


def _read_body_text(page: Any) -> str:
    try:
        body_text = page.run_js("document.body && document.body.innerText ? document.body.innerText.slice(0, 12000) : ''")
    except Exception:
        return ""
    return str(body_text or "")


def _build_page_state_script() -> str:
    return GET_PAGE_STATE_SCRIPT
