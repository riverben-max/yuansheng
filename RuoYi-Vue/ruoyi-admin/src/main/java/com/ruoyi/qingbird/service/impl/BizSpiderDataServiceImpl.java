package com.ruoyi.qingbird.service.impl;

import java.math.BigDecimal;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.alibaba.fastjson2.JSON;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.qingbird.domain.BizEmployee;
import com.ruoyi.qingbird.domain.BizSpiderData;
import com.ruoyi.qingbird.domain.dto.SpiderDataUploadDTO;
import com.ruoyi.qingbird.mapper.BizEmployeeMapper;
import com.ruoyi.qingbird.mapper.BizSpiderDataMapper;
import com.ruoyi.qingbird.service.IBizSpiderDataService;

@Service
public class BizSpiderDataServiceImpl implements IBizSpiderDataService {

    @Autowired
    private BizSpiderDataMapper bizSpiderDataMapper;

    @Autowired
    private BizEmployeeMapper bizEmployeeMapper;

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
        if (uploadDTO.getLoginAccount() == null || uploadDTO.getLoginAccount().isBlank()) {
            throw new IllegalArgumentException("loginAccount 不能为空，请填写客服平台登录账号。");
        }
        if (uploadDTO.getPlatformType() == null) {
            throw new IllegalArgumentException("platformType 不能为空。");
        }
        if (uploadDTO.getRecordDate() == null) {
            throw new IllegalArgumentException("recordDate 不能为空。");
        }

        // 按 loginAccount 查员工档案（找不到时允许继续，标记异常）
        BizEmployee employee = bizEmployeeMapper.selectEmployeeByLoginAccount(uploadDTO.getLoginAccount().trim());

        Long employeeId = null;
        Long branchId = null;
        String abnormalReason = null;
        if (employee == null) {
            abnormalReason = "系统无对应客服档案";
        } else {
            employeeId = employee.getId();
            if (employee.getUserId() != null) {
                branchId = bizEmployeeMapper.selectBranchIdByUserId(employee.getUserId());
            }
        }

        BizSpiderData data = new BizSpiderData();
        data.setEmployeeId(employeeId);
        data.setBranchId(branchId);
        data.setPlatformType(uploadDTO.getPlatformType());
        data.setLoginAccount(uploadDTO.getLoginAccount().trim());
        data.setRecordDate(uploadDTO.getRecordDate());
        data.setSubAccount(uploadDTO.getSubAccount() != null ? uploadDTO.getSubAccount() : "");

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

        // 预警逻辑：无档案 or 3分钟回复率 < 50% 则标记异常
        if (abnormalReason != null) {
            data.setIsAbnormal(1);
            data.setAbnormalReason(abnormalReason);
        } else if (uploadDTO.getResponseRate3m() != null &&
            uploadDTO.getResponseRate3m().compareTo(new BigDecimal("50.0")) < 0) {
            data.setIsAbnormal(1);
            data.setAbnormalReason("3分钟回复率低于50%");
        } else {
            data.setIsAbnormal(0);
        }

        return bizSpiderDataMapper.upsertSpiderData(data);
    }
}
