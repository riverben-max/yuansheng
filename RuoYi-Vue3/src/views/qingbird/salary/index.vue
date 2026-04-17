<template>
  <div class="qb-page">
    <!-- 页面标题 -->
    <div class="qb-page-header salary-header">
      <div class="salary-title-group">
        <div class="salary-title-icon">
          <el-icon><Money /></el-icon>
        </div>
        <div>
          <h1 class="qb-page-title">我的薪资进度表</h1>
          <p class="qb-page-subtitle">
            <el-tag type="info" size="small" style="margin-right:6px;">多分公司模板限属</el-tag>
            账期：{{ selectedMonth }}
          </p>
        </div>
      </div>
      <div class="salary-header-actions">
        <el-date-picker
          v-model="selectedMonth"
          type="month"
          format="YYYY-MM"
          value-format="YYYY-MM"
          size="default"
          style="width: 150px;"
          :disabled-date="disableFutureMonth"
          @change="fetchData"
        />
        <el-button :icon="View" @click="dialogDetail = true" style="border-radius:8px;">
          查看详细
        </el-button>
        <el-button class="qb-btn-primary" :icon="Plus" @click="openAddDialog" v-hasRole="['admin', 'finance']">
          录入薪资
        </el-button>
        <el-button :icon="Refresh" :loading="loading" @click="fetchData" circle style="border-radius:8px;" />
      </div>
    </div>

    <!-- 4 个 KPI 卡片 -->
    <el-row :gutter="14" v-loading="loading">
      <!-- 月度预估总量 -->
      <el-col :span="6">
        <div class="salary-kpi-card dark-card">
          <div class="kpi-card-bg-icon">💰</div>
          <div class="kpi-card-label">月月预估金额全量</div>
          <div class="kpi-card-value">
            <span class="kpi-currency">¥</span>{{ fmtNum(salaryData.estimatedTotal) }}
          </div>
          <div class="kpi-card-sub">
            <el-icon style="color:#FAAD14;"><WarningFilled /></el-icon>
            动态图模板计算中
          </div>
        </div>
      </el-col>

      <!-- 强度档位 -->
      <el-col :span="6">
        <div class="salary-kpi-card tier-card">
          <div class="kpi-card-label-sm">强度档位倍率素数</div>
          <div class="kpi-tier-value">{{ fmtNum(salaryData.tierRate) }}</div>
          <div class="kpi-tier-unit">人/天</div>
          <div class="kpi-tier-sub">ACROSS {{ salaryData.tierMonths ?? 1 }} MONTHS</div>
        </div>
      </el-col>

      <!-- 晋级奖金 -->
      <el-col :span="6">
        <div class="salary-kpi-card bonus-card">
          <div class="kpi-card-label-sm">营商晋级奖金</div>
          <div class="kpi-bonus-value">
            +¥{{ fmtNum(salaryData.promotionBonus) }}
          </div>
          <el-tag type="success" size="small" style="margin-top:10px;">PERFORMANCE TIERS</el-tag>
        </div>
      </el-col>

      <!-- 品质积分扣款 -->
      <el-col :span="6">
        <div class="salary-kpi-card deduct-card">
          <div class="kpi-card-label-sm">品质积分扣款</div>
          <div class="kpi-deduct-value">
            -¥{{ fmtNum(Math.abs(salaryData.qualityDeduction ?? 0)) }}
          </div>
          <el-tag type="danger" size="small" style="margin-top:10px;">QUALITY AUDIT REDUCTIONS</el-tag>
        </div>
      </el-col>
    </el-row>

    <!-- 薪资核算大表 -->
    <div class="qb-card salary-table-card" style="margin-top:16px;">
      <div class="salary-table-header">
        <div>
          <div class="section-title">
            <el-icon style="color:var(--qb-primary);"><List /></el-icon>
            薪资核算大表 · <span class="period-tag">{{ selectedMonth }} 账期</span>
          </div>
        </div>
        <el-input
          v-model="searchName"
          placeholder="搜索姓名..."
          :prefix-icon="Search"
          clearable
          size="small"
          style="width: 200px;"
        />
      </div>

      <div class="table-scroll-wrap">
        <el-table
          :data="filteredTableData"
          size="small"
          border
          v-loading="loading"
          style="margin-top:14px;"
          :header-cell-style="{ background: '#F8F9FA', fontWeight: '600', fontSize: '12px' }"
          empty-text="暂无核算数据"
          show-summary
          :summary-method="getSummary"
        >
          <!-- 成员/岗位 -->
          <el-table-column label="成员/岗位" width="120" fixed="left">
            <template #default="{ row }">
              <div class="member-cell">
                <div class="member-avatar" :style="{ background: row.avatarColor }">
                  {{ row.name?.[0] }}
                </div>
                <div>
                  <div class="member-name">{{ row.name }}</div>
                  <div class="member-pos">{{ row.position }}</div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="baseWage" label="底薪基数" width="90" align="right">
            <template #default="{ row }">¥{{ fmtNum(row.baseWage) }}</template>
          </el-table-column>

          <el-table-column prop="attendanceDays" label="出勤天数" width="80" align="center">
            <template #default="{ row }">
              <span class="days-val">{{ row.attendanceDays }}</span>
            </template>
          </el-table-column>

          <el-table-column prop="performancePay" label="当月底薪绩效" width="110" align="right">
            <template #default="{ row }">
              <span style="color:var(--qb-primary); font-weight:700;">¥{{ fmtNum(row.performancePay) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="在岗期间(店铺号)" width="140" align="center">
            <template #default="{ row }">
              <div class="shop-cell">
                <div class="shop-price">¥{{ row.shopDailyRate }}</div>
                <el-tag type="success" size="small" style="margin-top:2px;">{{ row.tierRate }} 人/天</el-tag>
                <el-tag type="warning" size="small" style="margin-top:2px; margin-left:2px;" v-if="row.promotionBonus > 0">
                  +¥{{ row.promotionBonus }}
                </el-tag>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="standbyDeduction" label="当日待岗" width="80" align="right">
            <template #default="{ row }">
              <span :class="row.standbyDeduction < 0 ? 'val-danger' : 'val-normal'">
                {{ row.standbyDeduction ?? 0 }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="leaveDeduction" label="请假扣款" width="80" align="right">
            <template #default="{ row }">
              <span :class="row.leaveDeduction < 0 ? 'val-danger' : 'val-normal'">
                {{ row.leaveDeduction ?? 0 }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="loanDeduction" label="借款金额" width="80" align="right">
            <template #default="{ row }">{{ row.loanDeduction ?? 0 }}</template>
          </el-table-column>

          <el-table-column prop="unitSubsidy" label="单件补贴" width="80" align="right">
            <template #default="{ row }">{{ row.unitSubsidy ?? 0 }}</template>
          </el-table-column>

          <el-table-column prop="specialSubsidy" label="专项补贴" width="80" align="right">
            <template #default="{ row }">{{ row.specialSubsidy ?? 0 }}</template>
          </el-table-column>

          <el-table-column prop="lateDeduction" label="迟到扣款" width="80" align="right">
            <template #default="{ row }">
              <span :class="(row.lateDeduction ?? 0) < 0 ? 'val-danger' : 'val-normal'">
                {{ row.lateDeduction ?? 0 }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="midSubsidy" label="15日补贴" width="80" align="right">
            <template #default="{ row }">{{ row.midSubsidy ?? 0 }}</template>
          </el-table-column>

          <el-table-column prop="extraWage" label="额外工资" width="80" align="right">
            <template #default="{ row }">{{ row.extraWage ?? 0 }}</template>
          </el-table-column>

          <el-table-column prop="policyBonus" label="政策奖金" width="80" align="right">
            <template #default="{ row }">
              <span style="color:var(--qb-text-muted); font-size:11px;">
                {{ row.policyBonusNote || '入入薪资忠...' }}
              </span>
            </template>
          </el-table-column>

          <!-- 实发合计 -->
          <el-table-column label="实发合计" width="100" align="right" fixed="right">
            <template #default="{ row }">
              <div class="total-pay">¥{{ fmtNum(row.actualTotal) }}</div>
            </template>
          </el-table-column>
          <!-- 操作列 -->
          <el-table-column label="操作" width="100" align="center" fixed="right" v-hasRole="['admin', 'finance']">
            <template #default="{ row }">
              <el-button link size="small" type="primary" :icon="EditPen" @click="openEditDialog(row)" />
              <el-button link size="small" type="danger" :icon="Delete" @click="handleDelete(row)" />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 底部说明 -->
    <div class="qb-card policy-note" style="margin-top:14px;">
      <div class="policy-note-header">
        <el-icon style="color:var(--qb-primary);"><InfoFilled /></el-icon>
        多分公司模板核算说明
      </div>
      <p class="policy-note-text">
        系统当前运行于 <strong>多分公司模板并行模式*</strong>，每个分公司拥有独立的薪资奖惩模板。在薪资条中，系统会自动显示该员工应用的是哪个领域的模板。如果某分公司独立配置，则默认认继承集团通用规则，确保薪资核算无纰漏。
      </p>
    </div>

    <!-- 薪资详情弹窗 -->
    <el-dialog v-model="dialogDetail" title="薪资核算详情" width="640px">
      <div v-for="row in tableData" :key="row.id" class="detail-item">
        <div class="detail-member">
          <div class="member-avatar" :style="{ background: row.avatarColor }">{{ row.name?.[0] }}</div>
          <div>
            <div class="member-name">{{ row.name }} · {{ row.position }}</div>
            <div class="member-pos">{{ selectedMonth }} 账期</div>
          </div>
        </div>
        <el-descriptions :column="3" border size="small" style="margin-top:10px;">
          <el-descriptions-item label="底薪基数">¥{{ fmtNum(row.baseWage) }}</el-descriptions-item>
          <el-descriptions-item label="出勤天数">{{ row.attendanceDays }}天</el-descriptions-item>
          <el-descriptions-item label="当月底薪绩效"><span style="color:var(--qb-primary)">¥{{ fmtNum(row.performancePay) }}</span></el-descriptions-item>
          <el-descriptions-item label="档位倍率">{{ row.tierRate }} 人/天</el-descriptions-item>
          <el-descriptions-item label="晋级奖金"><span style="color:var(--qb-success)">+¥{{ row.promotionBonus }}</span></el-descriptions-item>
          <el-descriptions-item label="品质扣款"><span style="color:var(--qb-danger)">-¥{{ Math.abs(row.lateDeduction ?? 0) }}</span></el-descriptions-item>
          <el-descriptions-item label="实发合计" :span="3">
            <span style="font-size:18px; font-weight:800; color:var(--qb-primary)">¥{{ fmtNum(row.actualTotal) }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="dialogDetail = false">关 闭</el-button>
        <el-button class="qb-btn-primary" :icon="Download">导出账单</el-button>
      </template>
    </el-dialog>

    <!-- 新增/编辑薪资 Dialog -->
    <el-dialog
      v-model="dialogForm"
      :title="isEdit ? '编辑薪资记录' : '录入薪资记录'"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form ref="salaryFormRef" :model="salaryForm" :rules="salaryRules" label-width="110px" size="small">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="账期" prop="salaryMonth">
              <el-date-picker v-model="salaryForm.salaryMonth" type="month" format="YYYY-MM" value-format="YYYY-MM" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="员工姓名" prop="name">
              <el-input v-model="salaryForm.name" placeholder="姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="岗位">
              <el-input v-model="salaryForm.position" placeholder="如：客服主管" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="底薪基数(¥)" prop="baseWage">
              <el-input-number v-model="salaryForm.baseWage" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出勤天数">
              <el-input-number v-model="salaryForm.attendanceDays" :min="0" :max="31" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当月底薪绩效(¥)">
              <el-input-number v-model="salaryForm.performancePay" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="在岗日薪(¥)">
              <el-input-number v-model="salaryForm.shopDailyRate" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="档位倍率">
              <el-input-number v-model="salaryForm.tierRate" :min="0" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="晋级奖金(¥)">
              <el-input-number v-model="salaryForm.promotionBonus" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="待岗扣款">
              <el-input-number v-model="salaryForm.standbyDeduction" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="请假扣款">
              <el-input-number v-model="salaryForm.leaveDeduction" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="借款金额">
              <el-input-number v-model="salaryForm.loanDeduction" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单件补贴">
              <el-input-number v-model="salaryForm.unitSubsidy" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="专项补贴">
              <el-input-number v-model="salaryForm.specialSubsidy" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="迟到扣款">
              <el-input-number v-model="salaryForm.lateDeduction" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="15日补贴">
              <el-input-number v-model="salaryForm.midSubsidy" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="额外工资">
              <el-input-number v-model="salaryForm.extraWage" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="政策奖金备注">
              <el-input v-model="salaryForm.policyBonusNote" placeholder="政策奖金说明" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 实发合计预览 -->
        <el-divider />
        <div class="form-total-preview">
          <span class="form-total-label">实发合计预估：</span>
          <span class="form-total-value">¥{{ fmtNum(computedActualTotal) }}</span>
          <span class="form-total-tip">（底薪绩效 + 奖金补贴 - 各项扣款）</span>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogForm = false">取 消</el-button>
        <el-button class="qb-btn-primary" :loading="submitLoading" @click="handleSubmit">确 认 保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="QingbirdSalary">
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Money, View, Refresh, List, Search, InfoFilled, Download, WarningFilled, Plus, EditPen, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const now = new Date()
const selectedMonth = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const loading = ref(false)
const searchName = ref('')
const dialogDetail = ref(false)

const salaryData = reactive({
  estimatedTotal: 3557,
  tierRate: 698,
  tierMonths: 1,
  promotionBonus: 500,
  qualityDeduction: 101,
})

const tableData = ref([
  {
    id: 1,
    name: '测试12',
    position: '客服主管',
    avatarColor: '#6C4EF2',
    baseWage: 3000,
    attendanceDays: 30,
    performancePay: 3000,
    shopDailyRate: 158,
    tierRate: 698,
    promotionBonus: 500,
    standbyDeduction: 0,
    leaveDeduction: 0,
    loanDeduction: 0,
    unitSubsidy: 0,
    specialSubsidy: 0,
    lateDeduction: -101,
    midSubsidy: 0,
    extraWage: 0,
    policyBonusNote: '入入薪资忠...',
    actualTotal: 3557,
  },
])

const filteredTableData = computed(() => {
  if (!searchName.value) return tableData.value
  return tableData.value.filter(r => r.name.includes(searchName.value))
})

const fmtNum = (v) => {
  if (v === null || v === undefined) return '0'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const disableFutureMonth = (date) => date > new Date()

const getSummary = ({ columns, data }) => {
  const sums = []
  columns.forEach((col, idx) => {
    if (idx === 0) { sums[idx] = '合 计'; return }
    const numCols = ['baseWage', 'performancePay', 'actualTotal']
    if (col.property && numCols.includes(col.property)) {
      const total = data.reduce((sum, r) => sum + (Number(r[col.property]) || 0), 0)
      sums[idx] = '¥' + fmtNum(total)
    } else {
      sums[idx] = '--'
    }
  })
  return sums
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request({
      url: '/qingbird/salary/list',
      method: 'get',
      params: { salaryMonth: selectedMonth.value },
      hideErrorMsg: true
    })
    if (res?.code === 200) {
      tableData.value = res.rows || []
      if (res.data?.overview) Object.assign(salaryData, res.data.overview)
      recomputeKpi()
    }
  } catch {
    // 保持 mock 数据
  } finally {
    loading.value = false
  }
}

const recomputeKpi = () => {
  salaryData.estimatedTotal = tableData.value.reduce((s, r) => s + (r.actualTotal || 0), 0)
  salaryData.promotionBonus = tableData.value.reduce((s, r) => s + (r.promotionBonus || 0), 0)
  salaryData.qualityDeduction = Math.abs(tableData.value.reduce((s, r) => s + (r.lateDeduction || 0), 0))
}

// ====== 新增 / 编辑 ======
const dialogForm = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const salaryFormRef = ref(null)

const defaultForm = () => ({
  id: null,
  salaryMonth: selectedMonth.value,
  name: '', position: '', avatarColor: '#6C4EF2',
  baseWage: 0, attendanceDays: 30, performancePay: 0,
  shopDailyRate: 0, tierRate: 0, promotionBonus: 0,
  standbyDeduction: 0, leaveDeduction: 0, loanDeduction: 0,
  unitSubsidy: 0, specialSubsidy: 0, lateDeduction: 0,
  midSubsidy: 0, extraWage: 0, policyBonusNote: ''
})

const salaryForm = reactive(defaultForm())

const salaryRules = {
  salaryMonth: [{ required: true, message: '请选择账期', trigger: 'change' }],
  name:        [{ required: true, message: '请输入员工姓名', trigger: 'blur' }],
  baseWage:    [{ required: true, message: '请填写底薪基数', trigger: 'blur' }],
}

// 实时计算实发合计
const computedActualTotal = computed(() => {
  const f = salaryForm
  return (f.performancePay || 0)
    + (f.promotionBonus || 0)
    + (f.unitSubsidy || 0)
    + (f.specialSubsidy || 0)
    + (f.midSubsidy || 0)
    + (f.extraWage || 0)
    + (f.standbyDeduction || 0)  // 负数
    + (f.leaveDeduction || 0)
    + (f.lateDeduction || 0)
    - Math.abs(f.loanDeduction || 0)
})

const openAddDialog = () => {
  isEdit.value = false
  Object.assign(salaryForm, defaultForm(), { salaryMonth: selectedMonth.value })
  dialogForm.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  Object.assign(salaryForm, { ...row })
  dialogForm.value = true
}

const handleSubmit = async () => {
  await salaryFormRef.value.validate()
  submitLoading.value = true
  const payload = { ...salaryForm, actualTotal: computedActualTotal.value }
  try {
    const res = await request({
      url: isEdit.value ? '/qingbird/salary' : '/qingbird/salary',
      method: isEdit.value ? 'put' : 'post',
      data: payload,
      hideErrorMsg: true
    })
    if (res?.code === 200) {
      ElMessage.success(isEdit.value ? '更新成功' : '录入成功')
      dialogForm.value = false
      fetchData()
    } else {
      // 后端未实现：本地更新
      localSave(payload)
    }
  } catch {
    localSave(payload)
  } finally {
    submitLoading.value = false
  }
}

const localSave = (payload) => {
  if (isEdit.value) {
    const idx = tableData.value.findIndex(r => r.id === payload.id)
    if (idx !== -1) tableData.value.splice(idx, 1, { ...payload })
  } else {
    tableData.value.push({ ...payload, id: Date.now(), actualTotal: computedActualTotal.value })
  }
  recomputeKpi()
  ElMessage.success((isEdit.value ? '更新' : '录入') + '成功（本地模式，后端接口未连接）')
  dialogForm.value = false
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确认删除 ${row.name} 的 ${row.salaryMonth || selectedMonth.value} 薪资记录？`, '提示', {
    confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning'
  })
  try {
    const res = await request({ url: `/qingbird/salary/${row.id}`, method: 'delete', hideErrorMsg: true })
    if (res?.code === 200) {
      ElMessage.success('删除成功')
      fetchData()
    } else { localDelete(row.id) }
  } catch { localDelete(row.id) }
}

const localDelete = (id) => {
  tableData.value = tableData.value.filter(r => r.id !== id)
  recomputeKpi()
  ElMessage.success('删除成功（本地模式）')
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
/* ---- 页面头部 ---- */
.salary-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.salary-title-group {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.salary-title-icon {
  width: 48px;
  height: 48px;
  background: var(--qb-primary-bg);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--qb-primary);
  font-size: 24px;
  flex-shrink: 0;
  margin-top: 2px;
}

.salary-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ---- KPI 卡片 ---- */
.salary-kpi-card {
  border-radius: var(--qb-radius);
  padding: 20px 22px;
  min-height: 130px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--qb-shadow-sm);
  transition: box-shadow .2s, transform .2s;

  &:hover {
    box-shadow: var(--qb-shadow-md);
    transform: translateY(-2px);
  }
}

/* 深色 月度总量卡 */
.dark-card {
  background: var(--qb-dark-card-bg);
  color: #fff;
}

.kpi-card-bg-icon {
  position: absolute;
  right: -8px;
  top: -10px;
  font-size: 72px;
  opacity: .08;
}

.kpi-card-label {
  font-size: 12px;
  opacity: .6;
  margin-bottom: 12px;
}

.kpi-card-label-sm {
  font-size: 11px;
  color: var(--qb-text-muted);
  margin-bottom: 10px;
}

.kpi-card-value {
  font-size: 34px;
  font-weight: 900;
  line-height: 1;
  color: #fff;
}

.kpi-currency {
  font-size: 18px;
  font-weight: 500;
  margin-right: 2px;
  opacity: .8;
}

.kpi-card-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  opacity: .6;
  margin-top: 10px;
}

/* 档位卡 */
.tier-card {
  background: #fff;
  border: 1px solid var(--qb-border);
}

.kpi-tier-value {
  font-size: 38px;
  font-weight: 900;
  color: var(--qb-primary);
  line-height: 1;
}

.kpi-tier-unit {
  font-size: 13px;
  color: var(--qb-text-muted);
  margin-top: 4px;
}

.kpi-tier-sub {
  font-size: 10px;
  color: var(--qb-text-muted);
  letter-spacing: .08em;
  margin-top: 8px;
  opacity: .7;
}

/* 奖金卡 */
.bonus-card {
  background: #fff;
  border: 1px solid var(--qb-border);
}

.kpi-bonus-value {
  font-size: 32px;
  font-weight: 900;
  color: var(--qb-success);
  line-height: 1;
  margin-top: 4px;
}

/* 扣款卡 */
.deduct-card {
  background: #fff;
  border: 1px solid var(--qb-border);
}

.kpi-deduct-value {
  font-size: 32px;
  font-weight: 900;
  color: var(--qb-danger);
  line-height: 1;
  margin-top: 4px;
}

/* ---- 薪资大表 ---- */
.salary-table-card {
  padding: 20px 22px;
}

.salary-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--qb-text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.period-tag {
  color: var(--qb-primary);
}

.table-scroll-wrap {
  overflow-x: auto;
}

.member-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.member-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.member-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
}

.member-pos {
  font-size: 10px;
  color: var(--qb-text-muted);
}

.days-val {
  font-size: 15px;
  font-weight: 700;
  color: var(--qb-primary);
}

.shop-cell {
  text-align: center;
}

.shop-price {
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
  margin-bottom: 2px;
}

.val-danger {
  color: var(--qb-danger);
  font-weight: 700;
}

.val-normal {
  color: var(--qb-text-muted);
}

.total-pay {
  font-size: 15px;
  font-weight: 800;
  color: var(--qb-primary);
}

/* ---- 政策说明 ---- */
.policy-note {
  padding: 16px 22px;
  background: #FAFBFF;
  border: 1px solid var(--qb-primary-bg);
}

.policy-note-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
  margin-bottom: 8px;
}

.policy-note-text {
  font-size: 13px;
  color: var(--qb-text-muted);
  line-height: 1.8;
  margin: 0;
}

/* ---- 详情弹窗 ---- */
.detail-item {
  & + & {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--qb-border);
  }
}

.detail-member {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

/* ---- 实发合计预览 ---- */
.form-total-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--qb-primary-bg);
  border-radius: var(--qb-radius-sm);
}

.form-total-label {
  font-size: 13px;
  color: var(--qb-text-muted);
  font-weight: 600;
}

.form-total-value {
  font-size: 22px;
  font-weight: 900;
  color: var(--qb-primary);
}

.form-total-tip {
  font-size: 11px;
  color: var(--qb-text-muted);
}
</style>
