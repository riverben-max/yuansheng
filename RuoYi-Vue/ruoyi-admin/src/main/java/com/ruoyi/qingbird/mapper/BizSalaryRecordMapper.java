package com.ruoyi.qingbird.mapper;

import java.util.List;
import com.ruoyi.qingbird.domain.BizSalaryRecord;

/**
 * 薪资核算记录 Mapper 接口
 */
public interface BizSalaryRecordMapper {

    /** 查询薪资列表（按账期+分公司） */
    List<BizSalaryRecord> selectSalaryList(BizSalaryRecord record);

    /** 根据 ID 查询 */
    BizSalaryRecord selectSalaryById(Long id);

    /** 新增 */
    int insertSalary(BizSalaryRecord record);

    /** 修改 */
    int updateSalary(BizSalaryRecord record);

    /** 删除 */
    int deleteSalaryById(Long id);

    /** 批量删除 */
    int deleteSalaryByIds(Long[] ids);
}
