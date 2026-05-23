from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def fail(message):
    print(f"FAIL: {message}")
    return 1


def assert_contains(text, needle, message):
    if needle not in text:
        return fail(message)
    return 0


def assert_not_contains(text, needle, message):
    if needle in text:
        return fail(message)
    return 0


def main():
    checks = []

    dashboard_controller = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/controller/DashboardController.java")
    dashboard_mapper = read("ruoyi-admin/src/main/resources/mapper/qingbird/DashboardMapper.xml")
    dashboard_mapper_java = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/mapper/DashboardMapper.java")
    employee_controller = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/controller/BizEmployeeController.java")
    spider_controller = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/controller/BizSpiderDataController.java")
    branch_service = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/service/impl/BizBranchInfoServiceImpl.java")
    employee_mapper = read("ruoyi-admin/src/main/resources/mapper/qingbird/BizEmployeeMapper.xml")
    login_mapper = read("ruoyi-system/src/main/resources/mapper/system/SysLogininforMapper.xml")
    upload_controller = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/controller/SpiderUploadController.java")
    signature_interceptor = read("ruoyi-admin/src/main/java/com/ruoyi/qingbird/interceptor/SignatureInterceptor.java")
    schema = read("sql/qingbird_schema.sql")
    employee_schema = read("sql/biz_employee.sql")
    seed = read("sql/qingbird_demo_seed.sql")

    for name, text in {
        "DashboardController": dashboard_controller,
        "BizEmployeeController": employee_controller,
        "BizSpiderDataController": spider_controller,
    }.items():
        checks.append(assert_not_contains(text, "hasAnyRoles('admin,manager')", f"{name} still grants admin/manager role bypass"))

    checks.append(assert_contains(dashboard_controller, "getDashboardScopeBranchId()", "DashboardController does not compute scoped branch id"))
    checks.append(assert_contains(dashboard_mapper_java, "@Param(\"branchId\") Long branchId", "DashboardMapper methods do not accept branchId filter"))
    checks.append(assert_contains(dashboard_mapper, "branchId != null", "DashboardMapper.xml does not apply branchId filter"))

    checks.append(assert_contains(branch_service, "selectBizBranchInfoByBranchId(deptId)", "submitBranchInfo does not load record by current dept id"))
    checks.append(assert_contains(branch_service, "bizBranchInfo.setBranchId(deptId)", "submitBranchInfo does not force current dept id"))

    checks.append(assert_contains(employee_controller, "selectLogininforListByExactUserName", "loginLogs does not use exact login log query"))
    checks.append(assert_contains(login_mapper, "user_name = #{userName}", "SysLogininforMapper lacks exact user_name query"))

    exact_employee_query = re.search(r'<select id="selectEmployeeByLoginAccount"[\s\S]*?</select>', employee_mapper)
    if not exact_employee_query:
        checks.append(fail("BizEmployeeMapper.xml lacks selectEmployeeByLoginAccount"))
    else:
        checks.append(assert_not_contains(exact_employee_query.group(0).upper(), "LIMIT 1", "selectEmployeeByLoginAccount still uses LIMIT 1"))
    checks.append(assert_contains(employee_schema, "UNIQUE KEY `uk_biz_employee_login_account`", "biz_employee.sql lacks unique login_account key"))

    checks.append(assert_contains(schema, "CREATE TABLE `biz_settlement`", "qingbird_schema.sql does not create biz_settlement"))
    checks.append(assert_contains(schema, "`settlement_period`", "qingbird_schema.sql settlement table lacks settlement_period"))
    checks.append(assert_contains(schema, "`settlement_amount`", "qingbird_schema.sql settlement table lacks settlement_amount"))

    checks.append(assert_contains(upload_controller, "uploadDTO == null", "SpiderUploadController does not guard null uploadDTO"))
    checks.append(assert_contains(signature_interceptor, 'request.getHeader("X-Request-Id")', "SignatureInterceptor does not require X-Request-Id"))
    checks.append(assert_contains(signature_interceptor, 'request.getHeader("X-Nonce")', "SignatureInterceptor does not require X-Nonce"))
    checks.append(assert_contains(signature_interceptor, "putIfAbsent", "SignatureInterceptor does not atomically reject replayed request ids/nonces"))
    checks.append(assert_contains(seed, "branch_id, platform_type, login_account", "demo seed spider data does not include new branch/platform/login columns"))

    failures = sum(checks)
    if failures:
        print(f"{failures} backend security/schema checks failed.")
        return 1
    print("All backend security/schema checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
