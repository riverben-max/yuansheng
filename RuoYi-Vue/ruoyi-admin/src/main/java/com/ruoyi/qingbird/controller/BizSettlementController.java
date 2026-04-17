package com.ruoyi.qingbird.controller;

import java.util.List;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.qingbird.domain.BizSettlement;
import com.ruoyi.qingbird.service.IBizSettlementService;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.common.core.page.TableDataInfo;

/**
 * 结算信息Controller
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
@RestController
@RequestMapping("/qingbird/settlement")
public class BizSettlementController extends BaseController
{
    @Autowired
    private IBizSettlementService bizSettlementService;

    @PreAuthorize("@ss.hasPermi('qingbird:settlement:list')")
    @GetMapping("/list")
    public TableDataInfo list(BizSettlement bizSettlement)
    {
        startPage();
        List<BizSettlement> list = bizSettlementService.selectBizSettlementList(bizSettlement);
        return getDataTable(list);
    }

    @PreAuthorize("@ss.hasPermi('qingbird:settlement:export')")
    @Log(title = "结算信息", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, BizSettlement bizSettlement)
    {
        List<BizSettlement> list = bizSettlementService.selectBizSettlementList(bizSettlement);
        ExcelUtil<BizSettlement> util = new ExcelUtil<BizSettlement>(BizSettlement.class);
        util.exportExcel(response, list, "结算信息数据");
    }

    @PreAuthorize("@ss.hasPermi('qingbird:settlement:query')")
    @GetMapping(value = "/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id)
    {
        return AjaxResult.success(bizSettlementService.selectBizSettlementById(id));
    }

    @PreAuthorize("@ss.hasPermi('qingbird:settlement:add')")
    @Log(title = "结算信息", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@RequestBody BizSettlement bizSettlement)
    {
        bizSettlement.setCreateBy(getUsername());
        return toAjax(bizSettlementService.insertBizSettlement(bizSettlement));
    }

    @PreAuthorize("@ss.hasPermi('qingbird:settlement:edit')")
    @Log(title = "结算信息", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@RequestBody BizSettlement bizSettlement)
    {
        bizSettlement.setUpdateBy(getUsername());
        return toAjax(bizSettlementService.updateBizSettlement(bizSettlement));
    }

    @PreAuthorize("@ss.hasPermi('qingbird:settlement:remove')")
    @Log(title = "结算信息", businessType = BusinessType.DELETE)
	@DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids)
    {
        return toAjax(bizSettlementService.deleteBizSettlementByIds(ids));
    }
}
