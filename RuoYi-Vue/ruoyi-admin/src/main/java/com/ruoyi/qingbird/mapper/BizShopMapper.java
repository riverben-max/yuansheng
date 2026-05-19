package com.ruoyi.qingbird.mapper;

import com.ruoyi.qingbird.domain.BizShop;

/**
 * 店铺资产表 biz_shop 数据访问层
 */
public interface BizShopMapper {

    /**
     * 根据 shop_id 查询店铺，关联获取 employee_id 和 branch_id
     */
    BizShop selectBizShopById(Long shopId);
}
