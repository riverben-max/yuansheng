package com.ruoyi.qingbird.service.impl;

import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.qingbird.domain.BizBranchInfo;
import com.ruoyi.qingbird.domain.BizEmployee;
import com.ruoyi.qingbird.mapper.BizBranchInfoMapper;
import com.ruoyi.qingbird.mapper.BizEmployeeMapper;
import com.ruoyi.qingbird.service.IBizEmployeeService;
import com.ruoyi.qingbird.service.support.InitialPasswordPolicy;
import com.ruoyi.system.service.ISysUserService;
import com.ruoyi.common.core.domain.entity.SysUser;

/**
 * 员工花名册 Service 实现
 */
@Service
public class BizEmployeeServiceImpl implements IBizEmployeeService {

    @Autowired
    private BizEmployeeMapper employeeMapper;

    @Autowired
    private BizBranchInfoMapper branchInfoMapper;

    @Autowired
    private ISysUserService sysUserService;

    @Override
    public List<BizEmployee> selectEmployeeList(BizEmployee employee) {
        applyBranchManagerScope(employee);
        return employeeMapper.selectEmployeeList(employee);
    }

    @Override
    public BizEmployee selectEmployeeById(Long id) {
        BizEmployee employee = employeeMapper.selectEmployeeById(id);
        if (isBranchManager() && (employee == null || !getCurrentBranchCode().equals(employee.getBranchCode()))) {
            return null;
        }
        return employee;
    }

    @Override
    public BizEmployee selectEmployeeByLoginAccount(String loginAccount) {
        if (StringUtils.isBlank(loginAccount)) {
            return null;
        }
        BizEmployee employee = employeeMapper.selectEmployeeByLoginAccount(loginAccount.trim());
        if (isBranchManager() && (employee == null || !getCurrentBranchCode().equals(employee.getBranchCode()))) {
            return null;
        }
        return employee;
    }

    @Override
    @Transactional
    public int insertEmployee(BizEmployee employee) {
        applyBranchManagerScope(employee);
        ensureEmployeeBranch(employee);
        normalizeLoginAccount(employee);
        employee.setCreateBy(SecurityUtils.getUsername());
        if (employee.getStatus() == null) {
            employee.setStatus("0"); // 默认在职
        }
        if (employee.getAvatarColor() == null || employee.getAvatarColor().isEmpty()) {
            employee.setAvatarColor("#6C4EF2"); // 默认紫色头像
        }

        // 绑定账号：创建对应的 SysUser
        if (employee.getLoginAccount() != null && !employee.getLoginAccount().isEmpty()) {
            ensureLoginAccountUnique(employee.getLoginAccount(), null);
            if (sysUserService.checkUserNameUnique(new SysUser() {{ setUserName(employee.getLoginAccount()); }})) {
                String initialPassword = StringUtils.trim(employee.getInitialPassword());
                if (StringUtils.isEmpty(initialPassword)) {
                    throw new ServiceException("客服坐席初始密码不能为空");
                }
                if (InitialPasswordPolicy.isWeak(initialPassword)) {
                    throw new ServiceException("客服坐席初始密码不能使用常见弱密码");
                }

                SysUser sysUser = new SysUser();
                sysUser.setUserName(employee.getLoginAccount());
                sysUser.setNickName(employee.getName());
                sysUser.setPhonenumber(employee.getMobile());
                Long deptId = resolveEmployeeDeptId(employee);
                if (deptId != null) {
                    sysUser.setDeptId(deptId);
                }
                sysUser.setPassword(SecurityUtils.encryptPassword(initialPassword));
                sysUser.setCreateBy(SecurityUtils.getUsername());
                sysUser.setStatus("0"); // 正常
                
                sysUserService.insertUser(sysUser);
                employee.setUserId(sysUser.getUserId());
            } else {
                throw new ServiceException("新增客服坐席失败，登录账号已存在");
            }
        }

        return employeeMapper.insertEmployee(employee);
    }

    @Override
    public int updateEmployee(BizEmployee employee) {
        checkBranchManagerEmployeeScope(employee.getId());
        applyBranchManagerScope(employee);
        ensureEmployeeBranch(employee);
        normalizeLoginAccount(employee);
        if (StringUtils.isNotEmpty(employee.getLoginAccount())) {
            ensureLoginAccountUnique(employee.getLoginAccount(), employee.getId());
        }
        employee.setUpdateBy(SecurityUtils.getUsername());
        return employeeMapper.updateEmployee(employee);
    }

    @Override
    public int deleteEmployeeById(Long id) {
        checkBranchManagerEmployeeScope(id);
        return employeeMapper.deleteEmployeeById(id);
    }

    private void applyBranchManagerScope(BizEmployee employee) {
        if (isBranchManager()) {
            employee.setBranchCode(getCurrentBranchCode());
        }
    }

    private void ensureEmployeeBranch(BizEmployee employee) {
        if (employee == null || StringUtils.isEmpty(employee.getBranchCode())) {
            throw new ServiceException("请选择员工所属分公司");
        }
    }

    private Long resolveEmployeeDeptId(BizEmployee employee) {
        if (isBranchManager()) {
            return SecurityUtils.getDeptId();
        }
        if (employee == null || StringUtils.isEmpty(employee.getBranchCode())) {
            return null;
        }
        BizBranchInfo query = new BizBranchInfo();
        query.setWorkplaceName(employee.getBranchCode());
        List<BizBranchInfo> branchInfos = branchInfoMapper.selectBizBranchInfoList(query);
        if (branchInfos != null) {
            for (BizBranchInfo branchInfo : branchInfos) {
                if (employee.getBranchCode().equals(branchInfo.getWorkplaceName())) {
                    return branchInfo.getBranchId();
                }
            }
        }
        try {
            return Long.valueOf(employee.getBranchCode());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private void checkBranchManagerEmployeeScope(Long id) {
        if (!isBranchManager() || id == null) {
            return;
        }
        BizEmployee existing = employeeMapper.selectEmployeeById(id);
        if (existing == null || !getCurrentBranchCode().equals(existing.getBranchCode())) {
            throw new ServiceException("无权操作其他分公司的员工");
        }
    }

    private void ensureLoginAccountUnique(String loginAccount, Long currentId) {
        BizEmployee existing = employeeMapper.selectEmployeeByLoginAccount(loginAccount.trim());
        if (existing != null && (currentId == null || !currentId.equals(existing.getId()))) {
            throw new ServiceException("登录账号已存在");
        }
    }

    private void normalizeLoginAccount(BizEmployee employee) {
        if (employee == null) {
            return;
        }
        String loginAccount = StringUtils.trim(employee.getLoginAccount());
        employee.setLoginAccount(StringUtils.isBlank(loginAccount) ? null : loginAccount);
    }

    private boolean isBranchManager() {
        return !SecurityUtils.isAdmin() && !SecurityUtils.hasRole("admin") && SecurityUtils.hasRole("manager");
    }

    private String getCurrentBranchCode() {
        BizBranchInfo branchInfo = branchInfoMapper.selectBizBranchInfoByBranchId(SecurityUtils.getDeptId());
        if (branchInfo != null && StringUtils.isNotEmpty(branchInfo.getWorkplaceName())) {
            return branchInfo.getWorkplaceName();
        }
        return String.valueOf(SecurityUtils.getDeptId());
    }

}
