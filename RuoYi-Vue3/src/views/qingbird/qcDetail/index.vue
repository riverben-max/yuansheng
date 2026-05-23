<template>
  <div class="qb-page">
    <div class="qb-page-header">
      <h1 class="qb-page-title">质检明细</h1>
      <p class="qb-page-subtitle">查看各店铺的客服数据采集明细与合规状态</p>
    </div>

    <!-- 筛选栏 -->
    <div class="qb-card filter-bar">
      <el-form :inline="true" :model="queryForm" size="default">
        <el-form-item label="分公司" v-if="isAdmin">
          <el-select
            v-model="queryForm.branchId"
            placeholder="全部分公司"
            clearable
            filterable
            style="width: 220px;"
          >
            <el-option
              v-for="branch in branchOptions"
              :key="branch.branchId"
              :label="branch.branchName"
              :value="branch.branchId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="queryForm.recordDate"
            type="date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 160px;"
          />
        </el-form-item>
        <el-form-item label="预警状态">
          <el-select v-model="queryForm.isAbnormal" placeholder="全部" style="width: 120px;" clearable>
            <el-option label="全部" value="" />
            <el-option label="🟢 正常" :value="0" />
            <el-option label="🔴 异常" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchData" class="qb-btn-primary" v-hasPermi="['qingbird:spider:list']">
            搜 索
          </el-button>
          <el-button :icon="Refresh" @click="resetQuery" v-hasPermi="['qingbird:spider:list']">重 置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 数据表格 -->
    <div class="qb-card" style="margin-top: 16px;">
      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
        :row-class-name="getRowClass"
        empty-text="暂无采集数据，请确认爬虫客户端运行正常"
      >
        <el-table-column label="数据日期" prop="recordDate" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.recordDate?.slice(0,10) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="子账号" prop="subAccount" width="110" />
        <el-table-column label="咨询人数" prop="consultationCount" width="90" align="center" sortable />
        <el-table-column label="接待人数" prop="receptionCount" width="90" align="center" sortable />
        <el-table-column label="有效接待" prop="effectiveReceptionCount" width="90" align="center" sortable />
        <el-table-column label="转化率" prop="conversionRate" width="80" align="center" sortable>
          <template #default="{ row }">{{ row.conversionRate ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="首响时长(s)" prop="firstResponseTime" width="100" align="center" sortable />
        <el-table-column label="平响时长(s)" prop="avgResponseTime" width="100" align="center" sortable />
        <el-table-column label="销售额(¥)" prop="salesAmount" width="100" align="center" sortable>
          <template #default="{ row }">
            <span style="font-weight: 600;">{{ row.salesAmount ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="3分钟回复率" prop="responseRate3m" width="110" align="center" sortable>
          <template #default="{ row }">
            <span :class="(row.responseRate3m ?? 100) < 50 ? 'text-danger' : 'text-success'">
              {{ row.responseRate3m ?? '-' }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="30秒回复率" prop="responseRate30s" width="100" align="center" sortable>
          <template #default="{ row }">{{ row.responseRate30s ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="回复率" prop="replyRate" width="80" align="center" sortable>
          <template #default="{ row }">{{ row.replyRate ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="满意度" prop="satisfaction" width="80" align="center" sortable>
          <template #default="{ row }">{{ row.satisfaction ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="店铺满意度" prop="shopSatisfaction" width="100" align="center" sortable>
          <template #default="{ row }">{{ row.shopSatisfaction ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="合规状态" prop="isAbnormal" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-tag v-if="row.abnormalReason === '系统无对应客服档案'" type="warning" size="small">⚠️ 无档案</el-tag>
            <el-tag v-else-if="row.isAbnormal" type="danger" size="small">⚠️ 异常</el-tag>
            <el-tag v-else type="success" size="small">✅ 正常</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="queryForm.pageNum"
          v-model:page-size="queryForm.pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup name="QingbirdQcDetail">
import { ref, computed, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import useUserStore from '@/store/modules/user'
import { listBranchInfo } from '@/api/qingbird/branchInfo'

const userStore = useUserStore()
const isAdmin = computed(() => (userStore.roles || []).includes('admin'))
const branchOptions = ref([])
const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const queryForm = ref({
  pageNum: 1,
  pageSize: 10,
  isAbnormal: '',
  branchId: '',
  recordDate: null
})

const getRowClass = ({ row }) => {
  return row.isAbnormal ? 'row-danger' : ''
}

function isEndpointNotReadyError(error) {
  const status = error?.response?.status
  const code = error?.response?.data?.code
  const message = String(error?.response?.data?.msg || error?.message || '')
  return status === 404 || code === 404 || message.includes('404') || message.includes('接口未就绪')
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      pageNum: queryForm.value.pageNum,
      pageSize: queryForm.value.pageSize,
    }
    if (isAdmin.value && queryForm.value.branchId !== '') params.branchId = queryForm.value.branchId
    if (queryForm.value.isAbnormal !== '') params.isAbnormal = queryForm.value.isAbnormal
    if (queryForm.value.recordDate) {
      params.recordDate = queryForm.value.recordDate
    }

    const res = await request({ url: '/qingbird/spider-data/list', method: 'get', params, hideErrorCodes: [404] })
    if (res.code === 200) {
      tableData.value = res.rows || []
      total.value = res.total || 0
    }
  } catch (e) {
    if (isEndpointNotReadyError(e)) {
      tableData.value = []
      total.value = 0
      ElMessage.warning('质检明细接口暂未就绪')
      return
    }
    ElMessage.error(e?.message || '质检明细加载失败')
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  queryForm.value.branchId = ''
  queryForm.value.isAbnormal = ''
  queryForm.value.recordDate = null
  queryForm.value.pageNum = 1
  fetchData()
}

const loadBranchOptions = async () => {
  if (!isAdmin.value) return
  const res = await listBranchInfo({ pageNum: 1, pageSize: 1000 })
  if (res?.code === 200) {
    branchOptions.value = (res.rows || []).map(item => ({
      branchId: item.branchId,
      branchName: item.workplaceName
        ? `${item.workplaceName} / ${item.companyName || '未命名分公司'}`
        : `${item.companyName || '未命名分公司'} / ${item.branchId}`
    }))
  }
}

onMounted(async () => {
  await loadBranchOptions()
  fetchData()
})
</script>

<style lang="scss" scoped>
/* 青鸟全局样式已在 main.js 引入 */

.filter-bar {
  :deep(.el-form-item) { margin-bottom: 0; }
}

.text-danger { color: var(--qb-danger); font-weight: 700; }
.text-success { color: var(--qb-success); font-weight: 600; }

:deep(.row-danger) {
  background-color: #FFF8F8 !important;
  td { color: #c0392b; }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
