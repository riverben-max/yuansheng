package com.ruoyi.qingbird.service;

import java.util.List;
import com.ruoyi.qingbird.domain.BizSettlement;

/**
 * 结算信息Service接口
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
public interface IBizSettlementService 
{
    public BizSettlement selectBizSettlementById(Long id);
    public List<BizSettlement> selectBizSettlementList(BizSettlement bizSettlement);
    public int insertBizSettlement(BizSettlement bizSettlement);
    public int updateBizSettlement(BizSettlement bizSettlement);
    public int deleteBizSettlementByIds(Long[] ids);
    public int deleteBizSettlementById(Long id);
}
