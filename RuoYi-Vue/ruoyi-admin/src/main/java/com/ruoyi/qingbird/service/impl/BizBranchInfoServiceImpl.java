package com.ruoyi.qingbird.service.impl;

import java.util.List;
import com.ruoyi.common.constant.UserConstants;
import com.ruoyi.common.core.domain.entity.SysDept;
import com.ruoyi.common.core.domain.entity.SysRole;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.DateUtils;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.utils.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.qingbird.mapper.BizBranchInfoMapper;
import com.ruoyi.qingbird.domain.BizBranchInfo;
import com.ruoyi.qingbird.service.IBizBranchInfoService;
import com.ruoyi.qingbird.service.support.InitialPasswordPolicy;
import com.ruoyi.system.mapper.SysRoleMapper;
import com.ruoyi.system.service.ISysDeptService;
import com.ruoyi.system.service.ISysUserService;

@Service
public class BizBranchInfoServiceImpl implements IBizBranchInfoService {

    @Autowired
    private BizBranchInfoMapper bizBranchInfoMapper;

    @Autowired
    private ISysDeptService deptService;

    @Autowired
    private ISysUserService userService;

    @Autowired
    private SysRoleMapper roleMapper;

    @Override
    public List<BizBranchInfo> selectBizBranchInfoList(BizBranchInfo bizBranchInfo) {
        return bizBranchInfoMapper.selectBizBranchInfoList(bizBranchInfo);
    }

    @Override
    public BizBranchInfo selectBizBranchInfoById(Long id) {
        return bizBranchInfoMapper.selectBizBranchInfoById(id);
    }

    @Override
    public BizBranchInfo getMyBranchInfo() {
        Long deptId = SecurityUtils.getDeptId();
        BizBranchInfo info = bizBranchInfoMapper.selectBizBranchInfoByBranchId(deptId);
        if (info == null) {
            info = new BizBranchInfo();
            info.setBranchId(deptId);
            info.setAuditStatus(0); // 0代表未完善
        }
        return info;
    }

    @Override
    public int submitBranchInfo(BizBranchInfo bizBranchInfo) {
        Long deptId = SecurityUtils.getDeptId();
        normalizeJsonFields(bizBranchInfo);
        validateBranchMaterials(bizBranchInfo);
        bizBranchInfo.setBranchId(deptId);
        bizBranchInfo.setAuditStatus(1); // 提交流程后变为 待审核

        BizBranchInfo existing = bizBranchInfoMapper.selectBizBranchInfoByBranchId(deptId);
        if (existing == null) {
            bizBranchInfo.setId(null);
            bizBranchInfo.setCreateTime(DateUtils.getNowDate());
            bizBranchInfo.setCreateBy(SecurityUtils.getUsername());
            return bizBranchInfoMapper.insertBizBranchInfo(bizBranchInfo);
        }

        bizBranchInfo.setId(existing.getId());
        bizBranchInfo.setUpdateTime(DateUtils.getNowDate());
        bizBranchInfo.setUpdateBy(SecurityUtils.getUsername());
        return bizBranchInfoMapper.updateBizBranchInfo(bizBranchInfo);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int adminAddBranchInfo(BizBranchInfo bizBranchInfo) {
        normalizeJsonFields(bizBranchInfo);
        Long deptId = bizBranchInfo.getBranchId();
        if (deptId == null) {
            deptId = createBranchDept(bizBranchInfo);
            bizBranchInfo.setBranchId(deptId);
        }
        createManagerUser(bizBranchInfo, deptId);

        bizBranchInfo.setCreateTime(DateUtils.getNowDate());
        bizBranchInfo.setCreateBy(SecurityUtils.getUsername());
        // 管理员新增时，由于需要分公司补充资料，初始状态应为0(未完善资料)
        bizBranchInfo.setAuditStatus(0); 
        return bizBranchInfoMapper.insertBizBranchInfo(bizBranchInfo);
    }

    @Override
    public int adminUpdateBranchInfo(BizBranchInfo bizBranchInfo) {
        normalizeJsonFields(bizBranchInfo);
        bizBranchInfo.setUpdateTime(DateUtils.getNowDate());
        bizBranchInfo.setUpdateBy(SecurityUtils.getUsername());
        return bizBranchInfoMapper.updateBizBranchInfo(bizBranchInfo);
    }

    @Override
    public int approveBranchInfo(Long id) {
        BizBranchInfo branchInfo = new BizBranchInfo();
        branchInfo.setId(id);
        branchInfo.setAuditStatus(2); // 2:已通过生效
        branchInfo.setUpdateTime(DateUtils.getNowDate());
        branchInfo.setUpdateBy(SecurityUtils.getUsername());
        return bizBranchInfoMapper.updateBizBranchInfo(branchInfo);
    }

    @Override
    public int deleteBizBranchInfoById(Long id) {
        return bizBranchInfoMapper.deleteBizBranchInfoById(id);
    }

    private void normalizeJsonFields(BizBranchInfo bizBranchInfo) {
        if (StringUtils.isEmpty(bizBranchInfo.getSettlementAccounts())) {
            bizBranchInfo.setSettlementAccounts("[]");
        }
    }

    private void validateBranchMaterials(BizBranchInfo bizBranchInfo) {
        if (StringUtils.isEmpty(bizBranchInfo.getCompanyName())) {
            throw new ServiceException("提交审核失败，分公司名称不能为空");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getLegalPersonName())) {
            throw new ServiceException("提交审核失败，负责人姓名不能为空");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getContactPhone())) {
            throw new ServiceException("提交审核失败，联系电话不能为空");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getContactAddress())) {
            throw new ServiceException("提交审核失败，联系地址不能为空");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getBusinessLicense())) {
            throw new ServiceException("提交审核失败，请提交营业执照");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getIdCardFront())) {
            throw new ServiceException("提交审核失败，请提交身份证正面");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getIdCardBack())) {
            throw new ServiceException("提交审核失败，请提交身份证反面");
        }
        if ("[]".equals(bizBranchInfo.getSettlementAccounts())) {
            throw new ServiceException("提交审核失败，请填写公司账号和支付宝账号");
        }
    }

    private Long createBranchDept(BizBranchInfo bizBranchInfo) {
        String deptName = StringUtils.isNotEmpty(bizBranchInfo.getWorkplaceName())
                ? bizBranchInfo.getWorkplaceName()
                : bizBranchInfo.getCompanyName();
        if (StringUtils.isEmpty(deptName)) {
            throw new ServiceException("分公司名称不能为空");
        }

        SysDept dept = new SysDept();
        dept.setParentId(bizBranchInfo.getParentDeptId() == null ? 100L : bizBranchInfo.getParentDeptId());
        dept.setDeptName(deptName);
        dept.setOrderNum(0);
        dept.setLeader(bizBranchInfo.getLegalPersonName());
        dept.setPhone(bizBranchInfo.getContactPhone());
        dept.setStatus(UserConstants.DEPT_NORMAL);
        dept.setCreateBy(SecurityUtils.getUsername());

        if (!deptService.checkDeptNameUnique(dept)) {
            throw new ServiceException("新增分公司失败，分公司部门名称已存在");
        }
        deptService.insertDept(dept);
        return dept.getDeptId();
    }

    private void createManagerUser(BizBranchInfo bizBranchInfo, Long deptId) {
        if (StringUtils.isEmpty(bizBranchInfo.getManagerUserName())) {
            throw new ServiceException("主管登录账号不能为空");
        }
        if (StringUtils.isEmpty(bizBranchInfo.getManagerPassword())) {
            throw new ServiceException("主管初始密码不能为空");
        }
        if (InitialPasswordPolicy.isWeak(bizBranchInfo.getManagerPassword())) {
            throw new ServiceException("主管初始密码不能使用常见弱密码");
        }

        SysRole managerRole = roleMapper.checkRoleKeyUnique("manager");
        if (managerRole == null) {
            throw new ServiceException("新增分公司失败，请先创建 role_key 为 manager 的分公司主管角色");
        }

        SysUser user = new SysUser();
        user.setDeptId(deptId);
        user.setUserName(bizBranchInfo.getManagerUserName());
        user.setNickName(StringUtils.isNotEmpty(bizBranchInfo.getLegalPersonName())
                ? bizBranchInfo.getLegalPersonName()
                : bizBranchInfo.getManagerUserName());
        user.setPhonenumber(bizBranchInfo.getContactPhone());
        user.setSex("2");
        user.setStatus(UserConstants.NORMAL);
        user.setPassword(SecurityUtils.encryptPassword(bizBranchInfo.getManagerPassword()));
        user.setRoleIds(new Long[] { managerRole.getRoleId() });
        user.setCreateBy(SecurityUtils.getUsername());
        user.setRemark("分公司主管账号，由分公司管理自动创建");

        if (!userService.checkUserNameUnique(user)) {
            throw new ServiceException("新增分公司失败，主管登录账号已存在");
        }
        if (StringUtils.isNotEmpty(user.getPhonenumber()) && !userService.checkPhoneUnique(user)) {
            throw new ServiceException("新增分公司失败，主管手机号已存在");
        }
        userService.insertUser(user);
    }

}
