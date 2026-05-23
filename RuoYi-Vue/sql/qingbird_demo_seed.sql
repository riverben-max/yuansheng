-- =============================================
-- Qingbird demo data: super admin -> branch -> employee
-- Safe to run more than once. Password for demo users: 123456
-- =============================================

SET NAMES utf8mb4;
START TRANSACTION;

-- 1) Roles used by the Qingbird frontend/backend role checks.
INSERT INTO sys_role (
  role_id, role_name, role_key, role_sort, data_scope,
  menu_check_strictly, dept_check_strictly, status, del_flag,
  create_by, create_time, update_by, update_time, remark
)
SELECT 9001, '分公司主管', 'manager', 3, '3',
       1, 1, '0', '0',
       'admin', NOW(), '', NULL, '青鸟分公司主管'
WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key = 'manager');

UPDATE sys_role
SET role_name = '分公司主管', remark = '青鸟分公司主管'
WHERE role_key = 'manager';

INSERT INTO sys_role (
  role_id, role_name, role_key, role_sort, data_scope,
  menu_check_strictly, dept_check_strictly, status, del_flag,
  create_by, create_time, update_by, update_time, remark
)
SELECT 9002, '普通员工', 'employee', 4, '5',
       1, 1, '0', '0',
       'admin', NOW(), '', NULL, '青鸟普通员工'
WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key = 'employee');

UPDATE sys_role
SET role_name = '普通员工', remark = '青鸟普通员工'
WHERE role_key = 'employee';

-- 2) One demo branch department.
INSERT INTO sys_dept (
  dept_id, parent_id, ancestors, dept_name, order_num, leader, phone, email,
  status, del_flag, create_by, create_time, update_by, update_time
)
SELECT 2201, 100, '0,100', '演示一号分公司', 99, '演示主管', '13900002201', 'demo-branch@example.com',
       '0', '0', 'admin', NOW(), 'admin', NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_dept WHERE dept_id = 2201);

UPDATE sys_dept
SET dept_name = '演示一号分公司',
    leader = '演示主管',
    phone = '13900002201',
    email = 'demo-branch@example.com',
    status = '0',
    del_flag = '0',
    update_by = 'admin',
    update_time = NOW()
WHERE dept_id = 2201;

-- 3) Branch business archive. workplace_name is the employee branch_code.
INSERT INTO biz_branch_info (
  branch_id, workplace_name, company_name, legal_person_name,
  contact_phone, contact_address, settlement_accounts, audit_status,
  create_by, create_time, update_by, update_time
) VALUES (
  2201, 'B-DEMO-001', '演示一号分公司有限公司', '演示法人',
  '13900002201', '北京市朝阳区演示路 1 号',
  '[{"type":"bank","bank":"演示银行","account":"6222000000000001","name":"演示一号分公司有限公司"}]',
  2, 'admin', NOW(), 'admin', NOW()
)
ON DUPLICATE KEY UPDATE
  workplace_name = VALUES(workplace_name),
  company_name = VALUES(company_name),
  legal_person_name = VALUES(legal_person_name),
  contact_phone = VALUES(contact_phone),
  contact_address = VALUES(contact_address),
  settlement_accounts = VALUES(settlement_accounts),
  audit_status = VALUES(audit_status),
  update_by = 'admin',
  update_time = NOW();

-- 4) Demo users. The bcrypt hash below is the default RuoYi 123456 hash.
INSERT INTO sys_user (
  user_id, dept_id, user_name, nick_name, user_type, email, phonenumber, sex, avatar,
  password, status, del_flag, login_ip, login_date, pwd_update_date,
  create_by, create_time, update_by, update_time, remark
)
SELECT 22001, 2201, 'demo_manager', '演示分公司主管', '00', 'demo-manager@example.com', '13900002201', '0', '',
       '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2',
       '0', '0', '127.0.0.1', NOW(), NOW(),
       'admin', NOW(), '', NULL, '演示分公司主管，密码 123456'
WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE user_name = 'demo_manager');

UPDATE sys_user
SET dept_id = 2201, status = '0', del_flag = '0', nick_name = '演示分公司主管'
WHERE user_name = 'demo_manager';

INSERT INTO sys_user (
  user_id, dept_id, user_name, nick_name, user_type, email, phonenumber, sex, avatar,
  password, status, del_flag, login_ip, login_date, pwd_update_date,
  create_by, create_time, update_by, update_time, remark
)
SELECT 22002, 2201, 'demo_kf_001', '演示客服一号', '00', 'demo-kf-001@example.com', '13900002202', '0', '',
       '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2',
       '0', '0', '127.0.0.1', NOW(), NOW(),
       'admin', NOW(), '', NULL, '演示客服员工，密码 123456'
WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE user_name = 'demo_kf_001');

UPDATE sys_user
SET dept_id = 2201, status = '0', del_flag = '0', nick_name = '演示客服一号'
WHERE user_name = 'demo_kf_001';

INSERT IGNORE INTO sys_user_role (user_id, role_id)
SELECT u.user_id, r.role_id
FROM sys_user u
JOIN sys_role r ON r.role_key = 'manager'
WHERE u.user_name = 'demo_manager';

INSERT IGNORE INTO sys_user_role (user_id, role_id)
SELECT u.user_id, r.role_id
FROM sys_user u
JOIN sys_role r ON r.role_key = 'employee'
WHERE u.user_name = 'demo_kf_001';

-- 5) Employee roster row under the demo branch.
INSERT INTO biz_employee (
  user_id, login_account, id_card, address,
  branch_code, name, avatar_color, position, department,
  source, birthday, mobile, intern_date, hire_date,
  contract_status, salary_base, deposit_amount, status, resign_date,
  remark, create_by, create_time
)
SELECT u.user_id, 'demo_kf_001', '110101199901010011', '北京市朝阳区演示路 1 号',
       'B-DEMO-001', '演示客服一号', '#2F80ED', '客服专员', '客服一部',
       '演示数据', '1999-01-01', '13900002202', '2026-04-01', '2026-04-15',
       1, 4500.00, 0.00, '0', NULL,
       '演示分公司员工，用于验证管理员全量和主管隔离', 'admin', NOW()
FROM sys_user u
WHERE u.user_name = 'demo_kf_001'
  AND NOT EXISTS (SELECT 1 FROM biz_employee WHERE login_account = 'demo_kf_001');

UPDATE biz_employee
SET user_id = (SELECT user_id FROM sys_user WHERE user_name = 'demo_kf_001' LIMIT 1),
    id_card = '110101199901010011',
    address = '北京市朝阳区演示路 1 号',
    branch_code = 'B-DEMO-001',
    name = '演示客服一号',
    avatar_color = '#2F80ED',
    position = '客服专员',
    department = '客服一部',
    source = '演示数据',
    birthday = '1999-01-01',
    mobile = '13900002202',
    intern_date = '2026-04-01',
    hire_date = '2026-04-15',
    contract_status = 1,
    salary_base = 4500.00,
    deposit_amount = 0.00,
    status = '0',
    resign_date = NULL,
    remark = '演示分公司员工，用于验证管理员全量和主管隔离',
    update_by = 'admin',
    update_time = NOW()
WHERE login_account = 'demo_kf_001';

-- 6) Demo shop and QC data under the demo branch.
INSERT INTO biz_shop (
  shop_id, shop_name, platform_type, login_account, shop_key,
  branch_id, employee_id, status, remark, create_time
)
SELECT 22001, '演示一号店铺', 1, 'demo_kf_001', 'DEMO_SHOP_001',
       2201, u.user_id, '0', '演示分公司质检数据店铺', NOW()
FROM sys_user u
WHERE u.user_name = 'demo_kf_001'
  AND NOT EXISTS (SELECT 1 FROM biz_shop WHERE shop_key = 'DEMO_SHOP_001');

UPDATE biz_shop
SET shop_name = '演示一号店铺',
    login_account = 'demo_kf_001',
    branch_id = 2201,
    employee_id = (SELECT user_id FROM sys_user WHERE user_name = 'demo_kf_001' LIMIT 1),
    status = '0',
    remark = '演示分公司质检数据店铺',
    update_time = NOW()
WHERE shop_key = 'DEMO_SHOP_001';

INSERT INTO biz_spider_data (
  shop_id, employee_id, branch_id, platform_type, login_account, record_date, sub_account,
  consultation_count, reception_count, effective_reception_count,
  conversion_rate, first_response_time, avg_response_time,
  sales_amount, response_rate_3m, response_rate_30s,
  reply_rate, satisfaction, shop_satisfaction,
  raw_metrics, upload_ip, is_abnormal, create_time
)
SELECT 22001, e.id, 2201, 1, 'demo_kf_001', CURDATE(), 'demo_kf_001',
       36, 34, 30,
       18.50, 22, 48,
       12888.00, 96.00, 88.00,
       98.00, 99.00, 98.00,
       '{"source":"qingbird_demo_seed"}', '127.0.0.1', 0, NOW()
FROM biz_employee e
WHERE e.login_account = 'demo_kf_001'
ON DUPLICATE KEY UPDATE
  employee_id = VALUES(employee_id),
  branch_id = VALUES(branch_id),
  platform_type = VALUES(platform_type),
  login_account = VALUES(login_account),
  consultation_count = VALUES(consultation_count),
  reception_count = VALUES(reception_count),
  effective_reception_count = VALUES(effective_reception_count),
  conversion_rate = VALUES(conversion_rate),
  first_response_time = VALUES(first_response_time),
  avg_response_time = VALUES(avg_response_time),
  sales_amount = VALUES(sales_amount),
  response_rate_3m = VALUES(response_rate_3m),
  response_rate_30s = VALUES(response_rate_30s),
  reply_rate = VALUES(reply_rate),
  satisfaction = VALUES(satisfaction),
  shop_satisfaction = VALUES(shop_satisfaction),
  raw_metrics = VALUES(raw_metrics),
  upload_ip = VALUES(upload_ip),
  is_abnormal = VALUES(is_abnormal),
  update_time = NOW();

COMMIT;
