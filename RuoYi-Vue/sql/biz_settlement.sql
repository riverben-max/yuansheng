USE `ry-vue`;

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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结算信息表';
