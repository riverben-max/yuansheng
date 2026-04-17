USE `ry-vue`;

-- ----------------------------
-- 1. 创建文章表
-- ----------------------------
DROP TABLE IF EXISTS `biz_cloud_doc`;
CREATE TABLE `biz_cloud_doc` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '文章ID',
  `title` varchar(255) NOT NULL COMMENT '文章标题',
  `category` varchar(50) DEFAULT NULL COMMENT '文章分类（存字典键值）',
  `content` longtext COMMENT '富文本内容',
  `status` char(1) DEFAULT '0' COMMENT '状态（0正常 1隐藏）',
  `create_by` varchar(64) DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云文档文章表';

-- ----------------------------
-- 2. 新增云文档分类字典
-- ----------------------------
-- 字典类型
INSERT INTO sys_dict_type(dict_id, dict_name, dict_type, status, create_by, create_time, update_by, update_time, remark)
SELECT (SELECT IFNULL(MAX(dict_id), 0) + 1 FROM sys_dict_type dummy), '云文档分类', 'biz_cloud_doc_category', '0', 'admin', sysdate(), '', null, '云文档文章类型字典'
FROM dual WHERE NOT EXISTS (SELECT 1 FROM sys_dict_type WHERE dict_type = 'biz_cloud_doc_category');

-- 字典数据
INSERT INTO sys_dict_data(dict_sort, dict_label, dict_value, dict_type, css_class, list_class, is_default, status, create_by, create_time, update_by, update_time, remark)
SELECT 1, '集团公共规章', 'group', 'biz_cloud_doc_category', '', 'primary', 'Y', '0', 'admin', sysdate(), '', null, '集团全员可见'
FROM dual WHERE NOT EXISTS (SELECT 1 FROM sys_dict_data WHERE dict_type = 'biz_cloud_doc_category' AND dict_value = 'group');

INSERT INTO sys_dict_data(dict_sort, dict_label, dict_value, dict_type, css_class, list_class, is_default, status, create_by, create_time, update_by, update_time, remark)
SELECT 2, '数据物证留证', 'evidence', 'biz_cloud_doc_category', '', 'warning', 'N', '0', 'admin', sysdate(), '', null, '分公司可见'
FROM dual WHERE NOT EXISTS (SELECT 1 FROM sys_dict_data WHERE dict_type = 'biz_cloud_doc_category' AND dict_value = 'evidence');

INSERT INTO sys_dict_data(dict_sort, dict_label, dict_value, dict_type, css_class, list_class, is_default, status, create_by, create_time, update_by, update_time, remark)
SELECT 3, '我的私有文件', 'private', 'biz_cloud_doc_category', '', 'danger', 'N', '0', 'admin', sysdate(), '', null, '仅本人'
FROM dual WHERE NOT EXISTS (SELECT 1 FROM sys_dict_data WHERE dict_type = 'biz_cloud_doc_category' AND dict_value = 'private');
