package com.ruoyi.qingbird.domain;

import java.math.BigDecimal;
import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 结算信息对象 biz_settlement
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
public class BizSettlement extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    /** 结算ID */
    private Long id;

    /** 被结算的分公司ID */
    private Long branchId;

    /** 被结算的分公司名称 */
    @Excel(name = "分公司名称")
    private String branchName;

    /** 结算周期 */
    @Excel(name = "结算周期")
    private String settlementPeriod;

    /** 结算金额 */
    @Excel(name = "结算金额")
    private BigDecimal settlementAmount;

    /** 底薪 */
    @Excel(name = "底薪")
    private BigDecimal baseSalary;

    /** 佣金 */
    @Excel(name = "佣金")
    private BigDecimal commission;

    /** 扣罚 */
    @Excel(name = "扣罚")
    private BigDecimal penalty;

    /** 结算时间 */
    @JsonFormat(pattern = "yyyy-MM-dd")
    @Excel(name = "结算时间", width = 30, dateFormat = "yyyy-MM-dd")
    private Date settlementTime;

    public void setId(Long id) 
    {
        this.id = id;
    }

    public Long getId() 
    {
        return id;
    }

    public void setBranchId(Long branchId) 
    {
        this.branchId = branchId;
    }

    public Long getBranchId() 
    {
        return branchId;
    }

    public void setBranchName(String branchName) 
    {
        this.branchName = branchName;
    }

    public String getBranchName() 
    {
        return branchName;
    }

    public void setSettlementPeriod(String settlementPeriod) 
    {
        this.settlementPeriod = settlementPeriod;
    }

    public String getSettlementPeriod() 
    {
        return settlementPeriod;
    }

    public void setSettlementAmount(BigDecimal settlementAmount) 
    {
        this.settlementAmount = settlementAmount;
    }

    public BigDecimal getSettlementAmount() 
    {
        return settlementAmount;
    }

    public void setBaseSalary(BigDecimal baseSalary) 
    {
        this.baseSalary = baseSalary;
    }

    public BigDecimal getBaseSalary() 
    {
        return baseSalary;
    }

    public void setCommission(BigDecimal commission) 
    {
        this.commission = commission;
    }

    public BigDecimal getCommission() 
    {
        return commission;
    }

    public void setPenalty(BigDecimal penalty) 
    {
        this.penalty = penalty;
    }

    public BigDecimal getPenalty() 
    {
        return penalty;
    }

    public void setSettlementTime(Date settlementTime) 
    {
        this.settlementTime = settlementTime;
    }

    public Date getSettlementTime() 
    {
        return settlementTime;
    }
}
