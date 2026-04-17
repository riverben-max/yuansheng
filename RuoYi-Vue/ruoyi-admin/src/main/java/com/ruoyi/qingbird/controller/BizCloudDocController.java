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
import com.ruoyi.qingbird.domain.BizCloudDoc;
import com.ruoyi.qingbird.service.IBizCloudDocService;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.common.core.page.TableDataInfo;

/**
 * 云文档文章Controller
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
@RestController
@RequestMapping("/qingbird/doc")
public class BizCloudDocController extends BaseController
{
    @Autowired
    private IBizCloudDocService bizCloudDocService;

    /**
     * 查询云文档文章列表
     */
    @PreAuthorize("@ss.hasPermi('qingbird:doc:list')")
    @GetMapping("/list")
    public TableDataInfo list(BizCloudDoc bizCloudDoc)
    {
        startPage();
        List<BizCloudDoc> list = bizCloudDocService.selectBizCloudDocList(bizCloudDoc);
        return getDataTable(list);
    }

    /**
     * 导出云文档文章列表
     */
    @PreAuthorize("@ss.hasPermi('qingbird:doc:export')")
    @Log(title = "云文档文章", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, BizCloudDoc bizCloudDoc)
    {
        List<BizCloudDoc> list = bizCloudDocService.selectBizCloudDocList(bizCloudDoc);
        ExcelUtil<BizCloudDoc> util = new ExcelUtil<BizCloudDoc>(BizCloudDoc.class);
        util.exportExcel(response, list, "云文档文章数据");
    }

    /**
     * 获取云文档文章详细信息
     */
    @PreAuthorize("@ss.hasPermi('qingbird:doc:query')")
    @GetMapping(value = "/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id)
    {
        return AjaxResult.success(bizCloudDocService.selectBizCloudDocById(id));
    }

    /**
     * 新增云文档文章
     */
    @PreAuthorize("@ss.hasPermi('qingbird:doc:add')")
    @Log(title = "云文档文章", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@RequestBody BizCloudDoc bizCloudDoc)
    {
        bizCloudDoc.setCreateBy(getUsername());
        return toAjax(bizCloudDocService.insertBizCloudDoc(bizCloudDoc));
    }

    /**
     * 修改云文档文章
     */
    @PreAuthorize("@ss.hasPermi('qingbird:doc:edit')")
    @Log(title = "云文档文章", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@RequestBody BizCloudDoc bizCloudDoc)
    {
        bizCloudDoc.setUpdateBy(getUsername());
        return toAjax(bizCloudDocService.updateBizCloudDoc(bizCloudDoc));
    }

    /**
     * 删除云文档文章
     */
    @PreAuthorize("@ss.hasPermi('qingbird:doc:remove')")
    @Log(title = "云文档文章", businessType = BusinessType.DELETE)
	@DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids)
    {
        return toAjax(bizCloudDocService.deleteBizCloudDocByIds(ids));
    }
}
