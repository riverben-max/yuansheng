package com.ruoyi.qingbird.controller;

import java.util.Collections;
import java.util.List;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.qingbird.domain.BizEmployee;
import com.ruoyi.system.domain.SysLogininfor;
import com.ruoyi.system.service.ISysLogininforService;
import com.ruoyi.qingbird.service.IBizEmployeeService;

/**
 * 分公司员工花名册 Controller
 */
@RestController
@RequestMapping("/qingbird/employee")
public class BizEmployeeController extends BaseController {

    @Autowired
    private IBizEmployeeService employeeService;

    @Autowired
    private ISysLogininforService logininforService;

    /** 查询员工列表 */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:list')")
    @GetMapping("/list")
    public TableDataInfo list(BizEmployee employee) {
        startPage();
        List<BizEmployee> list = employeeService.selectEmployeeList(employee);
        return getDataTable(list);
    }

    /** 查询坐席登录打卡日志流水 
     * 故意不用 monitor 权限，方便分公司管理员直接查询
     */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:list')")
    @GetMapping("/loginLogs")
    public TableDataInfo loginLogs(SysLogininfor logininfor) {
        String userName = StringUtils.trim(logininfor.getUserName());
        if (isBranchManager()) {
            if (StringUtils.isBlank(userName) || !isEmployeeInCurrentBranch(userName)) {
                return getDataTable(Collections.emptyList());
            }
        }
        logininfor.setUserName(userName);
        startPage();
        List<SysLogininfor> list = StringUtils.isNotBlank(userName)
                ? logininforService.selectLogininforListByExactUserName(logininfor)
                : logininforService.selectLogininforList(logininfor);
        return getDataTable(list);
    }

    /** 导出 CSV/Excel */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:export')")
    @Log(title = "员工花名册", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, BizEmployee employee) {
        List<BizEmployee> list = employeeService.selectEmployeeList(employee);
        ExcelUtil<BizEmployee> util = new ExcelUtil<>(BizEmployee.class);
        util.exportExcel(response, list, "员工花名册");
    }

    /** 查询单个员工 */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:query')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable Long id) {
        return success(employeeService.selectEmployeeById(id));
    }

    /** 新增员工 */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:add')")
    @Log(title = "员工花名册", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@RequestBody BizEmployee employee) {
        return toAjax(employeeService.insertEmployee(employee));
    }

    /** 修改员工信息 */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:edit')")
    @Log(title = "员工花名册", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@RequestBody BizEmployee employee) {
        return toAjax(employeeService.updateEmployee(employee));
    }

    /** 删除员工 */
    @PreAuthorize("@ss.hasPermi('qingbird:employee:remove')")
    @Log(title = "员工花名册", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        for (Long id : ids) {
            employeeService.deleteEmployeeById(id);
        }
        return success();
    }

    private boolean isBranchManager() {
        return !SecurityUtils.isAdmin() && !SecurityUtils.hasRole("admin") && SecurityUtils.hasRole("manager");
    }

    private boolean isEmployeeInCurrentBranch(String loginAccount) {
        BizEmployee employee = employeeService.selectEmployeeByLoginAccount(loginAccount);
        return employee != null && loginAccount.equals(employee.getLoginAccount());
    }
}
