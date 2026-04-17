<template>
  <div class="qb-page">
    <!-- 问候语 -->
    <div class="qb-page-header">
      <div class="breadcrumb-tip">青鸟核心指挥中心 ›</div>
      <h1 class="qb-page-title">{{ greeting }}，{{ userName }}</h1>
      <p class="qb-page-subtitle">这是您今天的数据概览。所有业务主体运行正常。</p>
    </div>

    <!-- 月份选择 -->
    <div class="month-selector">
      <el-icon><Calendar /></el-icon>
      <span>{{ currentMonth }}</span>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        size="small"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        range-separator="至"
        style="width: 240px; margin-left: 12px;"
        @change="fetchData"
      />
      <el-button :icon="Refresh" size="small" circle style="margin-left:8px;" @click="fetchData" :loading="loading" />
    </div>

    <!-- 深色 KPI Banner -->
    <div class="kpi-banner" v-loading="loading" element-loading-background="rgba(18,18,30,0.8)">
      <div class="kpi-banner-left">
        <div class="kpi-brand-icon">⚡</div>
        <div>
          <div class="kpi-brand-name">Q43-锦鲤电商 · 控制台</div>
          <div class="kpi-brand-sub">REAL-TIME GLOBAL OPERATIONS</div>
        </div>
      </div>
      <div class="kpi-banner-right">
        <div class="kpi-globe">🌐</div>
        <div class="kpi-total-label">全集团总产品总量</div>
        <div class="kpi-total-value">{{ kpi.totalProductCount ?? 0 }}</div>
      </div>

      <div class="kpi-metrics">
        <div class="kpi-metric">
          <div class="kpi-metric-label">✓ 今日销售额</div>
          <div class="kpi-metric-value">
            <span class="kpi-unit">¥</span>{{ formatAmount(kpi.todaySalesAmount) }}
          </div>
        </div>
        <div class="kpi-metric-divider"></div>
        <div class="kpi-metric">
          <div class="kpi-metric-label">全员在职数</div>
          <div class="kpi-metric-value">
            {{ kpi.activeEmployeeCount ?? 0 }} <span class="kpi-unit">员</span>
          </div>
        </div>
        <div class="kpi-metric-divider"></div>
        <div class="kpi-metric">
          <div class="kpi-metric-label">运营店铺</div>
          <div class="kpi-metric-value">
            {{ kpi.activeShopCount ?? 0 }} <span class="kpi-unit">家</span>
          </div>
        </div>
      </div>

      <div class="kpi-banner-footer">
        <span class="kpi-refresh" @click="fetchData">
          <el-icon><Refresh /></el-icon> 最后刷新：{{ lastRefreshTime }}
        </span>
        <span class="kpi-safety">数据安全监控</span>
      </div>
    </div>

    <!-- 业务规模 + 合规预警 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <!-- 业务规模与咨询概况 -->
      <el-col :span="12">
        <div class="qb-card" v-loading="loading">
          <div class="section-header">
            <div class="section-title">
              <el-icon style="color: var(--qb-primary);"><DataLine /></el-icon>
              业务规模与咨询概况
            </div>
            <div class="section-sub">GLOBAL SCALE & TRAFFIC ANALYTICS</div>
          </div>
          <el-row :gutter="12" style="margin-top: 16px;">
            <el-col :span="12" v-for="m in scaleMetrics" :key="m.label">
              <div class="mini-metric-card">
                <div class="mini-metric-icon">{{ m.icon }}</div>
                <div class="mini-metric-label">{{ m.label }}</div>
                <div class="mini-metric-value" :style="{ color: m.color || 'var(--qb-text-primary)' }">
                  {{ m.value }} <span class="mini-metric-unit">{{ m.unit }}</span>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-col>

      <!-- 实时异动与合规预警 -->
      <el-col :span="12">
        <div class="qb-card" v-loading="loading">
          <div class="section-header">
            <div class="section-title">
              <el-icon style="color: var(--qb-danger);"><WarningFilled /></el-icon>
              实时异动与合规预警
            </div>
            <div class="section-sub">REAL-TIME COMPLIANCE MONITORING</div>
          </div>
          <el-row :gutter="12" style="margin-top: 16px;">
            <el-col :span="12" v-for="m in complianceMetrics" :key="m.label">
              <div class="mini-metric-card" :class="{ 'danger-card': m.danger, 'success-card': m.success }">
                <div class="mini-metric-label">{{ m.label }}</div>
                <div class="mini-metric-value"
                  :style="{ color: m.danger ? 'var(--qb-danger)' : m.success ? 'var(--qb-success)' : 'var(--qb-text-primary)' }">
                  <span class="mini-metric-unit" v-if="m.prefix">{{ m.prefix }}</span>{{ m.value }}
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-col>
    </el-row>

    <!-- 近7天趋势图 -->
    <div class="qb-card" style="margin-top: 16px;" v-if="kpi.trendData && kpi.trendData.length > 0">
      <div class="section-title" style="margin-bottom:16px;">
        <el-icon style="color: var(--qb-info);"><TrendCharts /></el-icon>
        近7天采集趋势
      </div>
      <el-table :data="kpi.trendData" size="small" stripe>
        <el-table-column prop="date" label="日期" width="100" />
        <el-table-column prop="consultation" label="接待总量" align="center" />
        <el-table-column prop="abnormalCount" label="异常条数" align="center">
          <template #default="{ row }">
            <el-tag :type="row.abnormalCount > 0 ? 'danger' : 'success'" size="small">
              {{ row.abnormalCount }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 最近预警列表 -->
    <div class="qb-card" style="margin-top: 16px;" v-if="kpi.alertList && kpi.alertList.length > 0">
      <div class="section-title" style="margin-bottom:16px;">
        <el-icon style="color: var(--qb-danger);"><Warning /></el-icon>
        最近异常预警
      </div>
      <el-table :data="kpi.alertList" size="small">
        <el-table-column prop="shopId" label="店铺ID" width="80" align="center" />
        <el-table-column prop="responseRate" label="3分钟响应率" align="center">
          <template #default="{ row }">
            <span style="color:var(--qb-danger); font-weight:700;">{{ row.responseRate ?? '-' }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="consultationCount" label="接待人数" align="center" />
        <el-table-column prop="salesAmount" label="销售额(¥)" align="center" />
        <el-table-column prop="recordDate" label="记录日期" width="120">
          <template #default="{ row }">{{ row.recordDate?.substring(0, 10) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup name="QingbirdDashboard">
import { ref, computed, reactive, onMounted } from 'vue'
import { Calendar, DataLine, WarningFilled, Refresh, TrendCharts, Warning } from '@element-plus/icons-vue'
import useUserStore from '@/store/modules/user'
import request from '@/utils/request'

const userStore = useUserStore()
const userName = computed(() => userStore.name || 'admin')
const loading = ref(false)
const lastRefreshTime = ref('--')

const now = new Date()
const h = now.getHours()
const greeting = h < 12 ? '早安' : h < 18 ? '下午好' : '晚上好'
const currentMonth = `${now.getFullYear()}年${String(now.getMonth() + 1).padStart(2, '0')}月`
const dateRange = ref([
  new Date(now.getFullYear(), now.getMonth(), 1).toISOString().substring(0, 10),
  now.toISOString().substring(0, 10)
])

const kpi = reactive({
  todaySalesAmount: 0, activeEmployeeCount: 0, activeShopCount: 0, totalProductCount: 0,
  todayConsultation: 0, todayOperatorCount: 0, monthConsultation: 0,
  todayAbnormalCount: 0, todayNormalCount: 0, todayHighRiskCount: 0, monthAbnormalCount: 0,
  trendData: [], alertList: []
})

const formatAmount = (val) => {
  if (!val && val !== 0) return '0'
  return Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

const scaleMetrics = computed(() => [
  { icon: '🏪', label: '运营平台店铺',  value: kpi.activeShopCount, unit: '家', color: 'var(--qb-primary)' },
  { icon: '👤', label: '今日操作员数',  value: kpi.todayOperatorCount, unit: '人', color: 'var(--qb-primary)' },
  { icon: '💬', label: '今日接待总量',  value: kpi.todayConsultation, unit: '条' },
  { icon: '📈', label: '近30天接待',    value: kpi.monthConsultation, unit: '条' },
])

const complianceMetrics = computed(() => [
  { label: '↑ 今日新增异常',   value: kpi.todayAbnormalCount, prefix: '',  danger: kpi.todayAbnormalCount > 0 },
  { label: '✔ 今日正常达标',   value: kpi.todayNormalCount,   prefix: '',  success: true },
  { label: '⚡ 今日高危积分',  value: kpi.todayHighRiskCount, prefix: '',  danger: kpi.todayHighRiskCount > 0 },
  { label: '📅 本月累计异常',  value: kpi.monthAbnormalCount, prefix: '',  danger: kpi.monthAbnormalCount > 0 },
])

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request({ url: '/qingbird/dashboard/overview', method: 'get' })
    if (res.code === 200) {
      Object.assign(kpi, res.data)
      const t = new Date()
      lastRefreshTime.value = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}:${String(t.getSeconds()).padStart(2,'0')}`
    }
  } catch (e) {
    console.error('Dashboard API error', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.breadcrumb-tip { font-size: 12px; color: var(--qb-primary); margin-bottom: 4px; }

.month-selector {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--qb-text-primary);
}

/* 深色 KPI 卡片 */
.kpi-banner {
  background: var(--qb-dark-card-bg);
  border-radius: var(--qb-radius);
  padding: 24px 28px;
  color: #fff;
  position: relative;
  overflow: hidden;
  min-height: 200px;
}

.kpi-banner-left { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }

.kpi-brand-icon {
  width: 40px; height: 40px;
  background: rgba(108, 78, 242, 0.4);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}

.kpi-brand-name { font-size: 18px; font-weight: 700; }
.kpi-brand-sub { font-size: 11px; opacity: 0.5; letter-spacing: .1em; margin-top: 3px; }

.kpi-banner-right {
  position: absolute; right: 28px; top: 24px; text-align: right;
}

.kpi-globe { font-size: 80px; opacity: .1; position: absolute; right: -10px; top: -20px; }
.kpi-total-label { font-size: 11px; opacity: .5; letter-spacing: .05em; }
.kpi-total-value { font-size: 28px; font-weight: 800; color: var(--qb-primary); }

.kpi-metrics { display: flex; align-items: center; margin-bottom: 20px; }
.kpi-metric { flex: 1; padding-right: 32px; }
.kpi-metric-label { font-size: 12px; opacity: .6; margin-bottom: 6px; }
.kpi-metric-value { font-size: 36px; font-weight: 800; line-height: 1; }
.kpi-unit { font-size: 18px; font-weight: 400; opacity: .7; }
.kpi-metric-divider { width: 1px; height: 50px; background: rgba(255,255,255,.12); margin-right: 32px; }

.kpi-banner-footer {
  display: flex; align-items: center; gap: 16px;
  font-size: 12px; opacity: .5;
  border-top: 1px solid rgba(255,255,255,.1); padding-top: 12px;
}
.kpi-refresh, .kpi-safety {
  display: flex; align-items: center; gap: 4px; cursor: pointer;
  &:hover { opacity: 1; }
}

/* 功能区块 */
.section-header { margin-bottom: 4px; }
.section-title {
  font-size: 15px; font-weight: 700; color: var(--qb-text-primary);
  display: flex; align-items: center; gap: 6px;
}
.section-sub { font-size: 10px; color: var(--qb-text-muted); letter-spacing: .08em; margin-top: 3px; }

/* 迷你指标卡 */
.mini-metric-card {
  background: #F8F9FA; border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius-sm); padding: 14px; margin-bottom: 12px;
  transition: box-shadow .2s;
  &:hover { box-shadow: var(--qb-shadow-md); }
  &.danger-card { background: #FFF5F5; border-color: #FFD6D6; }
  &.success-card { background: #F0FFF4; border-color: #B7EBC3; }
}
.mini-metric-icon { font-size: 20px; margin-bottom: 6px; }
.mini-metric-label { font-size: 11px; color: var(--qb-text-muted); margin-bottom: 4px; }
.mini-metric-value { font-size: 22px; font-weight: 700; }
.mini-metric-unit { font-size: 12px; font-weight: 400; opacity: .7; }
</style>
