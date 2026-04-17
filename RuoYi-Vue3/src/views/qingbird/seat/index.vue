<template>
  <div class="qb-page">
    <!-- 页面标题 -->
    <div class="qb-page-header emp-header">
      <div class="emp-title-group">
        <div class="emp-title-icon">
          <el-icon><Avatar /></el-icon>
        </div>
        <div>
          <h1 class="qb-page-title">客​服​坐​席​花​名​册</h1>
          <p class="qb-page-subtitle">所属分公司信息维护域 · {{ branchScopeLabel }}</p>
        </div>
      </div>
      <div class="emp-header-actions">
        <el-button v-if="isAdmin" :icon="Plus" @click="goBranchPage" style="border-radius:8px;">
          新增分公司
        </el-button>
        <el-button :icon="Download" @click="handleExport" style="border-radius:8px;">
          导出 CSV
        </el-button>
        <el-button class="qb-btn-primary" :icon="Plus" @click="openAddDialog">
          录入客服坐席
        </el-button>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="qb-card search-bar">
      <el-select
        v-if="isAdmin"
        v-model="selectedBranchCode"
        placeholder="所属分公司：全部"
        clearable
        style="width: 220px; margin-right: 12px;"
        @change="handleBranchChange"
      >
        <el-option
          v-for="branch in branchOptions"
          :key="branch.branchCode"
          :label="branch.branchName"
          :value="branch.branchCode"
        />
      </el-select>
      <el-input
        v-model="queryForm.name"
        placeholder="搜索姓名、登录账号..."
        :prefix-icon="Search"
        clearable
        @keyup.enter="fetchData"
        style="width: 320px;"
      />
      <el-select
        v-model="queryForm.department"
        placeholder="部门：全部门"
        clearable
        style="width: 140px; margin-left: 12px;"
        @change="fetchData"
      >
        <el-option label="全部门" value="" />
        <el-option label="管理层" value="管理层" />
        <el-option label="客服组" value="客服组" />
        <el-option label="运营组" value="运营组" />
      </el-select>
      <el-select
        v-model="queryForm.status"
        placeholder="在职状态"
        clearable
        style="width: 120px; margin-left: 8px;"
        @change="fetchData"
      >
        <el-option label="在职" value="0" />
        <el-option label="离职" value="1" />
      </el-select>
      <el-button class="qb-btn-primary" :icon="Search" @click="fetchData" style="margin-left: 8px;">
        搜 索
      </el-button>
    </div>

    <!-- 员工表格 -->
    <div class="qb-card" style="margin-top: 14px;">
      <el-table
        :data="tableData"
        v-loading="loading"
        style="width: 100%"
        empty-text="暂无数据，点击「录入客服坐席」添加"
      >
        <!-- 员工基本信息 -->
        <el-table-column label="坐席基本信息" min-width="190">
          <template #default="{ row }">
            <div class="emp-info-cell">
              <div class="emp-avatar" :style="{ background: row.avatarColor || '#6C4EF2' }">
                {{ row.name?.[0] }}
              </div>
              <div>
                <div class="emp-name">{{ row.name }} <span class="login-acc" v-if="row.loginAccount">(@{{ row.loginAccount }})</span></div>
                <div class="emp-position">{{ row.department }}·{{ row.position }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <!-- 身份与联系 -->
        <el-table-column label="身份与联系" min-width="200">
          <template #default="{ row }">
            <div class="contact-item" v-if="row.idCard">
              <el-icon><Postcard /></el-icon> {{ row.idCard }}
            </div>
            <div class="contact-item" v-if="row.mobile">
              <el-icon><Phone /></el-icon> {{ row.mobile }}
            </div>
            <div class="contact-item" v-if="row.address" style="color: #999; font-size: 11px;">
              <el-icon><Location /></el-icon> {{ row.address }}
            </div>
          </template>
        </el-table-column>

        <!-- 登录跟踪 -->
        <el-table-column label="登录跟踪" min-width="170">
          <template #default="{ row }">
            <div v-if="row.loginAccount">
              <el-tooltip :content="`上次登录IP: ${row.lastLoginIp || '未知'} (点击查看完整日志)`" placement="top" effect="light">
                <div class="login-track">
                  <el-icon><Monitor /></el-icon> 
                  {{ row.lastLoginTime ? row.lastLoginTime : '从未使用此账号登录' }}
                </div>
              </el-tooltip>
              <div style="margin-top: 4px;">
                 <el-button size="small" type="primary" link @click="openLoginLogs(row)">
                   <el-icon><Tickets /></el-icon> 查看完整上线/下线日志
                 </el-button>
              </div>
            </div>
             <div v-else class="cell-muted">
               无登录账号 
               <el-tooltip content="历史测试数据或未绑定账号，请新建坐席以体验">
                 <el-icon style="vertical-align: middle; margin-left:2px;"><InfoFilled /></el-icon>
               </el-tooltip>
             </div>
          </template>
        </el-table-column>

        <!-- 实习与入职日期 -->
        <el-table-column label="实习与入职日期" width="130">
          <template #default="{ row }">
            <div class="date-pair">
              <span class="date-label">实习</span>
              <span class="cell-muted">{{ row.internDate ? formatDate(row.internDate) : '——' }}</span>
            </div>
            <div class="date-pair" style="margin-top: 4px;">
              <span class="date-label hire">正式入职</span>
              <span class="date-value">{{ row.hireDate ? formatDate(row.hireDate) : '——' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 薪资情况 -->
        <el-table-column label="薪资概况" width="120" align="center">
          <template #default="{ row }">
            <div class="salary-cell">
              <span class="salary-val">¥{{ row.salaryBase ?? '0' }}</span>
              <div class="salary-sub">基本底薪</div>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-popconfirm
              title="确定删除该客服记录吗？"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
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

    <!-- 录入/编辑员工 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑坐席信息' : '录入新客服坐席'"
      width="680px"
      :close-on-click-modal="false"
    >
      <div v-if="!isEdit" class="qb-alert-info">
        <el-icon><InfoFilled /></el-icon>
        <span>录入后，系统将自动分配登录账号，初始密码为：<strong>123456</strong></span>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="24" v-if="isAdmin">
            <el-form-item label="所属分公司" prop="branchCode">
              <el-select v-model="form.branchCode" placeholder="请选择员工所属分公司" style="width: 100%;" filterable>
                <el-option
                  v-for="branch in branchOptions"
                  :key="branch.branchCode"
                  :label="branch.branchName"
                  :value="branch.branchCode"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="登录账号" prop="loginAccount">
              <el-input v-model="form.loginAccount" placeholder="系统唯一,如: zhangsan_kf" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="真实姓名" prop="name">
              <el-input v-model="form.name" placeholder="请输入姓名或备注名" />
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="联系电话" prop="mobile">
              <el-input v-model="form.mobile" placeholder="手机号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="身份证号">
              <el-input v-model="form.idCard" placeholder="18位身份证号码" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-form-item label="联系地址">
              <el-input v-model="form.address" placeholder="现居或户籍地址" />
            </el-form-item>
          </el-col>

          <el-divider border-style="dashed"><span style="color:#aaa;font-size:12px;">以下为公司内部档案补充项</span></el-divider>

          <el-col :span="12">
            <el-form-item label="岗位">
              <el-input v-model="form.position" placeholder="如：客服主管" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="部门">
              <el-select v-model="form.department" style="width:100%;" allow-create filterable>
                <el-option label="客服一部" value="客服一部" />
                <el-option label="客服二部" value="客服二部" />
                <el-option label="管理层" value="管理层" />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="实习始期">
              <el-date-picker v-model="form.internDate" type="date" value-format="YYYY-MM-DD" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="正式入职">
              <el-date-picker v-model="form.hireDate" type="date" value-format="YYYY-MM-DD" style="width:100%;" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="基本工资(¥)">
              <el-input-number v-model="form.salaryBase" :min="0" :precision="2" style="width:100%; controls-position: right;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="在职状态">
              <el-select v-model="form.status" style="width:100%;">
                <el-option value="0" label="在职" />
                <el-option value="1" label="离职" />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12" v-if="form.status === '1'">
            <el-form-item label="离职日期">
              <el-date-picker v-model="form.resignDate" type="date" value-format="YYYY-MM-DD" style="width:100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="可选备注 / 质检明细及云文档权限调整说明等" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button class="qb-btn-primary" @click="handleSubmit">确 认 提 交</el-button>
      </template>
    </el-dialog>

    <!-- 详细登录日志 Dialog -->
    <el-dialog v-model="dialogLogs" :title="`[ ${currentLogAccount} ] 的详细打卡上线流水`" width="700px">
      <el-table :data="logData" v-loading="logLoading" height="400">
        <el-table-column prop="loginTime" label="操作时间" width="160" />
        <el-table-column prop="status" label="动作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.msg === '退出成功' ? 'info' : 'success'" size="small">
              {{ row.msg === '退出成功' ? '下线/登出' : '上线/登录' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ipaddr" label="操作 IP 地址" width="130" />
        <el-table-column prop="browser" label="终端与浏览器" min-width="160">
           <template #default="{ row }">
             {{ row.os }} - {{ row.browser }}
           </template>
        </el-table-column>
        <el-table-column prop="msg" label="系统回执" />
      </el-table>
      <div class="pagination-wrap">
         <el-pagination
           v-model:current-page="logQuery.pageNum"
           v-model:page-size="logQuery.pageSize"
           layout="prev, pager, next"
           :total="logTotal"
           @change="fetchLogs"
         />
      </div>
    </el-dialog>
  </div>
</template>

<script setup name="QingbirdSeat">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus, Download, Avatar, Phone, Postcard, Location, Monitor, InfoFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'
import useUserStore from '@/store/modules/user'
import { listBranchInfo, getMyBranchInfo } from '@/api/qingbird/branchInfo'

const DEFAULT_BRANCH_CODE = 'B-1773208272961'
const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => (userStore.roles || []).includes('admin'))
const branchOptions = ref([])
const selectedBranchCode = ref('')
const branchCode = computed(() => {
  if (isAdmin.value) return selectedBranchCode.value || ''
  return selectedBranchCode.value || DEFAULT_BRANCH_CODE
})
const branchScopeLabel = computed(() => {
  if (isAdmin.value) return selectedBranchCode.value || '全部分公司'
  return branchCode.value
})
const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const queryForm = reactive({
  pageNum: 1, pageSize: 10,
  name: '', department: '', status: ''
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null, userId: null, loginAccount: '', idCard: '', address: '',
  name: '', position: '', department: '客服一部',
  source: '', birthday: null, mobile: '',
  internDate: null, hireDate: null,
  contractStatus: 0, salaryBase: 0, depositAmount: 0,
  status: '0', resignDate: null, remark: '',
  branchCode: DEFAULT_BRANCH_CODE
})

const rules = {
  loginAccount: [
    { required: true, message: '必须分配系统登录账号', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入真实姓名/备注名', trigger: 'blur' }
  ]
}

const formatDate = (d) => {
  if (!d) return '——'
  return d.substring ? d.substring(0, 10) : new Date(d).toISOString().substring(0, 10)
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request({
      url: '/qingbird/employee/list', method: 'get',
      params: { ...queryForm, branchCode: branchCode.value }
    })
    if (res.code === 200) {
      tableData.value = res.rows || []
      total.value = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const loadBranchOptions = async () => {
  if (isAdmin.value) {
    const res = await listBranchInfo({ pageNum: 1, pageSize: 1000 })
    if (res?.code === 200) {
      branchOptions.value = (res.rows || []).map(item => ({
        branchId: item.branchId,
        branchCode: item.workplaceName || String(item.branchId),
        branchName: item.workplaceName
          ? `${item.workplaceName} / ${item.companyName || '未命名分公司'}`
          : `${item.companyName || '未命名分公司'} / ${item.branchId}`
      }))
    }
    return
  }

  const res = await getMyBranchInfo()
  if (res?.code === 200 && res.data) {
    const code = res.data.workplaceName || String(res.data.branchId || DEFAULT_BRANCH_CODE)
    selectedBranchCode.value = code
    branchOptions.value = [{
      branchId: res.data.branchId,
      branchCode: code,
      branchName: `${code} / ${res.data.companyName || '当前分公司'}`
    }]
  } else {
    selectedBranchCode.value = DEFAULT_BRANCH_CODE
  }
}

const handleBranchChange = () => {
  queryForm.pageNum = 1
  fetchData()
}

const goBranchPage = () => {
  router.push('/qingbird/branch')
}

const getDefaultFormBranchCode = () => {
  if (isAdmin.value) {
    return selectedBranchCode.value || branchOptions.value[0]?.branchCode || ''
  }
  return branchCode.value || DEFAULT_BRANCH_CODE
}

const resetForm = () => {
  Object.assign(form, {
    id: null, userId: null, loginAccount: '', idCard: '', address: '',
    name: '', position: '', department: '客服一部',
    source: '', birthday: null, mobile: '',
    internDate: null, hireDate: null,
    contractStatus: 0, salaryBase: 0, depositAmount: 0,
    status: '0', resignDate: null, remark: '', branchCode: getDefaultFormBranchCode()
  })
}

const openAddDialog = () => {
  isEdit.value = false
  resetForm()
  if (isAdmin.value && !form.branchCode && branchOptions.value.length > 0) {
    form.branchCode = branchOptions.value[0].branchCode
  }
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate()
  if (isAdmin.value && !form.branchCode) {
    ElMessage.warning('请先选择员工所属分公司')
    return
  }
  const url = '/qingbird/employee'
  const method = isEdit.value ? 'put' : 'post'
  const res = await request({ url, method, data: { ...form } })
  if (res.code === 200) {
    ElMessage.success(isEdit.value ? '更新成功' : '录入并开通账号成功')
    dialogVisible.value = false
    fetchData()
  } else {
    // Backend may return specific errors like "登录账号已存在"
  }
}

const handleDelete = async (id) => {
  const res = await request({ url: `/qingbird/employee/${id}`, method: 'delete' })
  if (res.code === 200) {
    ElMessage.success('删除成功')
    fetchData()
  }
}

const handleExport = async () => {
  const res = await request({
    url: '/qingbird/employee/export', method: 'post',
    responseType: 'blob', params: { branchCode: branchCode.value }
  })
  const blob = new Blob([res], { type: 'application/vnd.ms-excel' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = '客服坐席花名册.xlsx'; a.click()
  URL.revokeObjectURL(url)
}

// 登录日志逻辑
const dialogLogs = ref(false)
const logLoading = ref(false)
const logData = ref([])
const logTotal = ref(0)
const currentLogAccount = ref('')
const logQuery = reactive({ pageNum: 1, pageSize: 10, userName: '' })

const openLoginLogs = (row) => {
  if (!row.loginAccount) return
  currentLogAccount.value = row.loginAccount
  logQuery.userName = row.loginAccount
  logQuery.pageNum = 1
  dialogLogs.value = true
  fetchLogs()
}

const fetchLogs = async () => {
  logLoading.value = true
  try {
    const res = await request({
      url: '/qingbird/employee/loginLogs',
      method: 'get',
      params: logQuery
    })
    if (res.code === 200) {
      logData.value = res.rows || []
      logTotal.value = res.total || 0
    }
  } finally {
    logLoading.value = false
  }
}

onMounted(async () => {
  await loadBranchOptions()
  fetchData()
})
</script>

<style lang="scss" scoped>
/* 页面头部 */
.emp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.emp-title-group {
  display: flex;
  align-items: center;
  gap: 14px;
}

.emp-title-icon {
  width: 44px;
  height: 44px;
  background: var(--qb-primary-bg);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: var(--qb-primary);
}

.emp-header-actions {
  display: flex;
  gap: 10px;
}

/* 搜索栏 */
.search-bar {
  display: flex;
  align-items: center;
  padding: 14px 20px;
}

/* 员工信息单元格 */
.emp-info-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.emp-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.emp-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text-primary);
  .login-acc {
    color: var(--qb-primary);
    font-size: 11px;
    font-weight: normal;
    margin-left: 2px;
  }
}

.emp-position {
  font-size: 11px;
  color: var(--qb-text-muted);
  margin-top: 2px;
}

/* 联系信息块 */
.contact-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #555;
  margin-bottom: 3px;
}

/* 登录跟踪块 */
.login-track {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background-color: #f7f8fa;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--qb-primary);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  &:hover {
    background-color: var(--qb-primary-bg);
  }
}

/* 日期对 */
.date-pair { display: flex; align-items: center; gap: 6px; }

.date-label {
  font-size: 10px;
  background: #f0f0f0;
  color: #888;
  padding: 1px 5px;
  border-radius: 3px;
  &.hire { background: var(--qb-primary-bg); color: var(--qb-primary); }
}

.date-value {
  font-size: 12px;
  color: var(--qb-primary);
  font-weight: 600;
}

/* 通用 */
.cell-muted { font-size: 12px; color: var(--qb-text-muted); }

.salary-cell { text-align: center; }
.salary-val { font-size: 15px; font-weight: 700; color: var(--qb-text-primary); }
.salary-sub { font-size: 10px; color: var(--qb-text-muted); }

.deposit-val { font-size: 14px; font-weight: 700; color: var(--qb-danger); }
.deposit-sub { font-size: 10px; color: var(--qb-text-muted); }

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.qb-alert-info {
  background-color: #f0f9eb;
  color: #67c23a;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
</style>
