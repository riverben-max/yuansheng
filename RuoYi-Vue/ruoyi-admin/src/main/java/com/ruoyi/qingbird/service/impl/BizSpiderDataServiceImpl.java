package com.ruoyi.qingbird.service.impl;

import java.math.BigDecimal;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.alibaba.fastjson2.JSON;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.qingbird.domain.BizSpiderData;
import com.ruoyi.qingbird.domain.dto.SpiderDataUploadDTO;
import com.ruoyi.qingbird.mapper.BizSpiderDataMapper;
import com.ruoyi.qingbird.service.IBizSpiderDataService;

@Service
public class BizSpiderDataServiceImpl implements IBizSpiderDataService {

    @Autowired
    private BizSpiderDataMapper bizSpiderDataMapper;

    @Override
    public BizSpiderData selectSpiderDataById(Long id) {
        return bizSpiderDataMapper.selectSpiderDataById(id);
    }

    @Override
    public List<BizSpiderData> selectSpiderDataList(BizSpiderData bizSpiderData) {
        if (!SecurityUtils.isAdmin() && !SecurityUtils.hasRole("admin") && SecurityUtils.hasRole("manager")) {
            bizSpiderData.setBranchId(SecurityUtils.getDeptId());
        }
        return bizSpiderDataMapper.selectSpiderDataList(bizSpiderData);
    }

    @Override
    public int handleSpiderUpload(SpiderDataUploadDTO uploadDTO, String uploadIp) {
        BizSpiderData data = new BizSpiderData();
        data.setShopId(uploadDTO.getShopId());

        // TODO: 后续可通过 shop_id 查 biz_shop 自动取 employee_id
        data.setEmployeeId(1L);

        data.setRecordDate(uploadDTO.getRecordDate());
        // 子账号为空时默认空字符串（匹配唯一键 NOT NULL DEFAULT ''）
        data.setSubAccount(uploadDTO.getSubAccount() != null ? uploadDTO.getSubAccount() : "");

        // 采集字段映射
        data.setConsultationCount(uploadDTO.getConsultationCount());
        data.setReceptionCount(uploadDTO.getReceptionCount());
        data.setEffectiveReceptionCount(uploadDTO.getEffectiveReceptionCount());
        data.setConversionRate(uploadDTO.getConversionRate());
        data.setFirstResponseTime(uploadDTO.getFirstResponseTime());
        data.setAvgResponseTime(uploadDTO.getAvgResponseTime());
        data.setSalesAmount(uploadDTO.getSalesAmount());
        data.setResponseRate3m(uploadDTO.getResponseRate3m());
        data.setResponseRate30s(uploadDTO.getResponseRate30s());
        data.setReplyRate(uploadDTO.getReplyRate());
        data.setSatisfaction(uploadDTO.getSatisfaction());
        data.setShopSatisfaction(uploadDTO.getShopSatisfaction());
        data.setUploadIp(uploadIp);

        if (uploadDTO.getRawMetrics() != null) {
            data.setRawMetrics(JSON.toJSONString(uploadDTO.getRawMetrics()));
        }

        // 预警逻辑：3分钟回复率 < 50% 则标记异常
        if (uploadDTO.getResponseRate3m() != null &&
            uploadDTO.getResponseRate3m().compareTo(new BigDecimal("50.0")) < 0) {
            data.setIsAbnormal(1);
        } else {
            data.setIsAbnormal(0);
        }

        return bizSpiderDataMapper.upsertSpiderData(data);
    }
}
