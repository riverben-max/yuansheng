package com.ruoyi.qingbird.mapper;

import java.util.List;
import com.ruoyi.qingbird.domain.BizEmployee;

/**
 * 员工花名册 Mapper 接口
 */
public interface BizEmployeeMapper {

    /**
     * 查询员工列表（支持姓名/岗位/部门条件筛选）
     */
    List<BizEmployee> selectEmployeeList(BizEmployee employee);

    /**
     * 根据 ID 查询员工
     */
    BizEmployee selectEmployeeById(Long id);

    /**
     * 新增员工
     */
    int insertEmployee(BizEmployee employee);

    /**
     * 修改员工信息
     */
    int updateEmployee(BizEmployee employee);

    /**
     * 删除员工（逻辑删除 → status=1）
     */
    int deleteEmployeeById(Long id);
}
