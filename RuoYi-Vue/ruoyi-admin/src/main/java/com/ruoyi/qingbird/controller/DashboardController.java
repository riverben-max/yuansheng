package com.ruoyi.qingbird.controller;

import java.math.BigDecimal;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.qingbird.domain.dto.DashboardDataVO;
import com.ruoyi.qingbird.mapper.DashboardMapper;

/**
 * 控制台大屏 Controller（真实数据版）
 */
@RestController
@RequestMapping("/qingbird/dashboard")
public class DashboardController extends BaseController {

    @Autowired
    private DashboardMapper dashboardMapper;

    @PreAuthorize("@ss.hasPermi('qingbird:dashboard:list')")
    @GetMapping("/overview")
    public AjaxResult getOverview() {
        DashboardDataVO vo = new DashboardDataVO();
        Long branchId = getDashboardScopeBranchId();

        // ===== 核心 KPI（真实数据）=====
        BigDecimal todaySales = dashboardMapper.sumTodaySales(branchId);
        vo.setTodaySalesAmount(todaySales != null ? todaySales : BigDecimal.ZERO);
        vo.setActiveEmployeeCount(dashboardMapper.countActiveEmployees(branchId));
        vo.setActiveShopCount(dashboardMapper.countActiveShops(branchId));

        // ===== 业务规模（真实数据）=====
        vo.setTodayConsultation(dashboardMapper.sumTodayConsultation(branchId));
        vo.setTodayOperatorCount(dashboardMapper.countTodayOperators(branchId));
        vo.setMonthConsultation(dashboardMapper.sumMonthConsultation(branchId));

        // ===== 合规预警（真实数据）=====
        vo.setTodayAbnormalCount(dashboardMapper.countTodayAbnormal(branchId));
        vo.setTodayNormalCount(dashboardMapper.countTodayNormal(branchId));
        vo.setTodayHighRiskCount(dashboardMapper.countTodayHighRisk(branchId));
        vo.setMonthAbnormalCount(dashboardMapper.countMonthAbnormal(branchId));

        // ===== 趋势 & 预警列表（真实数据）=====
        vo.setTrendData(dashboardMapper.selectWeekTrend(branchId));
        vo.setAlertList(dashboardMapper.selectRecentAlerts(branchId));

        return success(vo);
    }

    private Long getDashboardScopeBranchId() {
        return SecurityUtils.isAdmin() ? null : SecurityUtils.getDeptId();
    }
}
