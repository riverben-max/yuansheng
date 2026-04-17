package com.ruoyi.qingbird.domain;

import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 分公司业务主体档案表 biz_branch_info
 */
public class BizBranchInfo extends BaseEntity {

    private Long id;

    @Excel(name = "关联分公司ID", readConverterExp = "底层sys_dept.dept_id")
    private Long branchId;

    @Excel(name = "职场名")
    private String workplaceName;

    @Excel(name = "公司正式名称")
    private String companyName;

    private String businessLicense;

    @Excel(name = "法人姓名")
    private String legalPersonName;

    private String idCardFront;
    private String idCardBack;

    @Excel(name = "联系电话")
    private String contactPhone;

    @Excel(name = "联系地址")
    private String contactAddress;

    private String settlementAccounts;

    @Excel(name = "审核状态", readConverterExp = "0=未完善,1=待审核,2=已通过")
    private Integer auditStatus;

    // 非数据库映射字段，用于前端组装数据（从 sys_user.login_name 或相关获取该分公司的超级登录账号）
    private String loginAccount;

    // 非数据库映射字段：管理员新增分公司时同步创建主管账号
    private String managerUserName;
    private String managerPassword;
    private Long parentDeptId;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getBranchId() { return branchId; }
    public void setBranchId(Long branchId) { this.branchId = branchId; }

    public String getWorkplaceName() { return workplaceName; }
    public void setWorkplaceName(String workplaceName) { this.workplaceName = workplaceName; }

    public String getCompanyName() { return companyName; }
    public void setCompanyName(String companyName) { this.companyName = companyName; }

    public String getBusinessLicense() { return businessLicense; }
    public void setBusinessLicense(String businessLicense) { this.businessLicense = businessLicense; }

    public String getLegalPersonName() { return legalPersonName; }
    public void setLegalPersonName(String legalPersonName) { this.legalPersonName = legalPersonName; }

    public String getIdCardFront() { return idCardFront; }
    public void setIdCardFront(String idCardFront) { this.idCardFront = idCardFront; }

    public String getIdCardBack() { return idCardBack; }
    public void setIdCardBack(String idCardBack) { this.idCardBack = idCardBack; }

    public String getContactPhone() { return contactPhone; }
    public void setContactPhone(String contactPhone) { this.contactPhone = contactPhone; }

    public String getContactAddress() { return contactAddress; }
    public void setContactAddress(String contactAddress) { this.contactAddress = contactAddress; }

    public String getSettlementAccounts() { return settlementAccounts; }
    public void setSettlementAccounts(String settlementAccounts) { this.settlementAccounts = settlementAccounts; }

    public Integer getAuditStatus() { return auditStatus; }
    public void setAuditStatus(Integer auditStatus) { this.auditStatus = auditStatus; }

    public String getLoginAccount() { return loginAccount; }
    public void setLoginAccount(String loginAccount) { this.loginAccount = loginAccount; }

    public String getManagerUserName() { return managerUserName; }
    public void setManagerUserName(String managerUserName) { this.managerUserName = managerUserName; }

    public String getManagerPassword() { return managerPassword; }
    public void setManagerPassword(String managerPassword) { this.managerPassword = managerPassword; }

    public Long getParentDeptId() { return parentDeptId; }
    public void setParentDeptId(Long parentDeptId) { this.parentDeptId = parentDeptId; }
}
