package com.ruoyi.qingbird.domain;

import java.math.BigDecimal;
import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 薪资核算记录 Domain
 */
public class BizSalaryRecord extends BaseEntity {

    private Long id;

    @Excel(name = "账期")
    private String salaryMonth;

    private String branchCode;

    @Excel(name = "员工姓名")
    private String name;

    @Excel(name = "岗位")
    private String position;

    private String avatarColor;

    @Excel(name = "底薪基数")
    private BigDecimal baseWage;

    @Excel(name = "出勤天数")
    private Integer attendanceDays;

    @Excel(name = "当月底薪绩效")
    private BigDecimal performancePay;

    private BigDecimal shopDailyRate;
    private Integer tierRate;

    @Excel(name = "晋级奖金")
    private BigDecimal promotionBonus;

    private BigDecimal standbyDeduction;
    private BigDecimal leaveDeduction;
    private BigDecimal loanDeduction;
    private BigDecimal unitSubsidy;
    private BigDecimal specialSubsidy;

    @Excel(name = "迟到扣款")
    private BigDecimal lateDeduction;

    private BigDecimal midSubsidy;
    private BigDecimal extraWage;
    private String policyBonusNote;

    @Excel(name = "实发合计")
    private BigDecimal actualTotal;

    // ===== Getters & Setters =====

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getSalaryMonth() { return salaryMonth; }
    public void setSalaryMonth(String salaryMonth) { this.salaryMonth = salaryMonth; }

    public String getBranchCode() { return branchCode; }
    public void setBranchCode(String branchCode) { this.branchCode = branchCode; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getPosition() { return position; }
    public void setPosition(String position) { this.position = position; }

    public String getAvatarColor() { return avatarColor; }
    public void setAvatarColor(String avatarColor) { this.avatarColor = avatarColor; }

    public BigDecimal getBaseWage() { return baseWage; }
    public void setBaseWage(BigDecimal baseWage) { this.baseWage = baseWage; }

    public Integer getAttendanceDays() { return attendanceDays; }
    public void setAttendanceDays(Integer attendanceDays) { this.attendanceDays = attendanceDays; }

    public BigDecimal getPerformancePay() { return performancePay; }
    public void setPerformancePay(BigDecimal performancePay) { this.performancePay = performancePay; }

    public BigDecimal getShopDailyRate() { return shopDailyRate; }
    public void setShopDailyRate(BigDecimal shopDailyRate) { this.shopDailyRate = shopDailyRate; }

    public Integer getTierRate() { return tierRate; }
    public void setTierRate(Integer tierRate) { this.tierRate = tierRate; }

    public BigDecimal getPromotionBonus() { return promotionBonus; }
    public void setPromotionBonus(BigDecimal promotionBonus) { this.promotionBonus = promotionBonus; }

    public BigDecimal getStandbyDeduction() { return standbyDeduction; }
    public void setStandbyDeduction(BigDecimal standbyDeduction) { this.standbyDeduction = standbyDeduction; }

    public BigDecimal getLeaveDeduction() { return leaveDeduction; }
    public void setLeaveDeduction(BigDecimal leaveDeduction) { this.leaveDeduction = leaveDeduction; }

    public BigDecimal getLoanDeduction() { return loanDeduction; }
    public void setLoanDeduction(BigDecimal loanDeduction) { this.loanDeduction = loanDeduction; }

    public BigDecimal getUnitSubsidy() { return unitSubsidy; }
    public void setUnitSubsidy(BigDecimal unitSubsidy) { this.unitSubsidy = unitSubsidy; }

    public BigDecimal getSpecialSubsidy() { return specialSubsidy; }
    public void setSpecialSubsidy(BigDecimal specialSubsidy) { this.specialSubsidy = specialSubsidy; }

    public BigDecimal getLateDeduction() { return lateDeduction; }
    public void setLateDeduction(BigDecimal lateDeduction) { this.lateDeduction = lateDeduction; }

    public BigDecimal getMidSubsidy() { return midSubsidy; }
    public void setMidSubsidy(BigDecimal midSubsidy) { this.midSubsidy = midSubsidy; }

    public BigDecimal getExtraWage() { return extraWage; }
    public void setExtraWage(BigDecimal extraWage) { this.extraWage = extraWage; }

    public String getPolicyBonusNote() { return policyBonusNote; }
    public void setPolicyBonusNote(String policyBonusNote) { this.policyBonusNote = policyBonusNote; }

    public BigDecimal getActualTotal() { return actualTotal; }
    public void setActualTotal(BigDecimal actualTotal) { this.actualTotal = actualTotal; }
}
