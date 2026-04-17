package com.ruoyi.qingbird.service.impl;

import java.util.List;
import com.ruoyi.common.utils.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.qingbird.mapper.BizSalaryRecordMapper;
import com.ruoyi.qingbird.domain.BizSalaryRecord;
import com.ruoyi.qingbird.service.IBizSalaryRecordService;

/**
 * 薪资核算记录Service业务层处理
 */
@Service
public class BizSalaryRecordServiceImpl implements IBizSalaryRecordService {
    @Autowired
    private BizSalaryRecordMapper salaryRecordMapper;

    @Override
    public List<BizSalaryRecord> selectSalaryList(BizSalaryRecord record) {
        return salaryRecordMapper.selectSalaryList(record);
    }

    @Override
    public BizSalaryRecord selectSalaryById(Long id) {
        return salaryRecordMapper.selectSalaryById(id);
    }

    @Override
    public int insertSalary(BizSalaryRecord record) {
        record.setCreateTime(DateUtils.getNowDate());
        // 若没有传递分公司编号，可以默认给一个演示的分公司
        if (record.getBranchCode() == null || record.getBranchCode().isEmpty()) {
            record.setBranchCode("B-1773208272961");
        }
        return salaryRecordMapper.insertSalary(record);
    }

    @Override
    public int updateSalary(BizSalaryRecord record) {
        record.setUpdateTime(DateUtils.getNowDate());
        return salaryRecordMapper.updateSalary(record);
    }

    @Override
    public int deleteSalaryById(Long id) {
        return salaryRecordMapper.deleteSalaryById(id);
    }

    @Override
    public int deleteSalaryByIds(Long[] ids) {
        return salaryRecordMapper.deleteSalaryByIds(ids);
    }
}
