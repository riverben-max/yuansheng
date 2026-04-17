package com.ruoyi.qingbird.mapper;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 控制台聚合查询 Mapper（专用汇总 SQL）
 */
public interface DashboardMapper {

    /** 今日销售额汇总 */
    BigDecimal sumTodaySales();

    /** 近30天销售额汇总 */
    BigDecimal sumMonthSales();

    /** 在职员工数 */
    Integer countActiveEmployees();

    /** 运营中的独立店铺数（按 shop_id distinct） */
    Integer countActiveShops();

    /** 今日采集条数 */
    Integer countTodayUploads();

    /** 今日接待人数汇总 */
    Integer sumTodayConsultation();

    /** 近30天接待人数 */
    Integer sumMonthConsultation();

    /** 今日子账号操作员数 */
    Integer countTodayOperators();

    /** 今日异常数 */
    Integer countTodayAbnormal();

    /** 今日正常数 */
    Integer countTodayNormal();

    /** 今日高危（3分钟响应率 < 50%）的记录数 */
    Integer countTodayHighRisk();

    /** 本月累计异常数 */
    Integer countMonthAbnormal();

    /** 近7天趋势（日期、接待量、异常数） */
    List<Map<String, Object>> selectWeekTrend();

    /** 最近5条异常预警详情 */
    List<Map<String, Object>> selectRecentAlerts();
}
