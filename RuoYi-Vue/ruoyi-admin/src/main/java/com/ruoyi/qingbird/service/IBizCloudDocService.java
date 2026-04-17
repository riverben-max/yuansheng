package com.ruoyi.qingbird.service;

import java.util.List;
import com.ruoyi.qingbird.domain.BizCloudDoc;

/**
 * 云文档文章Service接口
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
public interface IBizCloudDocService 
{
    /**
     * 查询云文档文章
     * 
     * @param id 云文档文章主键
     * @return 云文档文章
     */
    public BizCloudDoc selectBizCloudDocById(Long id);

    /**
     * 查询云文档文章列表
     * 
     * @param bizCloudDoc 云文档文章
     * @return 云文档文章集合
     */
    public List<BizCloudDoc> selectBizCloudDocList(BizCloudDoc bizCloudDoc);

    /**
     * 新增云文档文章
     * 
     * @param bizCloudDoc 云文档文章
     * @return 结果
     */
    public int insertBizCloudDoc(BizCloudDoc bizCloudDoc);

    /**
     * 修改云文档文章
     * 
     * @param bizCloudDoc 云文档文章
     * @return 结果
     */
    public int updateBizCloudDoc(BizCloudDoc bizCloudDoc);

    /**
     * 批量删除云文档文章
     * 
     * @param ids 需要删除的云文档文章主键集合
     * @return 结果
     */
    public int deleteBizCloudDocByIds(Long[] ids);

    /**
     * 删除云文档文章信息
     * 
     * @param id 云文档文章主键
     * @return 结果
     */
    public int deleteBizCloudDocById(Long id);
}
