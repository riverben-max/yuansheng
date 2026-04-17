package com.ruoyi.qingbird.controller;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.core.domain.entity.SysRole;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.qingbird.domain.BizSalaryRecord;
import com.ruoyi.qingbird.service.IBizSalaryRecordService;

/**
 * 薪资管理 Controller
 */
@RestController
@RequestMapping("/qingbird/salary")
public class SalaryController extends BaseController {

    @Autowired
    private IBizSalaryRecordService salaryService;

    /** 查询薪资列表与大屏宏观KPI */
    @GetMapping("/list")
    public AjaxResult list(BizSalaryRecord record) {
        // 核心权限拦截逻辑
        SysUser user = SecurityUtils.getLoginUser().getUser();
        boolean isAdmin = SecurityUtils.isAdmin(user.getUserId());
        boolean isFinance = user.getRoles().stream().anyMatch(r -> "finance".equals(r.getRoleKey()));
        boolean isManager = user.getRoles().stream().anyMatch(r -> "manager".equals(r.getRoleKey()));

        // 如果既不是超管，也不是财务，则进行数据降级（隔离）
        if (!isAdmin && !isFinance) {
            if (isManager) {
                // 主管等级：强行限定查询条件为其所在部门（分公司），他只能搜到本部门人的工资
                // 现实中如果是根据部门名称过滤可以设为 user.getDept().getDeptName()
                // 我们假设前端的 branchCode 就是绑定的部门 ID 或代号
                record.setBranchCode(String.valueOf(user.getDeptId()));
            } else {
                // 最底层的普通员工：强制限定只能搜出他自己的名字
                record.setName(user.getUserName());
            }
        }

        startPage();
        List<BizSalaryRecord> list = salaryService.selectSalaryList(record);
        TableDataInfo dataTable = getDataTable(list);

        // 组装前台需要的特殊数据格式 (融合 KPI overview)
        BigDecimal estimatedTotal = BigDecimal.ZERO;
        BigDecimal promotionBonus = BigDecimal.ZERO;
        BigDecimal qualityDeduction = BigDecimal.ZERO;

        // 这里仅计算当前页的数据作为演示，如果需要全量KPI应单独编写SQL
        for (BizSalaryRecord r : list) {
            if (r.getActualTotal() != null) estimatedTotal = estimatedTotal.add(r.getActualTotal());
            if (r.getPromotionBonus() != null) promotionBonus = promotionBonus.add(r.getPromotionBonus());
            if (r.getLateDeduction() != null) qualityDeduction = qualityDeduction.add(r.getLateDeduction().abs());
        }

        Map<String, Object> overview = new HashMap<>();
        overview.put("estimatedTotal", estimatedTotal);
        overview.put("promotionBonus", promotionBonus);
        overview.put("qualityDeduction", qualityDeduction);
        overview.put("tierRate", 698); // 演示档位倍率
        overview.put("tierMonths", 1);

        Map<String, Object> innerData = new HashMap<>();
        innerData.put("overview", overview);

        AjaxResult ajax = AjaxResult.success();
        ajax.put("rows", dataTable.getRows());
        ajax.put("total", dataTable.getTotal());
        ajax.put("data", innerData);
        
        return ajax;
    }

    /** 新增薪资 */
    @PreAuthorize("@ss.hasAnyRoles('admin,finance')")
    @Log(title = "资金账本管理", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@RequestBody BizSalaryRecord record) {
        return toAjax(salaryService.insertSalary(record));
    }

    /** 修改薪资 */
    @PreAuthorize("@ss.hasAnyRoles('admin,finance')")
    @Log(title = "资金账本管理", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@RequestBody BizSalaryRecord record) {
        return toAjax(salaryService.updateSalary(record));
    }

    /** 删除薪资 */
    @PreAuthorize("@ss.hasAnyRoles('admin,finance')")
    @Log(title = "资金账本管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{id}")
    public AjaxResult remove(@PathVariable Long id) {
        return toAjax(salaryService.deleteSalaryById(id));
    }
}
