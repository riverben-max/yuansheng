-- =============================================
-- 分公司业务主体档案表
-- 存储分公司的审核状态、提款结算资料、营业执照等
-- =============================================
DROP TABLE IF EXISTS `biz_branch_info`;
CREATE TABLE `biz_branch_info` (
  `id`                    BIGINT(20)      NOT NULL AUTO_INCREMENT         COMMENT '主键',
  `branch_id`             BIGINT(20)      NOT NULL                        COMMENT '关联的实际底层部门 sys_dept.dept_id',
  `workplace_name`        VARCHAR(100)    DEFAULT ''                      COMMENT '职场名字(内部代号，总管修改)',
  `company_name`          VARCHAR(200)    NOT NULL                        COMMENT '对外的正式公司/企业名称',
  `business_license`      VARCHAR(500)    DEFAULT ''                      COMMENT '营业执照照片 URL',
  `legal_person_name`     VARCHAR(50)     DEFAULT ''                      COMMENT '法定代表人/负责人姓名',
  `id_card_front`         VARCHAR(500)    DEFAULT ''                      COMMENT '身份证正面照片 URL',
  `id_card_back`          VARCHAR(500)    DEFAULT ''                      COMMENT '身份证反面照片 URL',
  `contact_phone`         VARCHAR(50)     DEFAULT ''                      COMMENT '联系电话',
  `contact_address`       VARCHAR(255)    DEFAULT ''                      COMMENT '联系地址',
  `settlement_accounts`   JSON                                            COMMENT '结算账号列表JSON (支持微信/支付宝/公账共存)',
  `audit_status`          TINYINT(1)      DEFAULT 0                       COMMENT '审核状态 (0:未完善并打回 1:待审核 2:已通过生效)',
  `create_by`             VARCHAR(64)     DEFAULT ''                      COMMENT '创建者',
  `create_time`           DATETIME                                        COMMENT '创建时间(入驻时间)',
  `update_by`             VARCHAR(64)     DEFAULT ''                      COMMENT '更新者',
  `update_time`           DATETIME                                        COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_branch_id` (`branch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分公司业务主体档案表';
