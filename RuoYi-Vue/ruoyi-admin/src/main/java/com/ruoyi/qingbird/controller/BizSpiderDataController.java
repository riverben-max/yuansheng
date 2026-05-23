package com.ruoyi.qingbird.controller;

import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.qingbird.domain.BizSpiderData;
import com.ruoyi.qingbird.service.IBizSpiderDataService;

/**
 * 质检明细/爬虫数据 Controller
 */
@RestController
@RequestMapping("/qingbird/spider-data")
public class BizSpiderDataController extends BaseController {
    
    @Autowired
    private IBizSpiderDataService bizSpiderDataService;

    /**
     * 查询爬虫/质检数据列表
     */
    @PreAuthorize("@ss.hasPermi('qingbird:spider:list')")
    @GetMapping("/list")
    public TableDataInfo list(BizSpiderData bizSpiderData) {
        startPage();
        List<BizSpiderData> list = bizSpiderDataService.selectSpiderDataList(bizSpiderData);
        return getDataTable(list);
    }
}
