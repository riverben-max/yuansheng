package com.ruoyi.qingbird.domain;

import java.math.BigDecimal;
import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 分公司员工花名册
 */
@Data
@EqualsAndHashCode(callSuper = true)
public class BizEmployee extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 主键 */
    private Long id;

    /** 系统用户ID */
    @Excel(name = "用户ID")
    private Long userId;

    /** 登录账号 */
    @Excel(name = "登录账号")
    private String loginAccount;

    /** 创建系统用户时使用的初始密码，不落库 */
    private transient String initialPassword;

    /** 身份证号 */
    @Excel(name = "身份证号")
    private String idCard;

    /** 联系地址 */
    @Excel(name = "联系地址")
    private String address;

    /** 最近登录IP (通过关联 sys_user 获取) */
    private transient String lastLoginIp;

    /** 最近登录时间 (通过关联 sys_user 获取) */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private transient Date lastLoginTime;

    /** 所属分公司编号 */
    @Excel(name = "分公司编号")
    private String branchCode;

    /** 员工姓名 */
    @Excel(name = "姓名")
    private String name;

    /** 头像背景色 */
    private String avatarColor;

    /** 岗位 */
    @Excel(name = "岗位")
    private String position;

    /** 部门 */
    @Excel(name = "部门")
    private String department;

    /** 来源渠道 */
    @Excel(name = "来源")
    private String source;

    /** 生日 */
    @JsonFormat(pattern = "yyyy-MM-dd")
    @Excel(name = "生日")
    private Date birthday;

    /** 联系电话 */
    @Excel(name = "联系电话")
    private String mobile;

    /** 实习开始日期 */
    @JsonFormat(pattern = "yyyy-MM-dd")
    @Excel(name = "实习开始日期")
    private Date internDate;

    /** 正式入职日期 */
    @JsonFormat(pattern = "yyyy-MM-dd")
    @Excel(name = "入职日期")
    private Date hireDate;

    /** 合同状态 0-未签署 1-已签署 */
    @Excel(name = "合同状态", readConverterExp = "0=未签署,1=已签署")
    private Integer contractStatus;

    /** 基本工资 */
    @Excel(name = "基本工资(¥)")
    private BigDecimal salaryBase;

    /** 押金金额 */
    @Excel(name = "押金(¥)")
    private BigDecimal depositAmount;

    /** 在职状态 0-在职 1-离职 */
    @Excel(name = "在职状态", readConverterExp = "0=在职,1=离职")
    private String status;

    /** 离职日期 */
    @JsonFormat(pattern = "yyyy-MM-dd")
    @Excel(name = "离职日期")
    private Date resignDate;
}
