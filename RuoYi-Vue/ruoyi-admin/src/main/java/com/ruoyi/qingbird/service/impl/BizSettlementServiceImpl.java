package com.ruoyi.qingbird.service.impl;

import java.util.List;
import com.ruoyi.common.utils.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.qingbird.mapper.BizSettlementMapper;
import com.ruoyi.qingbird.domain.BizSettlement;
import com.ruoyi.qingbird.service.IBizSettlementService;

/**
 * 结算信息Service业务层处理
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
@Service
public class BizSettlementServiceImpl implements IBizSettlementService 
{
    @Autowired
    private BizSettlementMapper bizSettlementMapper;

    @Override
    public BizSettlement selectBizSettlementById(Long id)
    {
        return bizSettlementMapper.selectBizSettlementById(id);
    }

    @Override
    public List<BizSettlement> selectBizSettlementList(BizSettlement bizSettlement)
    {
        return bizSettlementMapper.selectBizSettlementList(bizSettlement);
    }

    @Override
    public int insertBizSettlement(BizSettlement bizSettlement)
    {
        bizSettlement.setCreateTime(DateUtils.getNowDate());
        return bizSettlementMapper.insertBizSettlement(bizSettlement);
    }

    @Override
    public int updateBizSettlement(BizSettlement bizSettlement)
    {
        bizSettlement.setUpdateTime(DateUtils.getNowDate());
        return bizSettlementMapper.updateBizSettlement(bizSettlement);
    }

    @Override
    public int deleteBizSettlementByIds(Long[] ids)
    {
        return bizSettlementMapper.deleteBizSettlementByIds(ids);
    }

    @Override
    public int deleteBizSettlementById(Long id)
    {
        return bizSettlementMapper.deleteBizSettlementById(id);
    }
}
