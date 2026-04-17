package com.ruoyi.qingbird.domain.dto;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 控制台大屏聚合数据 VO（真实数据版）
 */
public class DashboardDataVO {

    // ===== 核心 KPI（真实数据）=====
    /** 今日总销售额（来自 biz_spider_data.sales_amount 汇总） */
    private BigDecimal todaySalesAmount;
    /** 在职员工数（来自 biz_employee） */
    private Integer activeEmployeeCount;
    /** 运营店铺数（distinct shop_id） */
    private Integer activeShopCount;
    /** 全集团产品总量（暂为 0，後续接 ERP 商品表） */
    private Integer totalProductCount = 0;

    // ===== 业务规模（真实数据）=====
    /** 今日新增接待（今日 consultation_count 汇总） */
    private Integer todayConsultation;
    /** 今日子账号数（distinct employee_id） */
    private Integer todayOperatorCount;
    /** 近30天咨询总量 */
    private Integer monthConsultation;

    // ===== 合规预警（真实数据）=====
    /** 今日新增异常数 */
    private Integer todayAbnormalCount;
    /** 今日整理（今日正常达标数） */
    private Integer todayNormalCount;
    /** 今日高危积分（response_rate_3m < 50 的记录数） */
    private Integer todayHighRiskCount;
    /** 本月累计异常数 */
    private Integer monthAbnormalCount;

    // ===== 趋势图（近7天）=====
    private List<Map<String, Object>> trendData;
    /** 异常预警列表（最近5条） */
    private List<Map<String, Object>> alertList;

    // ===== Getters & Setters =====
    public BigDecimal getTodaySalesAmount() { return todaySalesAmount; }
    public void setTodaySalesAmount(BigDecimal v) { this.todaySalesAmount = v; }
    public Integer getActiveEmployeeCount() { return activeEmployeeCount; }
    public void setActiveEmployeeCount(Integer v) { this.activeEmployeeCount = v; }
    public Integer getActiveShopCount() { return activeShopCount; }
    public void setActiveShopCount(Integer v) { this.activeShopCount = v; }
    public Integer getTotalProductCount() { return totalProductCount; }
    public void setTotalProductCount(Integer v) { this.totalProductCount = v; }
    public Integer getTodayConsultation() { return todayConsultation; }
    public void setTodayConsultation(Integer v) { this.todayConsultation = v; }
    public Integer getTodayOperatorCount() { return todayOperatorCount; }
    public void setTodayOperatorCount(Integer v) { this.todayOperatorCount = v; }
    public Integer getMonthConsultation() { return monthConsultation; }
    public void setMonthConsultation(Integer v) { this.monthConsultation = v; }
    public Integer getTodayAbnormalCount() { return todayAbnormalCount; }
    public void setTodayAbnormalCount(Integer v) { this.todayAbnormalCount = v; }
    public Integer getTodayNormalCount() { return todayNormalCount; }
    public void setTodayNormalCount(Integer v) { this.todayNormalCount = v; }
    public Integer getTodayHighRiskCount() { return todayHighRiskCount; }
    public void setTodayHighRiskCount(Integer v) { this.todayHighRiskCount = v; }
    public Integer getMonthAbnormalCount() { return monthAbnormalCount; }
    public void setMonthAbnormalCount(Integer v) { this.monthAbnormalCount = v; }
    public List<Map<String, Object>> getTrendData() { return trendData; }
    public void setTrendData(List<Map<String, Object>> v) { this.trendData = v; }
    public List<Map<String, Object>> getAlertList() { return alertList; }
    public void setAlertList(List<Map<String, Object>> v) { this.alertList = v; }
}
