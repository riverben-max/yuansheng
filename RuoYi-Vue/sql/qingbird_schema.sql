-- ==========================================
-- 青鸟集团 - 自动化数据采集与ERP系统 业务表设计
-- 建议运行于已经导入了 RuoYi-Vue ry_XXX.sql 的 MySQL 数据库中
-- ==========================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 店铺资产表 biz_shop
-- ----------------------------
DROP TABLE IF EXISTS `biz_shop`;
CREATE TABLE `biz_shop` (
  `shop_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '店铺ID',
  `shop_name` varchar(100) NOT NULL COMMENT '店铺名称（如：Q43-糖小精美妆）',
  `platform_type` tinyint(4) NOT NULL DEFAULT '1' COMMENT '平台：1淘宝 2京东 3拼多多',
  `login_account` varchar(100) DEFAULT NULL COMMENT '千牛/平台登录主账号',
  `shop_key` varchar(50) DEFAULT NULL COMMENT '平台唯一标识（用于爬虫识别当前页面归属）',
  `branch_id` bigint(20) NOT NULL COMMENT '关联分公司(映射 sys_dept.dept_id)',
  `employee_id` bigint(20) NOT NULL COMMENT '绑定负责人(映射 sys_user.user_id)',
  `status` char(1) DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(255) DEFAULT NULL COMMENT '备注',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`shop_id`),
  UNIQUE KEY `uk_shop_key` (`shop_key`),
  KEY `idx_branch_id` (`branch_id`),
  KEY `idx_employee_id` (`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='店铺资产表';

-- ----------------------------
-- 初期测试数据: 店铺
-- ----------------------------
INSERT INTO `biz_shop` (`shop_id`, `shop_name`, `platform_type`, `login_account`, `shop_key`, `branch_id`, `employee_id`, `remark`) VALUES
(1, 'Q43-糖小精美妆-全包-服-X5', 1, 'qingbird_main_01', '糖小精', 100, 1, '测试店铺A'),
(2, 'Q43-大山家 耙柑-售前售后服 X5', 1, 'qingbird_main_01', '大山家', 100, 1, '测试店铺B');

-- ----------------------------
-- 2. 采集数据明细表 biz_spider_data
--    业务约定: 客户端上传 N 条就保留 N 条，不在 (login_account, sub_account, date)
--    维度做服务端去重；同一店铺多个登录账号即使采集到同名子账号也独立保存。
-- ----------------------------
DROP TABLE IF EXISTS `biz_spider_data`;
CREATE TABLE `biz_spider_data` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `shop_id` bigint(20) DEFAULT NULL COMMENT '兼容旧版：关联业务店铺 ID',
  `employee_id` bigint(20) DEFAULT NULL COMMENT '上传员工 ID',
  `branch_id` bigint(20) DEFAULT NULL COMMENT '分公司/部门 ID',
  `platform_type` tinyint(4) NOT NULL DEFAULT '1' COMMENT '平台：1淘宝 2京东 3拼多多 4抖店',
  `login_account` varchar(100) NOT NULL COMMENT '客服平台登录主账号',
  `record_date` date NOT NULL COMMENT '数据日期（如2026-03-31）',
  `sub_account` varchar(100) NOT NULL DEFAULT '' COMMENT '千牛客服子账号（无子账号时填主账号）',
  `consultation_count` int(11) DEFAULT NULL COMMENT '咨询人数',
  `reception_count` int(11) DEFAULT NULL COMMENT '接待人数',
  `effective_reception_count` int(11) DEFAULT NULL COMMENT '有效接待人数',
  `conversion_rate` decimal(5,2) DEFAULT NULL COMMENT '转化率(%)',
  `first_response_time` int(11) DEFAULT NULL COMMENT '首响时长(秒)',
  `avg_response_time` int(11) DEFAULT NULL COMMENT '平均时长(秒)',
  `sales_amount` decimal(12,2) DEFAULT NULL COMMENT '销售额(元)',
  `response_rate_3m` decimal(5,2) DEFAULT NULL COMMENT '3分钟回复率(%)',
  `response_rate_30s` decimal(5,2) DEFAULT NULL COMMENT '30秒回复率(%)',
  `reply_rate` decimal(5,2) DEFAULT NULL COMMENT '回复率(%)',
  `satisfaction` decimal(5,2) DEFAULT NULL COMMENT '满意度(%)',
  `shop_satisfaction` decimal(5,2) DEFAULT NULL COMMENT '店铺满意度(%)',
  `raw_metrics` json DEFAULT NULL COMMENT '原始采集字典数据（JSON备份）',
  `upload_ip` varchar(45) DEFAULT NULL COMMENT '上传来源IP',
  `is_abnormal` tinyint(2) DEFAULT '0' COMMENT '是否触发预警(0正常 1低于阈值异常)',
  `abnormal_reason` varchar(255) DEFAULT NULL COMMENT '异常原因',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_login_platform_date_sub` (`login_account`,`platform_type`,`record_date`,`sub_account`) COMMENT '辅助查询索引（不做唯一约束）',
  KEY `idx_branch_id` (`branch_id`),
  KEY `idx_login_account` (`login_account`),
  KEY `idx_record_date` (`record_date`),
  KEY `idx_sub_account` (`sub_account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集数据明细表';

-- ----------------------------
-- 3. 结算信息表 biz_settlement
-- ----------------------------
DROP TABLE IF EXISTS `biz_settlement`;
CREATE TABLE `biz_settlement` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '结算ID',
  `branch_id` bigint(20) DEFAULT NULL COMMENT '被结算的分公司ID',
  `branch_name` varchar(255) DEFAULT NULL COMMENT '被结算的分公司名称',
  `settlement_period` varchar(50) DEFAULT NULL COMMENT '结算周期',
  `settlement_amount` decimal(10,2) DEFAULT '0.00' COMMENT '结算金额',
  `base_salary` decimal(10,2) DEFAULT '0.00' COMMENT '底薪',
  `commission` decimal(10,2) DEFAULT '0.00' COMMENT '佣金',
  `penalty` decimal(10,2) DEFAULT '0.00' COMMENT '扣罚',
  `settlement_time` datetime DEFAULT NULL COMMENT '结算时间',
  `remark` varchar(500) DEFAULT NULL COMMENT '结算备注',
  `create_by` varchar(64) DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_branch_period` (`branch_id`,`settlement_period`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结算信息表';

SET FOREIGN_KEY_CHECKS = 1;
