-- =============================================
-- Qingbird demo cleanup
-- Keep only: 总部, 演示一号分公司, admin, demo_manager, demo_kf_001
-- Safe to run more than once.
-- =============================================

SET NAMES utf8mb4;
START TRANSACTION;

-- 1) Keep the root department as headquarters.
UPDATE sys_dept
SET dept_name = '总部',
    parent_id = 0,
    ancestors = '0',
    order_num = 0,
    status = '0',
    del_flag = '0',
    update_by = 'admin',
    update_time = NOW()
WHERE dept_id = 100;

-- 2) Keep the demo branch under headquarters.
UPDATE sys_dept
SET parent_id = 100,
    ancestors = '0,100',
    dept_name = '演示一号分公司',
    order_num = 1,
    status = '0',
    del_flag = '0',
    update_by = 'admin',
    update_time = NOW()
WHERE dept_id = 2201;

-- 3) Hide original RuoYi sample companies/departments from the department tree.
UPDATE sys_dept
SET status = '1',
    del_flag = '2',
    update_by = 'admin',
    update_time = NOW()
WHERE dept_id IN (101, 102, 103, 104, 105, 106, 107, 108, 109);

-- 4) Put accounts in the expected departments.
UPDATE sys_user
SET dept_id = 100,
    status = '0',
    del_flag = '0',
    update_by = 'admin',
    update_time = NOW()
WHERE user_name = 'admin';

UPDATE sys_user
SET dept_id = 2201,
    status = '0',
    del_flag = '0',
    update_by = 'admin',
    update_time = NOW()
WHERE user_name IN ('demo_manager', 'demo_kf_001');

-- 5) Soft-delete old sample/test users from the system-user list.
UPDATE sys_user
SET status = '1',
    del_flag = '2',
    update_by = 'admin',
    update_time = NOW()
WHERE user_name NOT IN ('admin', 'demo_manager', 'demo_kf_001');

-- 6) Remove role/post links for deleted users.
DELETE ur
FROM sys_user_role ur
JOIN sys_user u ON u.user_id = ur.user_id
WHERE u.del_flag = '2';

DELETE up
FROM sys_user_post up
JOIN sys_user u ON u.user_id = up.user_id
WHERE u.del_flag = '2';

-- 7) Keep only the demo branch archive.
DELETE FROM biz_branch_info
WHERE workplace_name <> 'B-DEMO-001'
   OR branch_id <> 2201;

UPDATE biz_branch_info
SET branch_id = 2201,
    workplace_name = 'B-DEMO-001',
    company_name = '演示一号分公司有限公司',
    audit_status = 2,
    update_by = 'admin',
    update_time = NOW()
WHERE workplace_name = 'B-DEMO-001';

-- 8) Keep only employees under the demo branch.
DELETE FROM biz_employee
WHERE branch_code <> 'B-DEMO-001';

INSERT INTO biz_employee (
  user_id, login_account, id_card, address,
  branch_code, name, avatar_color, position, department,
  source, birthday, mobile, intern_date, hire_date,
  contract_status, salary_base, deposit_amount, status, resign_date,
  remark, create_by, create_time
)
SELECT u.user_id, 'demo_manager', '110101199001010010', '北京市朝阳区演示路 1 号',
       'B-DEMO-001', '演示分公司主管', '#6C4EF2', '分公司主管', '管理层',
       '演示数据', '1990-01-01', '13900002201', NULL, '2026-04-01',
       1, 6000.00, 0.00, '0', NULL,
       '演示一号分公司主管', 'admin', NOW()
FROM sys_user u
WHERE u.user_name = 'demo_manager'
  AND NOT EXISTS (SELECT 1 FROM biz_employee WHERE login_account = 'demo_manager');

UPDATE biz_employee
SET user_id = (SELECT user_id FROM sys_user WHERE user_name = 'demo_manager' LIMIT 1),
    id_card = '110101199001010010',
    address = '北京市朝阳区演示路 1 号',
    branch_code = 'B-DEMO-001',
    name = '演示分公司主管',
    avatar_color = '#6C4EF2',
    position = '分公司主管',
    department = '管理层',
    source = '演示数据',
    birthday = '1990-01-01',
    mobile = '13900002201',
    hire_date = '2026-04-01',
    contract_status = 1,
    salary_base = 6000.00,
    deposit_amount = 0.00,
    status = '0',
    resign_date = NULL,
    remark = '演示一号分公司主管',
    update_by = 'admin',
    update_time = NOW()
WHERE login_account = 'demo_manager';

UPDATE biz_employee e
JOIN sys_user u ON u.user_name = e.login_account
SET e.user_id = u.user_id,
    e.branch_code = 'B-DEMO-001',
    e.update_by = 'admin',
    e.update_time = NOW()
WHERE e.branch_code = 'B-DEMO-001';

-- 9) Keep demo branch shop/QC/payroll data only.
DELETE FROM biz_shop
WHERE branch_id <> 2201;

DELETE FROM biz_spider_data
WHERE sub_account <> 'demo_kf_001'
   OR employee_id <> (SELECT user_id FROM sys_user WHERE user_name = 'demo_kf_001' LIMIT 1);

DELETE FROM biz_settlement
WHERE branch_id <> 2201;

COMMIT;
