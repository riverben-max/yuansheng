package com.ruoyi.qingbird.domain;

import java.math.BigDecimal;
import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 采集数据明细实体
 * 唯一键：shop_id + record_date + sub_account
 */
public class BizSpiderData extends BaseEntity {
    private static final long serialVersionUID = 1L;

    private Long id;
    private Long shopId;
    private Long employeeId;
    private Long branchId;

    @JsonFormat(pattern = "yyyy-MM-dd")
    private Date recordDate;

    /** 千牛客服子账号（无子账号时填主账号） */
    private String subAccount;

    /** 咨询人数 */
    private Integer consultationCount;
    /** 接待人数 */
    private Integer receptionCount;
    /** 有效接待人数 */
    private Integer effectiveReceptionCount;
    /** 转化率(%) */
    private BigDecimal conversionRate;
    /** 首响时长(秒) */
    private Integer firstResponseTime;
    /** 平均时长(秒) */
    private Integer avgResponseTime;
    /** 销售额(元) */
    private BigDecimal salesAmount;
    /** 3分钟回复率(%) */
    private BigDecimal responseRate3m;
    /** 30秒回复率(%) */
    private BigDecimal responseRate30s;
    /** 回复率(%) */
    private BigDecimal replyRate;
    /** 满意度(%) */
    private BigDecimal satisfaction;
    /** 店铺满意度(%) */
    private BigDecimal shopSatisfaction;

    /** 原始采集JSON备份 */
    private String rawMetrics;
    private String uploadIp;
    private Integer isAbnormal;

    // ---- Getters & Setters ----

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getShopId() { return shopId; }
    public void setShopId(Long shopId) { this.shopId = shopId; }

    public Long getEmployeeId() { return employeeId; }
    public void setEmployeeId(Long employeeId) { this.employeeId = employeeId; }

    public Long getBranchId() { return branchId; }
    public void setBranchId(Long branchId) { this.branchId = branchId; }

    public Date getRecordDate() { return recordDate; }
    public void setRecordDate(Date recordDate) { this.recordDate = recordDate; }

    public String getSubAccount() { return subAccount; }
    public void setSubAccount(String subAccount) { this.subAccount = subAccount; }

    public Integer getConsultationCount() { return consultationCount; }
    public void setConsultationCount(Integer consultationCount) { this.consultationCount = consultationCount; }

    public Integer getReceptionCount() { return receptionCount; }
    public void setReceptionCount(Integer receptionCount) { this.receptionCount = receptionCount; }

    public Integer getEffectiveReceptionCount() { return effectiveReceptionCount; }
    public void setEffectiveReceptionCount(Integer effectiveReceptionCount) { this.effectiveReceptionCount = effectiveReceptionCount; }

    public BigDecimal getConversionRate() { return conversionRate; }
    public void setConversionRate(BigDecimal conversionRate) { this.conversionRate = conversionRate; }

    public Integer getFirstResponseTime() { return firstResponseTime; }
    public void setFirstResponseTime(Integer firstResponseTime) { this.firstResponseTime = firstResponseTime; }

    public Integer getAvgResponseTime() { return avgResponseTime; }
    public void setAvgResponseTime(Integer avgResponseTime) { this.avgResponseTime = avgResponseTime; }

    public BigDecimal getSalesAmount() { return salesAmount; }
    public void setSalesAmount(BigDecimal salesAmount) { this.salesAmount = salesAmount; }

    public BigDecimal getResponseRate3m() { return responseRate3m; }
    public void setResponseRate3m(BigDecimal responseRate3m) { this.responseRate3m = responseRate3m; }

    public BigDecimal getResponseRate30s() { return responseRate30s; }
    public void setResponseRate30s(BigDecimal responseRate30s) { this.responseRate30s = responseRate30s; }

    public BigDecimal getReplyRate() { return replyRate; }
    public void setReplyRate(BigDecimal replyRate) { this.replyRate = replyRate; }

    public BigDecimal getSatisfaction() { return satisfaction; }
    public void setSatisfaction(BigDecimal satisfaction) { this.satisfaction = satisfaction; }

    public BigDecimal getShopSatisfaction() { return shopSatisfaction; }
    public void setShopSatisfaction(BigDecimal shopSatisfaction) { this.shopSatisfaction = shopSatisfaction; }

    public String getRawMetrics() { return rawMetrics; }
    public void setRawMetrics(String rawMetrics) { this.rawMetrics = rawMetrics; }

    public String getUploadIp() { return uploadIp; }
    public void setUploadIp(String uploadIp) { this.uploadIp = uploadIp; }

    public Integer getIsAbnormal() { return isAbnormal; }
    public void setIsAbnormal(Integer isAbnormal) { this.isAbnormal = isAbnormal; }
}
