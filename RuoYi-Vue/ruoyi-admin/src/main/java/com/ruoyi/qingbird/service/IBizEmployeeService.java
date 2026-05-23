package com.ruoyi.qingbird.service;

import java.util.List;
import com.ruoyi.qingbird.domain.BizEmployee;

/**
 * 员工花名册 Service 接口
 */
public interface IBizEmployeeService {

    List<BizEmployee> selectEmployeeList(BizEmployee employee);

    BizEmployee selectEmployeeById(Long id);

    BizEmployee selectEmployeeByLoginAccount(String loginAccount);

    int insertEmployee(BizEmployee employee);

    int updateEmployee(BizEmployee employee);

    int deleteEmployeeById(Long id);
}
