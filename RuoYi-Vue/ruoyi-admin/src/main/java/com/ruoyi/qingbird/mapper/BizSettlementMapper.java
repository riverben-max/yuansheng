package com.ruoyi.qingbird.mapper;

import java.util.List;
import com.ruoyi.qingbird.domain.BizSettlement;

/**
 * 结算信息Mapper接口
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
public interface BizSettlementMapper 
{
    public BizSettlement selectBizSettlementById(Long id);
    public List<BizSettlement> selectBizSettlementList(BizSettlement bizSettlement);
    public int insertBizSettlement(BizSettlement bizSettlement);
    public int updateBizSettlement(BizSettlement bizSettlement);
    public int deleteBizSettlementById(Long id);
    public int deleteBizSettlementByIds(Long[] ids);
}
