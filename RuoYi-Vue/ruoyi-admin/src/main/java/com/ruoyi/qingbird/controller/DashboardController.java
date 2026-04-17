package com.ruoyi.qingbird.controller;

import java.math.BigDecimal;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
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

    @PreAuthorize("@ss.hasPermi('qingbird:dashboard:list') or @ss.hasAnyRoles('admin,manager')")
    @GetMapping("/overview")
    public AjaxResult getOverview() {
        DashboardDataVO vo = new DashboardDataVO();

        // ===== 核心 KPI（真实数据）=====
        BigDecimal todaySales = dashboardMapper.sumTodaySales();
        vo.setTodaySalesAmount(todaySales != null ? todaySales : BigDecimal.ZERO);
        vo.setActiveEmployeeCount(dashboardMapper.countActiveEmployees());
        vo.setActiveShopCount(dashboardMapper.countActiveShops());

        // ===== 业务规模（真实数据）=====
        vo.setTodayConsultation(dashboardMapper.sumTodayConsultation());
        vo.setTodayOperatorCount(dashboardMapper.countTodayOperators());
        vo.setMonthConsultation(dashboardMapper.sumMonthConsultation());

        // ===== 合规预警（真实数据）=====
        vo.setTodayAbnormalCount(dashboardMapper.countTodayAbnormal());
        vo.setTodayNormalCount(dashboardMapper.countTodayNormal());
        vo.setTodayHighRiskCount(dashboardMapper.countTodayHighRisk());
        vo.setMonthAbnormalCount(dashboardMapper.countMonthAbnormal());

        // ===== 趋势 & 预警列表（真实数据）=====
        vo.setTrendData(dashboardMapper.selectWeekTrend());
        vo.setAlertList(dashboardMapper.selectRecentAlerts());

        return success(vo);
    }
}
