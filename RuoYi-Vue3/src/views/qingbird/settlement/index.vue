<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="88px">
      <el-form-item label="分公司名称" prop="branchName">
        <el-input
          v-model="queryParams.branchName"
          placeholder="请输入分公司名称"
          clearable
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="结算周期" prop="settlementPeriod">
        <el-date-picker
          v-model="queryParams.settlementPeriod"
          type="month"
          placeholder="选择周期(如2026-03)"
          value-format="YYYY-MM"
          clearable
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button
          type="primary"
          plain
          icon="Plus"
          @click="handleAdd"
          v-hasPermi="['qingbird:settlement:add']"
        >新增结算</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="success"
          plain
          icon="Edit"
          :disabled="single"
          @click="handleUpdate"
          v-hasPermi="['qingbird:settlement:edit']"
        >修改结算</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="danger"
          plain
          icon="Delete"
          :disabled="multiple"
          @click="handleDelete"
          v-hasPermi="['qingbird:settlement:remove']"
        >删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="settlementList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="结算ID" align="center" prop="id" width="80" />
      <el-table-column label="分公司名称" align="center" prop="branchName" />
      <el-table-column label="结算周期" align="center" prop="settlementPeriod" width="120" />
      <el-table-column label="结算总金额" align="center" prop="settlementAmount">
        <template #default="scope">
          <span style="color: #F56C6C; font-weight: bold;">￥{{ scope.row.settlementAmount }}</span>
        </template>
      </el-table-column>
      <el-table-column label="底薪" align="center" prop="baseSalary" />
      <el-table-column label="佣金" align="center" prop="commission" />
      <el-table-column label="扣罚" align="center" prop="penalty" />
      <el-table-column label="结算时间" align="center" prop="settlementTime" width="120">
        <template #default="scope">
          <span>{{ parseTime(scope.row.settlementTime, '{y}-{m}-{d}') }}</span>
        </template>
      </el-table-column>
      <el-table-column label="录入人员" align="center" prop="createBy" width="100"/>
      <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="150">
        <template #default="scope">
          <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['qingbird:settlement:edit']">修改</el-button>
          <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['qingbird:settlement:remove']">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <pagination
      v-show="total>0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 添加或修改结算信息对话框 -->
    <el-dialog :title="title" v-model="open" width="700px" append-to-body>
      <el-form ref="settleRef" :model="form" :rules="rules" label-width="120px">
        <el-row>
          <el-col :span="24">
            <el-form-item label="分公司" prop="branchId">
              <el-select v-model="form.branchId" placeholder="请选择被结算的分公司" @change="handleBranchChange" style="width: 100%;">
                <el-option
                  v-for="branch in branchOptions"
                  :key="branch.id"
                  :label="branch.branchName"
                  :value="branch.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
             <el-form-item label="结算周期" prop="settlementPeriod">
               <el-date-picker
                v-model="form.settlementPeriod"
                type="month"
                placeholder="请选择结算周期"
                value-format="YYYY-MM"
                style="width: 100%;"
               />
             </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结算时间" prop="settlementTime">
              <el-date-picker clearable
                v-model="form.settlementTime"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="请选择实际结算打款时间"
                style="width: 100%;">
              </el-date-picker>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-divider content-position="left">资金明细 (支持自动计算)</el-divider>

        <el-row>
          <el-col :span="8">
            <el-form-item label="底薪" prop="baseSalary" label-width="80px">
              <el-input-number v-model="form.baseSalary" :precision="2" :step="100" @change="calcTotal" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="佣金" prop="commission" label-width="80px">
              <el-input-number v-model="form.commission" :precision="2" :step="100" @change="calcTotal" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="扣罚" prop="penalty" label-width="80px">
              <el-input-number v-model="form.penalty" :precision="2" :step="10" @change="calcTotal" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结算总金额" prop="settlementAmount">
              <el-input-number v-model="form.settlementAmount" :precision="2" style="width: 100%;" class="amount-input" />
            </el-form-item>
            <div style="font-size: 12px; color: #999; margin-left: 120px; line-height: 1;">( 默认自动计算：底薪 + 佣金 - 扣罚 )</div>
          </el-col>
          <el-col :span="24">
            <el-form-item label="结算备注" prop="remark" style="margin-top: 20px;">
              <el-input v-model="form.remark" type="textarea" placeholder="在此输入有关本周期财务结算的额外备注说明" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="QingbirdSettlement">
import { listSettlement, getSettlement, delSettlement, addSettlement, updateSettlement } from "@/api/qingbird/settlement";
import { listBranchInfo } from "@/api/qingbird/branchInfo";

const { proxy } = getCurrentInstance();

const settlementList = ref([]);
const branchOptions = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    branchName: undefined,
    settlementPeriod: undefined,
  },
  rules: {
    branchId: [
      { required: true, message: "被结算的分公司不能为空", trigger: "change" }
    ],
    settlementPeriod: [
      { required: true, message: "结算周期不能为空", trigger: "change" }
    ],
    settlementAmount: [
      { required: true, message: "结算金额不能为空", trigger: "blur" }
    ],
    settlementTime: [
      { required: true, message: "结算时间不能为空", trigger: "change" }
    ]
  }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询公司列表以供下拉选择 */
function getBranchOptions() {
  listBranchInfo({pageNum: 1, pageSize: 1000}).then(response => {
    branchOptions.value = response.rows;
  });
}

/** 查询结算信息列表 */
function getList() {
  loading.value = true;
  listSettlement(queryParams.value).then(response => {
    settlementList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

// 分公司下拉框切换时自动带入 branchName
function handleBranchChange(vid) {
  const branch = branchOptions.value.find(b => b.id === vid);
  if (branch) {
    form.value.branchName = branch.branchName;
  }
}

// 自动计算逻辑
function calcTotal() {
  const bs = Number(form.value.baseSalary) || 0;
  const com = Number(form.value.commission) || 0;
  const pen = Number(form.value.penalty) || 0;
  form.value.settlementAmount = Number((bs + com - pen).toFixed(2));
}

// 取消按钮
function cancel() {
  open.value = false;
  reset();
}

// 表单重置
function reset() {
  form.value = {
    id: undefined,
    branchId: undefined,
    branchName: undefined,
    settlementPeriod: undefined,
    settlementAmount: 0.00,
    baseSalary: 0.00,
    commission: 0.00,
    penalty: 0.00,
    settlementTime: undefined,
    remark: undefined
  };
  proxy.resetForm("settleRef");
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮操作 */
function resetQuery() {
  proxy.resetForm("queryRef");
  handleQuery();
}

// 多选框选中数据
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

/** 新增按钮操作 */
function handleAdd() {
  reset();
  getBranchOptions();
  open.value = true;
  title.value = "新增结算管理";
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset();
  getBranchOptions();
  const id = row.id || ids.value;
  getSettlement(id).then(response => {
    form.value = response.data;
    open.value = true;
    title.value = "修改结算信息";
  });
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["settleRef"].validate(valid => {
    if (valid) {
      if (form.value.id != undefined) {
        updateSettlement(form.value).then(response => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addSettlement(form.value).then(response => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}

/** 删除按钮操作 */
function handleDelete(row) {
  const settleIds = row.id || ids.value;
  proxy.$modal.confirm('是否确认删除该结算记录？').then(function() {
    return delSettlement(settleIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

getList();
getBranchOptions();
</script>

<style scoped>
/* 强调结算总金额的输入框 */
.amount-input :deep(.el-input__inner) {
  color: #F56C6C;
  font-weight: bold;
  font-size: 16px;
}
</style>
