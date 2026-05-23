package com.ruoyi.qingbird.mapper;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.apache.ibatis.annotations.Param;

/**
 * 控制台聚合查询 Mapper（专用汇总 SQL）
 */
public interface DashboardMapper {

    /** 今日销售额汇总 */
    BigDecimal sumTodaySales(@Param("branchId") Long branchId);

    /** 近30天销售额汇总 */
    BigDecimal sumMonthSales(@Param("branchId") Long branchId);

    /** 在职员工数 */
    Integer countActiveEmployees(@Param("branchId") Long branchId);

    /** 运营中的独立店铺数（按 shop_id distinct） */
    Integer countActiveShops(@Param("branchId") Long branchId);

    /** 今日采集条数 */
    Integer countTodayUploads(@Param("branchId") Long branchId);

    /** 今日接待人数汇总 */
    Integer sumTodayConsultation(@Param("branchId") Long branchId);

    /** 近30天接待人数 */
    Integer sumMonthConsultation(@Param("branchId") Long branchId);

    /** 今日子账号操作员数 */
    Integer countTodayOperators(@Param("branchId") Long branchId);

    /** 今日异常数 */
    Integer countTodayAbnormal(@Param("branchId") Long branchId);

    /** 今日正常数 */
    Integer countTodayNormal(@Param("branchId") Long branchId);

    /** 今日高危（3分钟响应率 < 50%）的记录数 */
    Integer countTodayHighRisk(@Param("branchId") Long branchId);

    /** 本月累计异常数 */
    Integer countMonthAbnormal(@Param("branchId") Long branchId);

    /** 近7天趋势（日期、接待量、异常数） */
    List<Map<String, Object>> selectWeekTrend(@Param("branchId") Long branchId);

    /** 最近5条异常预警详情 */
    List<Map<String, Object>> selectRecentAlerts(@Param("branchId") Long branchId);
}
