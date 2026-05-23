package com.ruoyi.qingbird.mapper;

import java.util.List;
import com.ruoyi.qingbird.domain.BizSpiderData;

public interface BizSpiderDataMapper {
    /**
     * 根据店铺和日期查询
     */
    BizSpiderData selectSpiderDataById(Long id);

    /**
     * 查询列表
     */
    List<BizSpiderData> selectSpiderDataList(BizSpiderData bizSpiderData);

    /**
     * 新增或更新（Upsert，按 shop_id 和 record_date）
     */
    int upsertSpiderData(BizSpiderData bizSpiderData);

    /**
     * 根据 ID 删除
     */
    int deleteSpiderDataById(Long id);
}
