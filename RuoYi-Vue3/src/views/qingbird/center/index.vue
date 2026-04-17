<template>
  <div class="qb-page">
    <!-- 页面标题 + 日期 -->
    <div class="qb-page-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
      <div>
        <h1 class="qb-page-title">集团中心</h1>
        <p class="qb-page-subtitle">发布全集团核心公告与最新业务动态</p>
      </div>
      <div class="date-badge">
        <el-icon><Calendar /></el-icon>
        {{ today }}
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左侧主区域 -->
      <el-col :span="16">
        <!-- 公告大卡片（紫色渐变） -->
        <div class="announcement-card">
          <div class="ann-tags">
            <span class="ann-tag urgent">重要</span>
            <span class="ann-tag notice">重要公告</span>
          </div>
          <h2 class="ann-title">关于罚款核对及费用结算时间调整公告</h2>
          <p class="ann-body">
            一、2026年3月1日前产生的罚款，请于3月5日前与雷神完成核对。<br>
            二、代理费用核对及结算时间调整为3月15日前对账打款。调整原因：部分客户（如2026年2月27日到期客户）需延期9天，与客户核对咨询量及款项工作需至3月8日方可完成对账结，因此代理费用顺延至3...
          </p>
          <div class="ann-footer">
            <div class="ann-publisher">
              <el-icon><OfficeBuilding /></el-icon>
              集团行政部总部办公室
            </div>
            <el-button class="qb-btn-primary" size="default">查看详情全文 ›</el-button>
          </div>
          <!-- 装饰图形 -->
          <div class="ann-decoration">✦</div>
        </div>

        <!-- 底部统计行 -->
        <el-row :gutter="16" style="margin-top: 16px;">
          <el-col :span="12">
            <div class="stat-mini-card">
              <el-icon class="stat-icon"><ChatDotRound /></el-icon>
              <div>
                <div class="stat-label">今日内部交流</div>
                <div class="stat-value">124 条</div>
              </div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="stat-mini-card">
              <el-icon class="stat-icon" style="color: var(--qb-warning);"><Bell /></el-icon>
              <div>
                <div class="stat-label">重要待办通知</div>
                <div class="stat-value">3 项</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-col>

      <!-- 右侧消息动态 -->
      <el-col :span="8">
        <div class="qb-card" style="height: 100%;">
          <div class="news-header">
            <el-icon><BellFilled /></el-icon> 最新消息动态
          </div>
          <div class="news-list">
            <div v-for="(item, i) in newsList" :key="i" class="news-item">
              <div class="news-meta">
                <span :class="['news-type', item.type]">{{ item.typeLabel }}</span>
                <span class="news-date">{{ item.date }}</span>
              </div>
              <div class="news-title">{{ item.title }}</div>
              <div class="news-source">{{ item.source }}</div>
            </div>
          </div>
          <div class="news-more">加载更多历史消息</div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup name="QingbirdCenter">
import { ref, computed } from 'vue'
import { Calendar, OfficeBuilding, ChatDotRound, Bell, BellFilled } from '@element-plus/icons-vue'

const now = new Date()
const today = computed(() => `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`)

const newsList = ref([
  {
    typeLabel: '系统', type: 'type-system', date: '2026-03-01',
    title: '青鸟集团-企业级管理系统V1版本',
    source: '青鸟集团-企业级管理系统V1版本'
  },
  {
    typeLabel: '重要', type: 'type-urgent', date: '2026-03-01',
    title: '青鸟集团-冷店铺预警',
    source: '店铺消息维持待处理超过3天为冷D消号导致错错错错'
  },
])
</script>

<style lang="scss" scoped>
/* 青鸟全局样式已在 main.js 引入 */

/* 日期徽章 */
.date-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--qb-text-secondary);
  background: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  box-shadow: var(--qb-shadow);
}

/* 公告大卡 */
.announcement-card {
  background: linear-gradient(135deg, #6C4EF2 0%, #4B8EF5 100%);
  border-radius: var(--qb-radius);
  padding: 28px;
  color: #fff;
  position: relative;
  overflow: hidden;
  min-height: 280px;
}

.ann-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.ann-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 4px;
  letter-spacing: 0.05em;

  &.urgent { background: rgba(255,255,255,0.25); }
  &.notice { background: rgba(255,255,255,0.15); }
}

.ann-title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 14px;
}

.ann-body {
  font-size: 13px;
  line-height: 1.8;
  opacity: 0.9;
  margin-bottom: 20px;
}

.ann-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ann-publisher {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  opacity: 0.9;
  background: rgba(255,255,255,0.2);
  padding: 6px 12px;
  border-radius: 20px;
}

.ann-decoration {
  position: absolute;
  top: -20px;
  right: 30px;
  font-size: 160px;
  opacity: 0.08;
  line-height: 1;
  pointer-events: none;
  transform: rotate(15deg);
}

/* 统计迷你卡片 */
.stat-mini-card {
  background: #fff;
  border-radius: var(--qb-radius);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--qb-shadow);

  .stat-icon {
    font-size: 32px;
    color: var(--qb-primary);
  }

  .stat-label {
    font-size: 13px;
    color: var(--qb-text-muted);
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 22px;
    font-weight: 700;
    color: var(--qb-text-primary);
  }
}

/* 消息动态 */
.news-header {
  font-size: 15px;
  font-weight: 700;
  color: var(--qb-text-primary);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.news-list { display: flex; flex-direction: column; gap: 12px; }

.news-item {
  padding: 12px;
  border-radius: var(--qb-radius-sm);
  border: 1px solid var(--qb-border);
  transition: box-shadow 0.2s;
  cursor: pointer;
  &:hover { box-shadow: var(--qb-shadow-md); }
}

.news-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.news-type {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  &.type-system { background: #e8f4ff; color: var(--qb-info); }
  &.type-urgent { background: #fff0f0; color: var(--qb-danger); }
}

.news-date { font-size: 11px; color: var(--qb-text-muted); }
.news-title { font-size: 13px; font-weight: 600; color: var(--qb-text-primary); margin-bottom: 4px; }
.news-source { font-size: 11px; color: var(--qb-text-muted); }

.news-more {
  text-align: center;
  margin-top: 16px;
  color: var(--qb-primary);
  font-size: 13px;
  cursor: pointer;
  &:hover { text-decoration: underline; }
}
</style>
