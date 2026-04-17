<template>
  <div class="qb-page">
    <!-- 页面标题 -->
    <div class="qb-page-header output-header">
      <div class="output-title-group">
        <div class="output-title-icon"><el-icon><TrendCharts /></el-icon></div>
        <div>
          <h1 class="qb-page-title">产值效能管理中心</h1>
          <p class="qb-page-subtitle">实时监控个人与小组的产值贡献、资产负载及分公司人效排名</p>
        </div>
      </div>
      <div class="view-toggle-group">
        <el-button
          :class="['view-btn', viewMode === 'personal' ? 'view-btn--active' : '']"
          :icon="User"
          @click="viewMode = 'personal'"
        >个人产值明细</el-button>
        <el-button
          :class="['view-btn', viewMode === 'group' ? 'view-btn--active' : '']"
          :icon="UserFilled"
          @click="viewMode = 'group'"
        >2人小组看板</el-button>
      </div>
    </div>

    <!-- 4 个顶部 KPI -->
    <el-row :gutter="14" v-loading="loading">
      <!-- 集团总产值 -->
      <el-col :span="6">
        <div class="output-kpi dark-kpi">
          <div class="dark-kpi-radial"></div>
          <div class="dark-kpi-label">集团实际总产值</div>
          <div class="dark-kpi-value">
            <span class="dark-kpi-cur">¥</span>{{ fmtNum(kpi.totalOutput) }}
          </div>
          <div class="dark-kpi-sub">
            <span class="pulse-dot"></span>
            实时动态统计中
          </div>
        </div>
      </el-col>

      <!-- 全员平均产值 -->
      <el-col :span="6">
        <div class="output-kpi light-kpi">
          <div class="light-kpi-label">全员平均产值</div>
          <div class="light-kpi-value">¥{{ fmtNum(kpi.avgOutput) }}</div>
          <div class="light-kpi-sub">AVERAGE PRODUCTIVITY PER HEAD</div>
        </div>
      </el-col>

      <!-- 最高个人产值 -->
      <el-col :span="6">
        <div class="output-kpi accent-kpi">
          <div class="light-kpi-label">最高个人产值</div>
          <div class="accent-kpi-value">¥{{ fmtNum(kpi.maxPersonalOutput) }}</div>
          <div class="light-kpi-sub accent-sub">
            <el-icon><Trophy /></el-icon>
            TOP PERFORMER IDENTIFIED
          </div>
        </div>
      </el-col>

      <!-- 管理资产总量 -->
      <el-col :span="6">
        <div class="output-kpi light-kpi">
          <div class="light-kpi-label">管理资产总量</div>
          <div class="light-kpi-value">{{ fmtNum(kpi.totalShops) }}<span class="light-kpi-unit">家</span></div>
          <div class="light-kpi-sub">TOTAL MANAGED PORTFOLIO</div>
        </div>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <div class="qb-card search-bar-card" style="margin-top:14px;">
      <el-input
        v-model="searchName"
        placeholder="搜索客服姓名进行产值穿透..."
        :prefix-icon="Search"
        clearable
        style="width:100%;"
        @input="handleSearch"
      />
    </div>

    <!-- ===== 个人产值明细视图 ===== -->
    <template v-if="viewMode === 'personal'">
      <div
        v-for="branch in filteredBranchGroups"
        :key="branch.branchCode"
        style="margin-top:16px;"
      >
        <!-- 分公司标题 -->
        <div class="branch-group-title">
          <el-icon style="color:var(--qb-primary);"><OfficeBuilding /></el-icon>
          <span class="branch-code-label">{{ branch.branchCode }}</span>
          <span class="branch-group-sub">· 人员产值明细</span>
        </div>

        <!-- 员工卡片网格 -->
        <el-row :gutter="14" style="margin-top:10px;">
          <el-col
            :span="8"
            v-for="emp in branch.employees"
            :key="emp.id"
            style="margin-bottom:14px;"
          >
            <div class="emp-output-card" @click="openEmpDetail(emp)">
              <div class="emp-card-header">
                <div class="emp-card-avatar" :style="{ background: emp.avatarColor }">
                  {{ emp.name?.[0] }}
                  <span v-if="emp.badge" class="emp-badge">{{ emp.badge }}</span>
                </div>
                <div class="emp-card-info">
                  <div class="emp-card-name">{{ emp.name }}</div>
                  <div class="emp-card-pos">{{ emp.position }}</div>
                </div>
                <div class="emp-card-shops">
                  <div class="emp-shops-label">负责店铺数</div>
                  <div class="emp-shops-value">{{ emp.shopCount }}<span style="font-size:11px; margin-left:2px;">家</span></div>
                </div>
              </div>
              <div class="emp-card-output">
                <div class="emp-output-label">累计接待产值</div>
                <div class="emp-output-value">¥{{ fmtNum(emp.totalOutput) }}</div>
              </div>
              <div class="emp-card-footer">
                查看详情店铺清单 <el-icon><ArrowRight /></el-icon>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </template>

    <!-- ===== 2人小组看板视图 ===== -->
    <template v-else>
      <div
        v-for="group in filteredGroups"
        :key="group.id"
        class="qb-card group-card"
        style="margin-top:16px;"
      >
        <div class="group-card-inner">
          <!-- 左：成员信息 -->
          <div class="group-left">
            <div class="group-avatars">
              <div class="group-avatar" :style="{ background: group.member1Color, zIndex: 2 }">
                {{ group.member1Name?.[0] }}
              </div>
              <div
                v-if="group.member2Name"
                class="group-avatar"
                :style="{ background: group.member2Color, marginLeft: '-10px' }"
              >
                {{ group.member2Name?.[0] }}
              </div>
            </div>
            <div class="group-names">
              {{ group.member1Name }}
              <template v-if="group.member2Name">& {{ group.member2Name }}</template>
            </div>
            <div class="group-branch">
              <span class="group-branch-code">{{ group.branchCode }}</span>
              <div class="group-branch-sub">· {{ group.groupLabel || '物联监合组挂小组' }}</div>
            </div>
          </div>

          <!-- 中：6格指标 -->
          <div class="group-metrics">
            <div class="group-metric" v-for="m in group.metrics" :key="m.label">
              <div class="gm-label">{{ m.label }}</div>
              <div class="gm-value" :style="{ color: m.danger ? 'var(--qb-danger)' : m.success ? 'var(--qb-success)' : '' }">
                {{ m.value }}
              </div>
            </div>
          </div>

          <!-- 右：KPI 产值 -->
          <div class="group-kpi">
            <div class="group-kpi-item">
              <div class="gki-label">累计接种产值</div>
              <div class="gki-value primary">¥{{ fmtNum(group.totalOutput) }}</div>
            </div>
            <div class="group-kpi-item">
              <div class="gki-label warn">当月预收产值余额</div>
              <div class="gki-input-wrap" v-if="!group.targetAmount">
                <el-input
                  v-model="group.inputTarget"
                  placeholder="输入目标金额"
                  size="small"
                  style="width:120px;"
                  @blur="setGroupTarget(group)"
                />
              </div>
              <div class="gki-value" v-else>¥{{ fmtNum(group.targetAmount) }}</div>
            </div>
            <div class="group-kpi-item">
              <div class="gki-label">当月预收备余金</div>
              <div class="gki-value danger">-¥{{ fmtNum(group.gapAmount) }}</div>
              <div class="gki-sub">已超标</div>
            </div>
            <div class="group-kpi-item">
              <div class="gki-label">当月营首达成</div>
              <div class="gki-value muted">{{ group.achieveRate || '——' }}</div>
              <div class="gki-sub">进行中营首数据</div>
            </div>
          </div>
        </div>

        <!-- 共同管理资产清单 -->
        <div class="group-shop-list" v-if="group.shops && group.shops.length > 0">
          <div class="gsl-header">
            <el-icon><List /></el-icon>
            共同管理资产清单（{{ group.shops.length }}家店铺）
            <span class="gsl-tag">DATA CERTIFIED BY BRANCH AUDIT CHAIN</span>
          </div>
          <div class="gsl-items">
            <div class="gsl-item" v-for="shop in group.shops" :key="shop.id">
              <div class="gsl-shop-icon">◈</div>
              <div class="gsl-shop-name">{{ shop.shopName }}</div>
              <div class="gsl-shop-amount">¥{{ fmtNum(shop.amount) }}</div>
              <div class="gsl-shop-meta">
                <span>🔑 {{ shop.subCount }}子账号</span>
                <span style="margin-left:8px;">📊 今日{{ shop.todayConsult }}咨询</span>
                <span style="margin-left:8px;">📅 {{ shop.days30 }}天</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup name="QingbirdOutput">
import { ref, computed, reactive, onMounted } from 'vue'
import {
  TrendCharts, User, UserFilled, Search, OfficeBuilding,
  ArrowRight, Trophy, List
} from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const viewMode = ref('personal')  // 'personal' | 'group'
const searchName = ref('')

const kpi = reactive({
  totalOutput: 65057,
  avgOutput: 2828,
  maxPersonalOutput: 2100,
  totalShops: 74
})

// mock 员工产值数据
const branchGroups = ref([
  {
    branchCode: 'B-1770628568451',
    employees: [
      { id: 1, name: 'D崔小雪', position: '客服专员', avatarColor: '#6C4EF2', badge: '⭐', shopCount: 4, totalOutput: 2100 },
      { id: 2, name: '6组【李子龙+张姿瑶】', position: '客服组', avatarColor: '#10B981', badge: '', shopCount: 6, totalOutput: 1600 },
      { id: 3, name: '朱树林', position: '客服专员', avatarColor: '#3B82F6', badge: '', shopCount: 2, totalOutput: 1600 },
      { id: 4, name: 'D尹一晨', position: '客服专员', avatarColor: '#8B5CF6', badge: '', shopCount: 1, totalOutput: 1000 },
      { id: 5, name: '张姿瑶', position: '客服专员', avatarColor: '#F59E0B', badge: '', shopCount: 0, totalOutput: 0 },
      { id: 6, name: '李子龙', position: '客服专员', avatarColor: '#EF4444', badge: '', shopCount: 0, totalOutput: 0 },
    ]
  },
  {
    branchCode: 'B-1773415060967',
    employees: [
      { id: 7, name: '王小明', position: '客服主管', avatarColor: '#0EA5E9', badge: '', shopCount: 5, totalOutput: 3200 },
      { id: 8, name: '陈丽华', position: '客服专员', avatarColor: '#D946EF', badge: '', shopCount: 3, totalOutput: 1800 },
    ]
  }
])

// mock 小组看板数据
const groups = ref([
  {
    id: 1,
    member1Name: '朱树林',
    member1Color: '#3B82F6',
    member2Name: '6组【李子龙+张姿瑶】',
    member2Color: '#10B981',
    branchCode: 'B-1770628568451',
    groupLabel: '物联监合组挂小组',
    metrics: [
      { label: '店铺总数', value: 2 },
      { label: '子账号总数', value: 0 },
      { label: '当月底薪是日', value: 0, danger: false },
      { label: '今日汇流', value: 0 },
      { label: '近7天汇流', value: 0 },
      { label: '近30天汇流', value: 0 },
    ],
    totalOutput: 1600,
    targetAmount: 0,
    inputTarget: '',
    gapAmount: 1600,
    achieveRate: '——',
    shops: [
      { id: 1, shopName: 'Q-恰恰良品女装多店...', amount: 1100, subCount: 0, todayConsult: 0, days30: 0 },
      { id: 2, shopName: 'Q-寻途科技GPS官方...', amount: 500, subCount: 0, todayConsult: 0, days30: 0 },
    ]
  },
  {
    id: 2,
    member1Name: 'D崔小雪',
    member1Color: '#6C4EF2',
    member2Name: '测试12',
    member2Color: '#F59E0B',
    branchCode: 'B-1770628568451',
    groupLabel: '物联监合组挂小组',
    metrics: [
      { label: '店铺总数', value: 3 },
      { label: '子账号总数', value: 7 },
      { label: '当月底薪是日', value: 20287, success: true },
      { label: '今日汇流', value: 0 },
      { label: '近7天汇流', value: 19932 },
      { label: '近30天汇流', value: 20287 },
    ],
    totalOutput: 1100,
    targetAmount: 0,
    inputTarget: '',
    gapAmount: 1100,
    achieveRate: '——',
    shops: [
      { id: 3, shopName: 'Q43-糖小精美妆-全包...', amount: 900, subCount: 5, todayConsult: 3, days30: 0 },
      { id: 4, shopName: 'Q43-炎森家居清洁...', amount: 200, subCount: 2, todayConsult: 0, days30: 0 },
    ]
  }
])

const fmtNum = (v) => {
  if (!v && v !== 0) return '0'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const filteredBranchGroups = computed(() => {
  if (!searchName.value) return branchGroups.value
  return branchGroups.value.map(b => ({
    ...b,
    employees: b.employees.filter(e => e.name.includes(searchName.value))
  })).filter(b => b.employees.length > 0)
})

const filteredGroups = computed(() => {
  if (!searchName.value) return groups.value
  return groups.value.filter(g =>
    g.member1Name.includes(searchName.value) ||
    (g.member2Name && g.member2Name.includes(searchName.value))
  )
})

const handleSearch = () => {}

const openEmpDetail = (emp) => {
  // TODO: 跳转或弹出员工详细产值清单
}

const setGroupTarget = (group) => {
  if (group.inputTarget) {
    group.targetAmount = parseFloat(group.inputTarget)
    group.gapAmount = Math.max(0, group.totalOutput - group.targetAmount)
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request({ url: '/qingbird/output/overview', method: 'get', hideErrorMsg: true })
    if (res?.code === 200 && res.data) {
      Object.assign(kpi, res.data.kpi || {})
      if (res.data.branchGroups) branchGroups.value = res.data.branchGroups
      if (res.data.groups) groups.value = res.data.groups
    }
  } catch { /* 使用 mock 数据 */ }
  finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
/* ---- 页头 ---- */
.output-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.output-title-group {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.output-title-icon {
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

.view-toggle-group {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.view-btn {
  border-radius: 8px;
  font-size: 13px;

  &--active {
    background: var(--qb-primary);
    color: #fff;
    border-color: var(--qb-primary);
  }
}

/* ---- KPI ---- */
.output-kpi {
  border-radius: var(--qb-radius);
  padding: 20px 22px;
  min-height: 120px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--qb-shadow-sm);
  transition: box-shadow .2s, transform .2s;

  &:hover { box-shadow: var(--qb-shadow-md); transform: translateY(-2px); }
}

/* 深色总产值卡 */
.dark-kpi {
  background: var(--qb-dark-card-bg);
}

.dark-kpi-radial {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(108,78,242,.3) 0%, transparent 70%);
  pointer-events: none;
}

.dark-kpi-label {
  font-size: 11px;
  color: rgba(255,255,255,.5);
  letter-spacing: .05em;
  margin-bottom: 10px;
}

.dark-kpi-value {
  font-size: 36px;
  font-weight: 900;
  color: #fff;
  line-height: 1;
  position: relative;
  z-index: 1;
}

.dark-kpi-cur {
  font-size: 18px;
  font-weight: 500;
  margin-right: 2px;
  opacity: .7;
}

.dark-kpi-sub {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255,255,255,.4);
  margin-top: 10px;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--qb-success);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .4; transform: scale(.8); }
}

/* 浅色 KPI */
.light-kpi {
  background: #fff;
  border: 1px solid var(--qb-border);
}

.light-kpi-label {
  font-size: 12px;
  color: var(--qb-text-muted);
  margin-bottom: 8px;
}

.light-kpi-value {
  font-size: 32px;
  font-weight: 900;
  color: var(--qb-text-primary);
  line-height: 1;
}

.light-kpi-unit {
  font-size: 14px;
  font-weight: 400;
  margin-left: 3px;
  opacity: .7;
}

.light-kpi-sub {
  font-size: 10px;
  color: var(--qb-text-muted);
  letter-spacing: .06em;
  margin-top: 8px;
  opacity: .7;
}

/* 最高产值（强调色） */
.accent-kpi {
  background: #fff;
  border: 1px solid var(--qb-primary-bg);
}

.accent-kpi-value {
  font-size: 32px;
  font-weight: 900;
  color: var(--qb-primary);
  line-height: 1;
}

.accent-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--qb-primary);
  opacity: .8;
}

/* ---- 搜索 ---- */
.search-bar-card { padding: 14px 20px; }

/* ---- 个人产值: 分公司标题 ---- */
.branch-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
}

.branch-code-label {
  color: var(--qb-primary);
  font-family: 'Courier New', monospace;
}

.branch-group-sub {
  font-size: 13px;
  color: var(--qb-text-muted);
  font-weight: 400;
}

/* ---- 员工产值卡片 ---- */
.emp-output-card {
  background: #fff;
  border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius);
  padding: 16px;
  cursor: pointer;
  transition: box-shadow .2s, transform .2s;
  box-shadow: var(--qb-shadow-sm);

  &:hover {
    box-shadow: var(--qb-shadow-md);
    transform: translateY(-2px);
  }
}

.emp-card-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
}

.emp-card-avatar {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

.emp-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  font-size: 12px;
}

.emp-card-info { flex: 1; min-width: 0; }

.emp-card-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.emp-card-pos { font-size: 11px; color: var(--qb-text-muted); margin-top: 2px; }

.emp-card-shops { text-align: right; flex-shrink: 0; }
.emp-shops-label { font-size: 10px; color: var(--qb-text-muted); margin-bottom: 2px; }
.emp-shops-value { font-size: 18px; font-weight: 800; color: var(--qb-text-primary); }

.emp-card-output { margin-bottom: 10px; }
.emp-output-label { font-size: 11px; color: var(--qb-text-muted); margin-bottom: 4px; }
.emp-output-value { font-size: 22px; font-weight: 900; color: var(--qb-text-primary); }

.emp-card-footer {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--qb-primary);
  border-top: 1px solid var(--qb-border);
  padding-top: 10px;
  margin-top: 4px;
  cursor: pointer;

  &:hover { opacity: .8; text-decoration: underline; }
}

/* ---- 小组看板 ---- */
.group-card {
  padding: 20px 22px;
}

.group-card-inner {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

/* 小组左侧 */
.group-left {
  width: 160px;
  flex-shrink: 0;
}

.group-avatars {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.group-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 2px solid #fff;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.group-names {
  font-size: 14px;
  font-weight: 700;
  color: var(--qb-text-primary);
  line-height: 1.4;
  margin-bottom: 6px;
}

.group-branch-code {
  font-size: 11px;
  color: var(--qb-primary);
  font-family: 'Courier New', monospace;
  display: block;
}

.group-branch-sub {
  font-size: 10px;
  color: var(--qb-text-muted);
  margin-top: 2px;
}

/* 小组中栏 6格指标 */
.group-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 0 16px;
  border-left: 1px solid var(--qb-border);
  border-right: 1px solid var(--qb-border);
  flex: 1;
}

.group-metric { text-align: center; }
.gm-label { font-size: 10px; color: var(--qb-text-muted); margin-bottom: 4px; }
.gm-value { font-size: 18px; font-weight: 700; color: var(--qb-text-primary); }

/* 小组右栏 KPI */
.group-kpi {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: 300px;
  flex-shrink: 0;
}

.group-kpi-item { }
.gki-label {
  font-size: 10px;
  color: var(--qb-text-muted);
  margin-bottom: 4px;
  &.warn { color: var(--qb-warning); }
}
.gki-value {
  font-size: 18px;
  font-weight: 800;
  &.primary { color: var(--qb-primary); }
  &.danger  { color: var(--qb-danger); }
  &.muted   { color: var(--qb-text-muted); }
}
.gki-input-wrap { margin-top: 4px; }
.gki-sub { font-size: 10px; color: var(--qb-text-muted); margin-top: 2px; }

/* 共同管理资产清单 */
.group-shop-list {
  margin-top: 16px;
  border-top: 1px solid var(--qb-border);
  padding-top: 14px;
}

.gsl-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
  margin-bottom: 10px;
}

.gsl-tag {
  font-size: 9px;
  color: var(--qb-text-muted);
  letter-spacing: .06em;
  margin-left: auto;
}

.gsl-items { display: flex; gap: 14px; flex-wrap: wrap; }

.gsl-item {
  flex: 1;
  min-width: 220px;
  background: #F8F9FA;
  border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius-sm);
  padding: 12px 14px;
}

.gsl-shop-icon { font-size: 16px; color: var(--qb-primary); margin-bottom: 4px; }

.gsl-shop-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gsl-shop-amount {
  font-size: 16px;
  font-weight: 800;
  color: var(--qb-primary);
  margin-bottom: 6px;
}

.gsl-shop-meta {
  font-size: 11px;
  color: var(--qb-text-muted);
}
</style>
