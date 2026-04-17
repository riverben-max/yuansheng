package com.ruoyi.qingbird.controller;

import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.qingbird.domain.BizBranchInfo;
import com.ruoyi.qingbird.service.IBizBranchInfoService;

@RestController
@RequestMapping("/qingbird/branch-info")
public class BizBranchInfoController extends BaseController {

    @Autowired
    private IBizBranchInfoService branchInfoService;

    /** 
     * 查询分公司列表 (针对 Admin) 
     */
    @PreAuthorize("@ss.hasRole('admin')")
    @GetMapping("/list")
    public TableDataInfo list(BizBranchInfo bizBranchInfo) {
        startPage();
        List<BizBranchInfo> list = branchInfoService.selectBizBranchInfoList(bizBranchInfo);
        return getDataTable(list);
    }

    /** 
     * 获取当前登录人的本部门分公司档案 (针对 Manager) 
     */
    @GetMapping("/my")
    public AjaxResult getMyInfo() {
        return success(branchInfoService.getMyBranchInfo());
    }

    /** 
     * 分公司提交资料变更申请 
     */
    @Log(title = "分公司档案申请", businessType = BusinessType.UPDATE)
    @PostMapping("/submit")
    public AjaxResult submit(@RequestBody BizBranchInfo bizBranchInfo) {
        return toAjax(branchInfoService.submitBranchInfo(bizBranchInfo));
    }

    /** 
     * 总管理：审核通过 
     */
    @PreAuthorize("@ss.hasRole('admin')")
    @Log(title = "分公司档案审批", businessType = BusinessType.UPDATE)
    @PutMapping("/approve/{id}")
    public AjaxResult approve(@PathVariable Long id) {
        return toAjax(branchInfoService.approveBranchInfo(id));
    }

    /** 
     * 获取详细信息 (Admin用) 
     */
    @PreAuthorize("@ss.hasRole('admin')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable Long id) {
        return success(branchInfoService.selectBizBranchInfoById(id));
    }

    /** 
     * 总管理：直接修改档案 (跳过审批) 
     */
    @PreAuthorize("@ss.hasRole('admin')")
    @Log(title = "分公司档案管理", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@RequestBody BizBranchInfo bizBranchInfo) {
        return toAjax(branchInfoService.adminUpdateBranchInfo(bizBranchInfo));
    }

    /** 
     * 总管理：直接新增档案入驻 
     */
    @PreAuthorize("@ss.hasRole('admin')")
    @Log(title = "分公司档案管理", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@RequestBody BizBranchInfo bizBranchInfo) {
        return toAjax(branchInfoService.adminAddBranchInfo(bizBranchInfo));
    }

    /** 
     * 总管理：删除 
     */
    @PreAuthorize("@ss.hasRole('admin')")
    @Log(title = "分公司档案管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{id}")
    public AjaxResult remove(@PathVariable Long id) {
        return toAjax(branchInfoService.deleteBizBranchInfoById(id));
    }
}
