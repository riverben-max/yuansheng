<template>
  <div class="qb-layout">
    <!-- 侧边栏 -->
    <aside class="qb-sidebar">
      <!-- Logo 区域 -->
      <div class="qb-logo">
        <div class="qb-logo-icon">
          <img src="@/assets/logo/logo1.png" alt="logo" class="qb-logo-img" />
        </div>
        <div class="qb-logo-name">远盛管理系统</div>
      </div>

      <!-- 导航菜单 -->
      <nav class="qb-nav">
        <div class="qb-nav-group-label">系统功能导航</div>
        <router-link
          v-for="item in visibleMenuItems"
          :key="item.path"
          :to="item.path"
          class="qb-nav-item"
          :class="{ 'is-active': isActive(item) }"
        >
          <el-icon class="qb-nav-icon"><component :is="item.icon" /></el-icon>
          <span class="qb-nav-label">{{ item.label }}</span>
          <el-icon v-if="isActive(item)" class="qb-nav-arrow"><ArrowRight /></el-icon>
        </router-link>
      </nav>

      <!-- 底部用户信息 -->
      <div class="qb-sidebar-user">
        <div class="qb-user-avatar">{{ userInitial }}</div>
        <div class="qb-user-info">
          <div class="qb-user-name">{{ userName }}</div>
          <div class="qb-user-role">{{ userDept }}</div>
        </div>
        <div class="qb-user-actions" style="margin-left: auto;">
          <div class="qb-action-icon" title="底层系统管理 (仅管理员)" v-hasRole="['admin']" @click="goToSystem">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="qb-action-icon logout-icon" title="安全退出系统" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="qb-main-wrapper">
      <!-- 顶部导航栏 -->
      <header class="qb-topbar">
        <div class="qb-topbar-left">
          <el-icon style="color: #6C4EF2; margin-right: 6px;"><Location /></el-icon>
          <span class="qb-topbar-mode">分公司数据隔离模式 · {{ branchCode }}</span>
        </div>
        <div class="qb-topbar-right">
          <div class="qb-clock">
            <el-icon><Clock /></el-icon>
            <span class="qb-clock-time">{{ currentTime }}</span>
          </div>
          <div class="qb-date">
            北京时间 (UTC+8) · {{ currentDate }} 星期{{ weekDay }}
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="qb-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import useUserStore from '@/store/modules/user'
import {
  OfficeBuilding, DataBoard, Connection, Files, User,
  Money, Shop, TrendCharts, Headset, CircleCheck,
  List, CreditCard, Tickets, PieChart,
  ArrowRight, Location, Clock, Setting, SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 用户信息
const userName = computed(() => userStore.name || 'Q43主管')
const userDept = computed(() => {
  const roles = userStore.roles || []
  if (roles.includes('admin')) return '超级管理员'
  if (roles.includes('manager')) return '分公司主管'
  if (roles.includes('finance')) return '财务管理员'
  if (roles.includes('employee')) return '普通员工'
  return '普通用户'
})
const userInitial = computed(() => (userStore.name || 'Q')[0].toUpperCase())
const branchCode = computed(() => 'B-1773208272961')

// 菜单配置
const menuItems = [
  { path: '/qingbird/center',     label: '集团中心',       icon: OfficeBuilding },
  { path: '/qingbird/dashboard',  label: '控制台',         icon: DataBoard },
  // { path: '/qingbird/branch-data',label: '分公司数据中心', icon: DataBoard },
  { path: '/qingbird/branch',     label: '分公司管理',     icon: Connection },
  { path: '/qingbird/system/user', label: '用户管理',       icon: User, roles: ['admin'], activePaths: ['/qingbird/system/user-auth'] },
  { path: '/qingbird/docs',       label: '云文档',         icon: Files },
  { path: '/qingbird/salary',     label: '薪资预览',   icon: Money },
  { path: '/qingbird/shop',       label: '店铺管理',   icon: Shop },
  { path: '/qingbird/output',     label: '产值管理',   icon: TrendCharts },
  { path: '/qingbird/seat',       label: '客服坐席',   icon: Headset },
  { path: '/qingbird/qc',         label: '店铺质检',   icon: CircleCheck },
  { path: '/qingbird/qc-detail',  label: '质检明细',   icon: List },
  { path: '/qingbird/settlement', label: '结算管理',   icon: CreditCard },
  { path: '/qingbird/bonus',      label: '绩费明细',   icon: Tickets },
  { path: '/qingbird/finance',    label: '财务总览',   icon: PieChart },
]

const visibleMenuItems = computed(() => {
  const roles = userStore.roles || []
  return menuItems.filter(item => {
    if (!item.roles || item.roles.length === 0) return true
    return roles.includes('admin') || item.roles.some(role => roles.includes(role))
  })
})

const isActive = (item) => {
  const path = typeof item === 'string' ? item : item.path
  const activePaths = typeof item === 'string' ? [] : item.activePaths || []
  return route.path === path || route.path.startsWith(path + '/') || activePaths.some(activePath => route.path.startsWith(activePath))
}

// 实时时钟
const currentTime = ref('')
const currentDate = ref('')
const weekDay = ref('')
const weekDays = ['日', '一', '二', '三', '四', '五', '六']
let timer = null

const updateClock = () => {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${h}:${m}:${s}`
  currentDate.value = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`
  weekDay.value = weekDays[now.getDay()]
}

onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
})

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm('确定要安全退出系统吗？', '退出提示', {
    confirmButtonText: '确认退出',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    userStore.logOut().then(() => {
      router.push('/login')
    })
  })
}

// 切回原版若依底层管理系统
const goToSystem = () => {
  router.push('/system/user')
}
</script>

<style lang="scss" scoped>
/* 青鸟全局样式已在 main.js 引入 */

.qb-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ===== 侧边栏 ===== */
.qb-sidebar {
  width: var(--qb-sidebar-width);
  background: var(--qb-sidebar-bg);
  border-right: 1px solid var(--qb-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

/* Logo */
.qb-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px 14px 16px;
  border-bottom: 1px solid var(--qb-border);
  flex-shrink: 0;
}

.qb-logo-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.qb-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain; /* Ensure it scales without distortion */
  border-radius: 6px;
}

.qb-logo-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--qb-text-primary);
  text-align: center;
  letter-spacing: 1px;
  white-space: nowrap;
}

/* 导航 */
.qb-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px;

  &::-webkit-scrollbar { width: 0; }
}

.qb-nav-group-label {
  font-size: 10px;
  color: var(--qb-text-muted);
  letter-spacing: 0.05em;
  padding: 8px 8px 6px;
  text-transform: uppercase;
}

.qb-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  height: var(--qb-sidebar-item-height);
  border-radius: var(--qb-radius-sm);
  color: var(--qb-text-secondary);
  text-decoration: none;
  font-size: 13px;
  transition: all 0.15s ease;
  margin-bottom: 2px;
  position: relative;
  white-space: nowrap;
  overflow: hidden;

  &:hover {
    background: var(--qb-sidebar-hover-bg);
    color: var(--qb-text-primary);
  }

  &.is-active {
    background: var(--qb-sidebar-active-bg);
    color: var(--qb-sidebar-active-text);
    font-weight: 600;
  }
}

.qb-nav-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.qb-nav-label {
  flex: 1;
}

.qb-nav-arrow {
  font-size: 12px;
  opacity: 0.7;
}

/* 底部用户卡片 */
.qb-sidebar-user {
  padding: 12px;
  border-top: 1px solid var(--qb-border);
  flex-shrink: 0;
}

.qb-user-avatar {
  width: 36px;
  height: 36px;
  background: var(--qb-primary);
  border-radius: 50%;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.qb-user-info {
  margin-bottom: 8px;
}

.qb-user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
}

.qb-user-role {
  font-size: 11px;
  color: var(--qb-text-muted);
}

.qb-user-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.qb-action-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--qb-text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #F1F5F9;
    color: var(--qb-primary);
  }

  &.logout-icon:hover {
    background: #FEF2F2;
    color: var(--qb-danger);
  }
}

/* ===== 主内容区 ===== */
.qb-main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶栏 */
.qb-topbar {
  height: var(--qb-topbar-height);
  background: var(--qb-topbar-bg);
  border-bottom: 1px solid var(--qb-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.qb-topbar-left {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: var(--qb-text-secondary);
}

.qb-topbar-mode {
  font-size: 13px;
  color: var(--qb-text-secondary);
}

.qb-topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.qb-clock {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 18px;
  font-weight: 700;
  color: var(--qb-primary);
  font-variant-numeric: tabular-nums;
}

.qb-clock-time {
  letter-spacing: 0.05em;
}

.qb-date {
  font-size: 12px;
  color: var(--qb-text-muted);
}

/* 内容区 */
.qb-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: var(--qb-bg);
}
</style>
