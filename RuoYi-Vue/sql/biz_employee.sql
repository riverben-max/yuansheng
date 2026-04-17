-- =============================================
-- 分公司员工花名册表
-- =============================================
DROP TABLE IF EXISTS `biz_employee`;
CREATE TABLE `biz_employee` (
  `id`               BIGINT(20) NOT NULL AUTO_INCREMENT          COMMENT '主键',
  `user_id`          BIGINT(20) DEFAULT NULL                     COMMENT '绑定系统用户ID',
  `login_account`    VARCHAR(50) DEFAULT ''                      COMMENT '登录账号',
  `id_card`          VARCHAR(18) DEFAULT ''                      COMMENT '身份证号',
  `address`          VARCHAR(255) DEFAULT ''                     COMMENT '联系地址',
  `branch_code`      VARCHAR(50)  NOT NULL                       COMMENT '所属分公司编号',
  `name`             VARCHAR(50)  NOT NULL                       COMMENT '员工姓名',
  `avatar_color`     VARCHAR(20)  DEFAULT '#6C4EF2'              COMMENT '头像背景色',
  `position`         VARCHAR(100) DEFAULT ''                     COMMENT '岗位/职位',
  `department`       VARCHAR(100) DEFAULT ''                     COMMENT '部门',
  `source`           VARCHAR(100) DEFAULT ''                     COMMENT '来源渠道',
  `birthday`         DATE                                        COMMENT '生日',
  `mobile`           VARCHAR(20)  DEFAULT ''                     COMMENT '联系电话',
  `intern_date`      DATE                                        COMMENT '实习开始日期',
  `hire_date`        DATE                                        COMMENT '正式入职日期',
  `contract_status`  TINYINT(1)   DEFAULT 0                      COMMENT '合同状态 0-未签署 1-已签署',
  `salary_base`      DECIMAL(10,2) DEFAULT 0.00                  COMMENT '基本工资',
  `deposit_amount`   DECIMAL(10,2) DEFAULT 0.00                  COMMENT '押金金额',
  `status`           CHAR(1)      DEFAULT '0'                    COMMENT '在职状态 0-在职 1-离职',
  `resign_date`      DATE                                        COMMENT '离职日期',
  `remark`           VARCHAR(500) DEFAULT ''                     COMMENT '备注',
  `create_by`        VARCHAR(64)  DEFAULT ''                     COMMENT '创建者',
  `create_time`      DATETIME                                    COMMENT '创建时间',
  `update_by`        VARCHAR(64)  DEFAULT ''                     COMMENT '更新者',
  `update_time`      DATETIME                                    COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='分公司员工花名册';

-- 插入样例数据
INSERT INTO `biz_employee` (
  `user_id`, `login_account`, `id_card`, `address`,
  `branch_code`, `name`, `avatar_color`, `position`, `department`,
  `source`, `birthday`, `mobile`,
  `intern_date`, `hire_date`, `contract_status`,
  `salary_base`, `deposit_amount`, `status`, `create_time`
) VALUES (
  NULL, 'q43_manager', '', '',
  'B-1773208272961', 'Q43主管', '#6C4EF2', 'Q43主管', '管理层',
  '未说明', NULL, '13562863535',
  NULL, '2026-03-07', 0,
  0.00, 0.00, '0', NOW()
);
