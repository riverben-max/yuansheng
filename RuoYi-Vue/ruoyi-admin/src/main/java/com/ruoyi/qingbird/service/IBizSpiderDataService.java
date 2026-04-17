package com.ruoyi.qingbird.service;

import java.util.List;
import com.ruoyi.qingbird.domain.BizSpiderData;
import com.ruoyi.qingbird.domain.dto.SpiderDataUploadDTO;

public interface IBizSpiderDataService {
    
    /**
     * 根据主键查询
     */
    BizSpiderData selectSpiderDataById(Long id);

    /**
     * 查询列表
     */
    List<BizSpiderData> selectSpiderDataList(BizSpiderData bizSpiderData);

    /**
     * 客户端上传采集数据处理（Upsert）
     */
    int handleSpiderUpload(SpiderDataUploadDTO uploadDTO, String uploadIp);
}
