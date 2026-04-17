<template>
  <div class="qb-page">
    <!-- 页面标题 -->
    <div class="qb-page-header shop-header">
      <div class="shop-title-group">
        <div class="shop-title-icon"><el-icon><Shop /></el-icon></div>
        <div>
          <h1 class="qb-page-title">店铺管理</h1>
          <p class="qb-page-subtitle">管理分公司旗下所有运营店铺，分配客服坐席，追踪产值与到期状态</p>
        </div>
      </div>
      <div class="shop-header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="fetchData" style="border-radius:8px;">刷新数据</el-button>
        <el-button class="qb-btn-primary" :icon="Plus" @click="openAddDialog">录入新店铺</el-button>
      </div>
    </div>

    <!-- 顶部 KPI -->
    <el-row :gutter="14" v-loading="loading">
      <el-col :span="6">
        <div class="shop-kpi-card light-card">
          <div class="kpi-icon-wrap blue">
            <el-icon><Calendar /></el-icon>
          </div>
          <div class="kpi-body">
            <div class="kpi-label">维护户产品总量</div>
            <div class="kpi-value">¥{{ fmtNum(stats.totalAssets) }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="shop-kpi-card light-card">
          <div class="kpi-icon-wrap orange">
            <el-icon><Warning /></el-icon>
          </div>
          <div class="kpi-body">
            <div class="kpi-label">待到总量</div>
            <div class="kpi-value">¥{{ fmtNum(stats.pendingAmount) }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="shop-kpi-card light-card">
          <div class="kpi-icon-wrap purple">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="kpi-body">
            <div class="kpi-label">近30天客询总量</div>
            <div class="kpi-value">{{ fmtNum(stats.monthConsultation) }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="shop-kpi-card dark-card">
          <div class="dark-kpi-bg">🏪</div>
          <div class="kpi-body">
            <div class="kpi-label white">智能店铺指数</div>
            <div class="kpi-value-big">{{ stats.shopCount }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <div class="qb-card search-area" style="margin-top:14px;">
      <el-input
        v-model="query.keyword"
        placeholder="全局搜索1000+家店铺..."
        :prefix-icon="Search"
        clearable
        style="width:100%; font-size:14px;"
        @keyup.enter="fetchData"
      />
      <div class="filter-row">
        <div class="filter-group">
          <span class="filter-label">等级：</span>
          <el-radio-group v-model="query.grade" size="small" @change="fetchData">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="S">S</el-radio-button>
            <el-radio-button value="A">A</el-radio-button>
            <el-radio-button value="B">B</el-radio-button>
            <el-radio-button value="C">C</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-group">
          <span class="filter-label">归属：</span>
          <el-select v-model="query.branchId" size="small" style="width:130px;" @change="fetchData">
            <el-option label="全部主体" value="" />
            <el-option label="Q43-锦鲤电商" value="100" />
          </el-select>
        </div>
        <el-button size="small" :icon="Filter" @click="showFilter = !showFilter">显示筛选</el-button>
        <div style="margin-left:auto;">
          <el-button class="qb-btn-primary" size="small" :icon="Search" @click="fetchData">搜 索</el-button>
        </div>
      </div>
    </div>

    <!-- 店铺表格 -->
    <div class="qb-card" style="margin-top:14px;">
      <el-table
        :data="tableData"
        v-loading="loading"
        style="width:100%;"
        size="small"
        @selection-change="handleSelectionChange"
        empty-text="暂无店铺数据"
      >
        <el-table-column type="selection" width="40" />

        <!-- 店铺名 -->
        <el-table-column label="店铺名" min-width="200">
          <template #default="{ row }">
            <div class="shop-name-cell">
              <div class="shop-platform-dot" :style="{ background: platColor(row.platformType) }"></div>
              <div>
                <div class="shop-name">{{ row.shopName }}</div>
                <div class="shop-platform-tag">{{ platLabel(row.platformType) }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <!-- 所属公司 -->
        <el-table-column label="所属公司" width="130">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" style="font-weight:700; font-size:12px;">
              {{ row.branchName || 'Q43-锦鲤电商' }}
            </el-link>
          </template>
        </el-table-column>

        <!-- 负责客服 -->
        <el-table-column label="负责客服" width="110">
          <template #default="{ row }">
            <div v-if="row.employeeName" class="employee-cell">
              <div class="emp-mini-avatar" :style="{ background: row.avatarColor || '#6C4EF2' }">
                {{ row.employeeName?.[0] }}
              </div>
              <span class="emp-name-sm">{{ row.employeeName }}</span>
            </div>
            <span v-else class="cell-muted">未指派</span>
          </template>
        </el-table-column>

        <!-- 子账号数 -->
        <el-table-column label="子账号数" width="90" align="center">
          <template #default="{ row }">
            <div class="sub-account-cell">
              <el-icon style="color:var(--qb-info); font-size:13px;"><User /></el-icon>
              <span>{{ row.subAccountCount ?? 0 }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 近30天客询量 -->
        <el-table-column label="近30天客询量" width="110" align="center">
          <template #default="{ row }">
            <div class="consult-cell">
              <el-icon style="color:var(--qb-primary); font-size:13px;"><ChatDotRound /></el-icon>
              <span>{{ row.monthConsultation ?? 0 }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 金额 -->
        <el-table-column label="金额" width="100" align="right">
          <template #default="{ row }">
            <span class="amount-val">¥{{ fmtNum(row.amount) }}</span>
          </template>
        </el-table-column>

        <!-- 到期日期 -->
        <el-table-column label="到期日期" width="100" align="center">
          <template #default="{ row }">
            <span class="cell-muted" style="font-size:12px;">{{ row.expireDate || '——' }}</span>
          </template>
        </el-table-column>

        <!-- 到期状态 -->
        <el-table-column label="到期状态" width="90" align="center">
          <template #default="{ row }">
            <div class="expire-status" v-if="row.daysLeft !== undefined">
              <el-tag :type="row.daysLeft <= 7 ? 'danger' : row.daysLeft <= 30 ? 'warning' : 'success'" size="small" round>
                剩余{{ row.daysLeft }}天
              </el-tag>
            </div>
            <span v-else class="cell-muted">——</span>
          </template>
        </el-table-column>

        <!-- 备注 -->
        <el-table-column label="备注" width="60" align="center">
          <template #default="{ row }">
            <el-tooltip :content="row.remark || '无备注'" placement="top" v-if="row.remark">
              <el-icon style="color:var(--qb-text-muted); cursor:pointer;"><Warning /></el-icon>
            </el-tooltip>
            <span v-else class="cell-muted">——</span>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">
              <el-icon><Edit /></el-icon>续
            </el-button>
            <el-button link size="small" @click="handleAssignEmployee(row)" style="color:var(--qb-success);">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <span class="table-total">共 {{ total }} 家店铺</span>
        <el-pagination
          v-model:current-page="query.pageNum"
          v-model:page-size="query.pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @change="fetchData"
        />
      </div>
    </div>

    <!-- 录入/编辑店铺 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑店铺信息' : '录入新店铺'"
      width="580px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="店铺名称" prop="shopName">
              <el-input v-model="form.shopName" placeholder="如：Q43-糖小精美妆-全包-服-X5" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="平台类型">
              <el-select v-model="form.platformType" style="width:100%;">
                <el-option :value="1" label="淘宝" />
                <el-option :value="2" label="京东" />
                <el-option :value="3" label="拼多多" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="店铺等级">
              <el-select v-model="form.grade" style="width:100%;">
                <el-option value="S" label="S级" />
                <el-option value="A" label="A级" />
                <el-option value="B" label="B级" />
                <el-option value="C" label="C级" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="平台账号">
              <el-input v-model="form.loginAccount" placeholder="千牛/平台登录主账号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="店铺标识">
              <el-input v-model="form.shopKey" placeholder="用于爬虫识别（如：糖小精）" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同金额(¥)">
              <el-input-number v-model="form.amount" :min="0" :precision="2" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同到期日">
              <el-date-picker v-model="form.expireDate" type="date" value-format="YYYY-MM-DD" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button class="qb-btn-primary" @click="handleSubmit">确 认 保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="QingbirdShop">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Shop, Refresh, Plus, Search, Filter, Calendar, Warning,
  ChatDotRound, User, Edit
} from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const showFilter = ref(false)
const selectedRows = ref([])

const stats = reactive({
  totalAssets: 2150,
  pendingAmount: 0,
  monthConsultation: 0,
  shopCount: 4
})

const query = reactive({
  pageNum: 1, pageSize: 10,
  keyword: '', grade: '', branchId: ''
})

const form = reactive({
  id: null, shopName: '', platformType: 1, grade: 'A',
  loginAccount: '', shopKey: '',
  amount: 0, expireDate: null, remark: '', status: '0'
})

const rules = {
  shopName: [{ required: true, message: '请输入店铺名称', trigger: 'blur' }]
}

// mock 数据（后端未实现时使用）
const mockShops = [
  { id: 1, shopName: 'Q43-糖小精美妆-全包-服-X5', platformType: 1, branchName: 'Q43-锦鲤电商', employeeName: '未指派', avatarColor: '#6C4EF2', subAccountCount: 0, monthConsultation: 0, amount: 900, expireDate: '2026-03-26', daysLeft: 12 },
  { id: 2, shopName: 'Q43-大山家耙耙柑-售前售后服-X5', platformType: 1, branchName: 'Q43-锦鲤电商', employeeName: '未指派', avatarColor: '#3B82F6', subAccountCount: 3, monthConsultation: 0, amount: 600, expireDate: '2026-04-03', daysLeft: 20 },
  { id: 3, shopName: 'Q43-炎森家居清洁-全包-服-X5', platformType: 1, branchName: 'Q43-锦鲤电商', employeeName: '未指派', avatarColor: '#10B981', subAccountCount: 0, monthConsultation: 0, amount: 400, expireDate: '2026-04-06', daysLeft: 23 },
  { id: 4, shopName: 'Q43-邓家竹园-售前售后-服-X1', platformType: 1, branchName: 'Q43-锦鲤电商', employeeName: '未指派', avatarColor: '#F59E0B', subAccountCount: 0, monthConsultation: 0, amount: 250, expireDate: '2026-04-07', daysLeft: 24 },
]

const fmtNum = (v) => {
  if (!v && v !== 0) return '0'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const platLabel = (p) => p === 1 ? '淘宝' : p === 2 ? '京东' : '拼多多'
const platColor = (p) => p === 1 ? '#FF6900' : p === 2 ? '#E2231A' : '#C0392B'

const handleSelectionChange = (rows) => { selectedRows.value = rows }

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request({
      url: '/qingbird/shop/list', method: 'get',
      params: { ...query },
      hideErrorMsg: true
    })
    if (res?.code === 200) {
      tableData.value = res.rows || []
      total.value = res.total || 0
      if (res.data?.stats) Object.assign(stats, res.data.stats)
    } else { useMock() }
  } catch { useMock() }
  finally { loading.value = false }
}

const useMock = () => {
  let filtered = mockShops.filter(s => {
    if (query.keyword && !s.shopName.includes(query.keyword)) return false
    if (query.grade && s.grade && s.grade !== query.grade) return false
    return true
  })
  tableData.value = filtered
  total.value = filtered.length
  stats.shopCount = filtered.length
  stats.totalAssets = filtered.reduce((sum, s) => sum + (s.amount || 0), 0)
}

const resetForm = () => Object.assign(form, {
  id: null, shopName: '', platformType: 1, grade: 'A',
  loginAccount: '', shopKey: '', amount: 0, expireDate: null, remark: '', status: '0'
})

const openAddDialog = () => { isEdit.value = false; resetForm(); dialogVisible.value = true }

const openEditDialog = (row) => {
  isEdit.value = true
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate()
  const url = isEdit.value ? '/qingbird/shop' : '/qingbird/shop'
  const method = isEdit.value ? 'put' : 'post'
  try {
    const res = await request({ url, method, data: { ...form }, hideErrorMsg: true })
    if (res?.code === 200) {
      ElMessage.success(isEdit.value ? '更新成功' : '录入成功')
      dialogVisible.value = false; fetchData()
    } else {
      // 演示模式
      ElMessage.success('保存成功（演示模式）')
      if (!isEdit.value) {
        mockShops.unshift({ ...form, id: Date.now(), branchName: 'Q43-锦鲤电商', subAccountCount: 0, monthConsultation: 0, daysLeft: 30 })
      }
      dialogVisible.value = false; useMock()
    }
  } catch {
    ElMessage.success('保存成功（演示模式）')
    dialogVisible.value = false
  }
}

const handleAssignEmployee = (row) => {
  ElMessage.info(`分配客服功能：请在员工花名册中为该店铺分配坐席（${row.shopName}）`)
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
/* ---- 页头 ---- */
.shop-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.shop-title-group {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.shop-title-icon {
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

.shop-header-actions {
  display: flex;
  gap: 10px;
}

/* ---- KPI 卡 ---- */
.shop-kpi-card {
  border-radius: var(--qb-radius);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--qb-shadow-sm);
  transition: box-shadow .2s, transform .2s;
  min-height: 88px;
  position: relative;
  overflow: hidden;

  &:hover {
    box-shadow: var(--qb-shadow-md);
    transform: translateY(-2px);
  }
}

.light-card {
  background: #fff;
  border: 1px solid var(--qb-border);
}

.dark-card {
  background: var(--qb-dark-card-bg);
  color: #fff;
}

.kpi-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;

  &.blue   { background: #EEF6FF; color: #3B82F6; }
  &.orange { background: #FFF7ED; color: #F97316; }
  &.purple { background: var(--qb-primary-bg); color: var(--qb-primary); }
}

.kpi-body { flex: 1; min-width: 0; }

.kpi-label {
  font-size: 12px;
  color: var(--qb-text-muted);
  margin-bottom: 6px;
  &.white { color: rgba(255,255,255,.6); }
}

.kpi-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--qb-text-primary);
  line-height: 1;
}

.dark-kpi-bg {
  position: absolute;
  right: -6px;
  top: -8px;
  font-size: 64px;
  opacity: .08;
}

.kpi-value-big {
  font-size: 38px;
  font-weight: 900;
  color: #fff;
  line-height: 1;
}

/* ---- 搜索区 ---- */
.search-area { padding: 16px 20px; }

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 12px;
  color: var(--qb-text-muted);
  white-space: nowrap;
}

/* ---- 表格 ---- */
.shop-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.shop-platform-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 2px;
}

.shop-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
}

.shop-platform-tag {
  font-size: 10px;
  color: var(--qb-text-muted);
  margin-top: 2px;
}

.employee-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.emp-mini-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.emp-name-sm { font-size: 12px; color: var(--qb-text-primary); }

.sub-account-cell,
.consult-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
}

.amount-val {
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
}

.expire-status { display: flex; justify-content: center; }

.cell-muted { font-size: 12px; color: var(--qb-text-muted); }

.pagination-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
}

.table-total {
  font-size: 12px;
  color: var(--qb-text-muted);
}
</style>
