package com.ruoyi.qingbird.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.ip.IpUtils;
import com.ruoyi.qingbird.domain.dto.SpiderDataUploadDTO;
import com.ruoyi.qingbird.service.IBizSpiderDataService;

@RestController
@RequestMapping("/spider")
public class SpiderUploadController extends BaseController {

    @Autowired
    private IBizSpiderDataService spiderDataService;

    /**
     * 自动化采集脚本上传数据入口
     */
    @Anonymous // 允许无 token 匿名访问
    @PostMapping("/upload")
    public AjaxResult uploadSpiderData(@RequestBody SpiderDataUploadDTO uploadDTO) {
        if (uploadDTO.getShopId() == null || uploadDTO.getRecordDate() == null) {
            return error("ShopId and RecordDate are required.");
        }
        try {
            String clientIp = IpUtils.getIpAddr();
            int rows = spiderDataService.handleSpiderUpload(uploadDTO, clientIp);
            if (rows > 0) {
                return success("Spider data uploaded/updated successfully");
            } else {
                return error("Upload failed, please check logs.");
            }
        } catch (Exception e) {
            logger.error("Error saving spider data", e);
            return error("Server error while processing spider data: " + e.getMessage());
        }
    }
}
