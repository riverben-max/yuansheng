package com.ruoyi.qingbird.mapper;

import java.util.List;
import com.ruoyi.qingbird.domain.BizBranchInfo;

/**
 * 分公司档案 Mapper 接口
 */
public interface BizBranchInfoMapper {

    /** 查询分公司主体列表 */
    List<BizBranchInfo> selectBizBranchInfoList(BizBranchInfo bizBranchInfo);

    /** 获取单个分公司档案 (根据ID) */
    BizBranchInfo selectBizBranchInfoById(Long id);

    /** 获取单个分公司档案 (根据实际的部门 branchId) */
    BizBranchInfo selectBizBranchInfoByBranchId(Long branchId);

    /** 新增 */
    int insertBizBranchInfo(BizBranchInfo bizBranchInfo);

    /** 修改 */
    int updateBizBranchInfo(BizBranchInfo bizBranchInfo);

    /** 删除 */
    int deleteBizBranchInfoById(Long id);
}
