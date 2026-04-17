-- =============================================
-- 薪资核算记录表
-- =============================================
DROP TABLE IF EXISTS `biz_salary_record`;
CREATE TABLE `biz_salary_record` (
  `id`                BIGINT(20)     NOT NULL AUTO_INCREMENT         COMMENT '主键',
  `salary_month`      VARCHAR(7)     NOT NULL                        COMMENT '账期 (YYYY-MM)',
  `branch_code`       VARCHAR(50)    NOT NULL                        COMMENT '所属分公司编号',
  `name`              VARCHAR(50)    NOT NULL                        COMMENT '员工姓名',
  `position`          VARCHAR(100)   DEFAULT ''                      COMMENT '岗位',
  `avatar_color`      VARCHAR(20)    DEFAULT '#6C4EF2'               COMMENT '头像背景色',
  `base_wage`         DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '底薪基数',
  `attendance_days`   INT            DEFAULT 30                      COMMENT '出勤天数',
  `performance_pay`   DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '当月底薪绩效',
  `shop_daily_rate`   DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '在岗日薪(店铺档)',
  `tier_rate`         INT            DEFAULT 0                       COMMENT '档位倍率(人/天)',
  `promotion_bonus`   DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '晋级奖金',
  `standby_deduction` DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '待岗扣款(负值)',
  `leave_deduction`   DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '请假扣款(负值)',
  `loan_deduction`    DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '借款金额',
  `unit_subsidy`      DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '单件补贴',
  `special_subsidy`   DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '专项补贴',
  `late_deduction`    DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '迟到扣款(负值)',
  `mid_subsidy`       DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '15日补贴',
  `extra_wage`        DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '额外工资',
  `policy_bonus_note` VARCHAR(500)   DEFAULT ''                      COMMENT '政策奖金备注',
  `actual_total`      DECIMAL(10,2)  DEFAULT 0.00                    COMMENT '实发合计',
  `create_by`         VARCHAR(64)    DEFAULT ''                      COMMENT '创建者',
  `create_time`       DATETIME                                       COMMENT '创建时间',
  `update_by`         VARCHAR(64)    DEFAULT ''                      COMMENT '更新者',
  `update_time`       DATETIME                                       COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_salary_month` (`salary_month`),
  KEY `idx_branch_code`  (`branch_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='薪资核算记录表';
