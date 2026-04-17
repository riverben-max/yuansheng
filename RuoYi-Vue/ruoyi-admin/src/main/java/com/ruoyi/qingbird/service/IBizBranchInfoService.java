package com.ruoyi.qingbird.service;

import java.util.List;
import com.ruoyi.qingbird.domain.BizBranchInfo;

/**
 * 分公司主体档案 Service 接口
 */
public interface IBizBranchInfoService {

    /** 查询分公司主体列表 */
    List<BizBranchInfo> selectBizBranchInfoList(BizBranchInfo bizBranchInfo);

    /** 获取单个分公司档案 (根据ID) */
    BizBranchInfo selectBizBranchInfoById(Long id);

    /** 获取本部门对应的档案资料 */
    BizBranchInfo getMyBranchInfo();

    /** 提交申请或新增保存 */
    int submitBranchInfo(BizBranchInfo bizBranchInfo);

    /** 行管人员直接新增入驻主体 */
    int adminAddBranchInfo(BizBranchInfo bizBranchInfo);

    /** 管理员直接修改入驻主体 */
    int adminUpdateBranchInfo(BizBranchInfo bizBranchInfo);

    /** 管理员审核通过 */
    int approveBranchInfo(Long id);

    /** 删除（限管理） */
    int deleteBizBranchInfoById(Long id);
}
