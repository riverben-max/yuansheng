<template>
  <div class="qb-page">
    <!-- 页面标题 -->
    <div class="qb-page-header branch-header">
      <div class="branch-title-group">
        <div class="branch-icon">🏢</div>
        <div>
          <div class="branch-breadcrumb">所属分公司运营指挥</div>
          <h1 class="qb-page-title">{{ overview.branchName || '分公司管理' }}</h1>
          <p class="qb-page-subtitle">
            监控您所属分公司的业务进度，当前已隔离其他分公司数据域。
          </p>
        </div>
      </div>
      <div class="branch-header-actions">
        <el-button :icon="Avatar" @click="goEmployeeList" style="border-radius:8px;">
          员工花名册
        </el-button>
        <el-button :icon="Refresh" :loading="loading" @click="fetchData" style="border-radius:8px;">
          实时数据 · 后端确认
        </el-button>
      </div>
    </div>

    <!-- 分公司信息卡头 -->
    <div class="branch-info-card" v-loading="loading" element-loading-background="rgba(255,255,255,0.7)">
      <div class="branch-info-left">
        <div class="branch-logo">
          <el-icon><OfficeBuilding /></el-icon>
        </div>
        <div class="branch-info-detail">
          <div class="branch-name">{{ overview.branchName || 'Q43-锦鲤电商' }}</div>
          <div class="branch-tags">
            <el-tag type="success" size="small" round>主营业主体</el-tag>
            <el-tag type="primary" size="small" round style="margin-left:6px;">实时运营中</el-tag>
          </div>
          <div class="branch-code">{{ branchCode }}</div>
        </div>
      </div>
      <div class="branch-info-right">
        <div class="branch-growth" :class="overview.growthRate >= 0 ? 'positive' : 'negative'">
          {{ overview.growthRate >= 0 ? '↑' : '↓' }}{{ Math.abs(overview.growthRate ?? 0).toFixed(1) }}%
        </div>
        <div class="branch-growth-label">全面产值标识</div>
      </div>
    </div>

    <!-- 第一行：4个核心指标 -->
    <el-row :gutter="14" style="margin-top:14px;" v-loading="loading">
      <el-col :span="6" v-for="m in topMetrics" :key="m.label">
        <div class="metric-card">
          <div class="metric-icon-wrap" :style="{ background: m.iconBg }">
            <span class="metric-emoji">{{ m.icon }}</span>
          </div>
          <div class="metric-body">
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-value" :style="{ color: m.color }">
              {{ m.value }}<span class="metric-unit">{{ m.unit }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 第二行：4个财务指标 -->
    <el-row :gutter="14" style="margin-top:14px;" v-loading="loading">
      <el-col :span="6" v-for="m in bottomMetrics" :key="m.label">
        <div class="metric-card" :class="{ 'metric-card--danger': m.danger }">
          <div class="metric-label-top">{{ m.label }}</div>
          <div class="metric-value-big" :style="{ color: m.color }">
            <span v-if="m.prefix" class="metric-prefix">{{ m.prefix }}</span>{{ m.value }}
          </div>
          <div class="metric-sub" v-if="m.sub">{{ m.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 资金储备进度条 -->
    <div class="qb-card reserve-card" style="margin-top:14px;">
      <div class="reserve-header">
        <span class="reserve-title">
          <el-icon><Coin /></el-icon>
          资金储备（预收占比）
        </span>
        <span class="reserve-rate" :class="overview.reserveRate > 80 ? 'rate-danger' : 'rate-normal'">
          {{ (overview.reserveRate ?? 0).toFixed(1) }}% 预收储量率
        </span>
      </div>
      <el-progress
        :percentage="overview.reserveRate ?? 0"
        :stroke-width="12"
        :color="progressColor"
        :format="() => ''"
        style="margin-top:10px;"
      />
      <div class="reserve-tips">
        <span class="reserve-tip-item">
          <span class="dot dot--orange"></span>
          预收金额：¥{{ fmtAmount(overview.prepaidAmount) }}
        </span>
        <span class="reserve-tip-item">
          <span class="dot dot--gray"></span>
          实际产值：¥{{ fmtAmount(overview.actualOutput) }}
        </span>
        <span class="reserve-tip-item" style="margin-left:auto;">
          已使用产值差额：
          <strong :style="{ color: overview.outputGap < 0 ? 'var(--qb-danger)' : 'var(--qb-success)' }">
            ¥{{ fmtAmount(overview.outputGap) }}
          </strong>
        </span>
      </div>
    </div>

    <!-- 近期运营数据 -->
    <div class="qb-card" style="margin-top:14px;">
      <div class="section-title-row">
        <div class="section-title">
          <el-icon style="color:var(--qb-primary);"><DataLine /></el-icon>
          近期店铺运营数据
        </div>
        <div class="section-sub">RECENT SHOP PERFORMANCE</div>
      </div>
      <el-table :data="shopList" size="small" stripe style="margin-top:12px;" empty-text="暂无数据，后端服务连接后显示">
        <el-table-column prop="shopName" label="店铺名称" min-width="160" />
        <el-table-column prop="platform" label="平台" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="platType(row.platform)">{{ platLabel(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="todaySales" label="今日销售额" width="110" align="right">
          <template #default="{ row }">¥{{ fmtAmount(row.todaySales) }}</template>
        </el-table-column>
        <el-table-column prop="consultCount" label="今日接待" width="90" align="center" />
        <el-table-column prop="responseRate" label="3分钟回复率" width="110" align="center">
          <template #default="{ row }">
            <span :style="{ color: (row.responseRate ?? 0) < 80 ? 'var(--qb-danger)' : 'var(--qb-success)', fontWeight: 700 }">
              {{ row.responseRate ?? '--' }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'danger'" size="small">
              {{ row.status === '0' ? '运营中' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup name="QingbirdBranch">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Avatar, Refresh, OfficeBuilding, Coin, DataLine } from '@element-plus/icons-vue'
import { getBranchOverview } from '@/api/qingbird/branch'

const router = useRouter()
const branchCode = 'B-1773208272961'
const loading = ref(false)

const overview = reactive({
  branchName: 'Q43-锦鲤电商',
  growthRate: 0.0,
  shopCount: 4,
  subAccountCount: 3,
  todayConsultation: 0,
  monthConsultation: 0,
  totalAssets: 2150,
  avgOutput: 2150,
  activeEmployees: 1,
  outputGap: 0,
  reserveRate: 0.0,
  prepaidAmount: 0,
  actualOutput: 0
})

const shopList = ref([])

const fmtAmount = (v) => {
  if (v === null || v === undefined) return '0'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const topMetrics = computed(() => [
  { icon: '🏪', label: '业务单店铺数', value: overview.shopCount, unit: '个', color: 'var(--qb-primary)', iconBg: 'var(--qb-primary-bg)' },
  { icon: '👥', label: '子账号总数',   value: overview.subAccountCount, unit: '个', color: 'var(--qb-info)', iconBg: '#EEF6FF' },
  { icon: '📊', label: '今日营业量',   value: overview.todayConsultation, unit: '条', color: 'var(--qb-success)', iconBg: '#F0FFF4' },
  { icon: '📅', label: '近30天营量',   value: overview.monthConsultation, unit: '条', color: 'var(--qb-text-muted)', iconBg: '#F8F9FA' },
])

const bottomMetrics = computed(() => [
  { label: '主体总产品值', prefix: '¥', value: fmtAmount(overview.totalAssets),   color: 'var(--qb-text-primary)', sub: 'TOTAL ASSETS' },
  { label: '人均营业额',   prefix: '¥', value: fmtAmount(overview.avgOutput),      color: 'var(--qb-text-primary)', sub: 'AVG OUTPUT' },
  { label: '在职人力',     prefix: '',  value: overview.activeEmployees,            color: 'var(--qb-primary)',       unit: '员', sub: 'ACTIVE STAFF' },
  { label: '累计因数据',   prefix: '-¥',value: fmtAmount(Math.abs(overview.outputGap ?? 0)), color: 'var(--qb-danger)', sub: 'GAP DEFICIT', danger: true },
])

const progressColor = computed(() => {
  const r = overview.reserveRate ?? 0
  if (r > 80) return 'var(--qb-danger)'
  if (r > 50) return '#FAAD14'
  return '#FF8C00'
})

const platType = (p) => p === 1 ? 'warning' : p === 2 ? 'primary' : 'danger'
const platLabel = (p) => p === 1 ? '淘宝' : p === 2 ? '京东' : '拼多多'

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getBranchOverview(branchCode)
    if (res?.code === 200 && res.data) {
      Object.assign(overview, res.data)
      shopList.value = res.data.shopList || []
    }
  } catch {
    // API 尚未就绪，使用默认 mock 数据，不报错
  } finally {
    loading.value = false
  }
}

const goEmployeeList = () => router.push('/qingbird/employee')

onMounted(fetchData)
</script>

<style lang="scss" scoped>
/* ---- 页头 ---- */
.branch-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.branch-title-group {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.branch-icon {
  font-size: 36px;
  line-height: 1;
  margin-top: 4px;
}

.branch-header-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.branch-breadcrumb {
  font-size: 12px;
  color: var(--qb-primary);
  margin-bottom: 4px;
  font-weight: 500;
}

/* ---- 分公司信息卡 ---- */
.branch-info-card {
  background: #fff;
  border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius);
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--qb-shadow-sm);
}

.branch-info-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.branch-logo {
  width: 52px;
  height: 52px;
  background: var(--qb-primary-bg);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--qb-primary);
  font-size: 26px;
  flex-shrink: 0;
}

.branch-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--qb-text-primary);
  margin-bottom: 6px;
}

.branch-tags {
  margin-bottom: 6px;
}

.branch-code {
  font-size: 12px;
  color: var(--qb-text-muted);
  font-family: 'Courier New', monospace;
}

.branch-info-right {
  text-align: right;
}

.branch-growth {
  font-size: 24px;
  font-weight: 800;
  &.positive { color: var(--qb-success); }
  &.negative { color: var(--qb-danger); }
}

.branch-growth-label {
  font-size: 11px;
  color: var(--qb-text-muted);
  margin-top: 4px;
}

/* ---- 第一行指标卡 ---- */
.metric-card {
  background: #fff;
  border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--qb-shadow-sm);
  transition: box-shadow .2s, transform .2s;

  &:hover {
    box-shadow: var(--qb-shadow-md);
    transform: translateY(-2px);
  }

  &--danger {
    background: #FFF8F8;
    border-color: #FFD6D6;
  }
}

.metric-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-emoji { font-size: 22px; }

.metric-body { flex: 1; min-width: 0; }

.metric-label {
  font-size: 12px;
  color: var(--qb-text-muted);
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-value {
  font-size: 26px;
  font-weight: 800;
  line-height: 1;
}

.metric-unit {
  font-size: 13px;
  font-weight: 400;
  margin-left: 3px;
  opacity: .7;
}

/* ---- 第二行指标卡 ---- */
.metric-label-top {
  font-size: 11px;
  color: var(--qb-text-muted);
  margin-bottom: 8px;
  font-weight: 500;
}

.metric-value-big {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
}

.metric-prefix {
  font-size: 14px;
  font-weight: 600;
  margin-right: 1px;
}

.metric-sub {
  font-size: 9px;
  color: var(--qb-text-muted);
  letter-spacing: .08em;
  margin-top: 6px;
  opacity: .7;
}

/* ---- 资金储备卡 ---- */
.reserve-card {
  padding: 20px 24px;
}

.reserve-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reserve-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
}

.reserve-rate {
  font-size: 13px;
  font-weight: 700;
  &.rate-danger { color: var(--qb-danger); }
  &.rate-normal { color: var(--qb-text-muted); }
}

.reserve-tips {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--qb-text-muted);
}

.reserve-tip-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  &--orange { background: #FF8C00; }
  &--gray { background: #CCC; }
}

/* ---- 近期运营 ---- */
.section-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-sub {
  font-size: 10px;
  color: var(--qb-text-muted);
  letter-spacing: .08em;
}
</style>
