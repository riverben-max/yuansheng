package com.ruoyi.qingbird.service.impl;

import java.util.List;
import com.ruoyi.common.utils.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.qingbird.mapper.BizCloudDocMapper;
import com.ruoyi.qingbird.domain.BizCloudDoc;
import com.ruoyi.qingbird.service.IBizCloudDocService;

/**
 * 云文档文章Service业务层处理
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
@Service
public class BizCloudDocServiceImpl implements IBizCloudDocService 
{
    @Autowired
    private BizCloudDocMapper bizCloudDocMapper;

    /**
     * 查询云文档文章
     * 
     * @param id 云文档文章主键
     * @return 云文档文章
     */
    @Override
    public BizCloudDoc selectBizCloudDocById(Long id)
    {
        return bizCloudDocMapper.selectBizCloudDocById(id);
    }

    /**
     * 查询云文档文章列表
     * 
     * @param bizCloudDoc 云文档文章
     * @return 云文档文章
     */
    @Override
    public List<BizCloudDoc> selectBizCloudDocList(BizCloudDoc bizCloudDoc)
    {
        return bizCloudDocMapper.selectBizCloudDocList(bizCloudDoc);
    }

    /**
     * 新增云文档文章
     * 
     * @param bizCloudDoc 云文档文章
     * @return 结果
     */
    @Override
    public int insertBizCloudDoc(BizCloudDoc bizCloudDoc)
    {
        bizCloudDoc.setCreateTime(DateUtils.getNowDate());
        return bizCloudDocMapper.insertBizCloudDoc(bizCloudDoc);
    }

    /**
     * 修改云文档文章
     * 
     * @param bizCloudDoc 云文档文章
     * @return 结果
     */
    @Override
    public int updateBizCloudDoc(BizCloudDoc bizCloudDoc)
    {
        bizCloudDoc.setUpdateTime(DateUtils.getNowDate());
        return bizCloudDocMapper.updateBizCloudDoc(bizCloudDoc);
    }

    /**
     * 批量删除云文档文章
     * 
     * @param ids 需要删除的云文档文章主键
     * @return 结果
     */
    @Override
    public int deleteBizCloudDocByIds(Long[] ids)
    {
        return bizCloudDocMapper.deleteBizCloudDocByIds(ids);
    }

    /**
     * 删除云文档文章信息
     * 
     * @param id 云文档文章主键
     * @return 结果
     */
    @Override
    public int deleteBizCloudDocById(Long id)
    {
        return bizCloudDocMapper.deleteBizCloudDocById(id);
    }
}
