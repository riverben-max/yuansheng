<template>
  <div class="branch-manage-page">
    <template v-if="isAdmin">
      <el-form
        v-show="showSearch"
        ref="queryRef"
        :model="queryParams"
        :inline="true"
        label-width="90px"
        class="search-form"
      >
        <el-form-item label="分公司名称" prop="companyName">
          <el-input
            v-model="queryParams.companyName"
            placeholder="请输入分公司名称"
            clearable
            style="width: 240px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="职场代号" prop="workplaceName">
          <el-input
            v-model="queryParams.workplaceName"
            placeholder="请输入职场代号"
            clearable
            style="width: 220px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="审核状态" prop="auditStatus">
          <el-select v-model="queryParams.auditStatus" placeholder="审核状态" clearable style="width: 180px">
            <el-option label="未完善资料" :value="0" />
            <el-option label="待总部审核" :value="1" />
            <el-option label="审核已通过" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery" v-hasPermi="['qingbird:branchInfo:list']">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery" v-hasPermi="['qingbird:branchInfo:list']">重置</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="10" class="mb8">
        <el-col :span="1.5">
          <el-button type="primary" plain icon="Plus" @click="handleAdd" v-hasPermi="['qingbird:branchInfo:add']">新增</el-button>
        </el-col>
        <el-col :span="1.5">
          <el-button type="success" plain icon="Check" :disabled="single || selectedRow?.auditStatus !== 1" @click="handleApprove()" v-hasPermi="['qingbird:branchInfo:approve']">
            审核通过
          </el-button>
        </el-col>
        <el-col :span="1.5">
          <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete()" v-hasPermi="['qingbird:branchInfo:remove']">
            删除
          </el-button>
        </el-col>
        <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
      </el-row>

      <el-table v-loading="loading" :data="branchList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="职场代号" prop="workplaceName" min-width="140" show-overflow-tooltip />
        <el-table-column label="分公司名称" prop="companyName" min-width="220" show-overflow-tooltip />
        <el-table-column label="负责人" prop="legalPersonName" width="120" />
        <el-table-column label="联系电话" prop="contactPhone" width="140" />
        <el-table-column label="状态" prop="auditStatus" width="120" align="center">
          <template #default="scope">
            <el-tag :type="statusMeta(scope.row.auditStatus).type">
              {{ statusMeta(scope.row.auditStatus).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="createTime" width="170" align="center" />
        <el-table-column label="操作" align="center" width="230" fixed="right">
          <template #default="scope">
            <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['qingbird:branchInfo:edit']">修改</el-button>
            <el-button
              v-if="scope.row.auditStatus === 1"
              link
              type="success"
              icon="Check"
              @click="handleApprove(scope.row)"
              v-hasPermi="['qingbird:branchInfo:approve']"
            >
              审核
            </el-button>
            <el-button link type="danger" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['qingbird:branchInfo:remove']">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="getList"
      />

      <el-dialog :title="title" v-model="open" width="720px" append-to-body>
        <el-form ref="branchRef" :model="form" :rules="rules" label-width="110px">
          <el-row>
            <el-col :span="12">
              <el-form-item label="职场代号" prop="workplaceName">
                <el-input v-model="form.workplaceName" placeholder="例如：Q43-锦鲤电商" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="主管账号" prop="managerUserName">
                <el-input v-model="form.managerUserName" :disabled="!!form.id" placeholder="例如：q43_manager" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="分公司名称" prop="companyName">
                <el-input v-model="form.companyName" placeholder="请输入营业执照上的公司名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="负责人姓名" prop="legalPersonName">
                <el-input v-model="form.legalPersonName" placeholder="请输入负责人姓名" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="联系电话" prop="contactPhone">
                <el-input v-model="form.contactPhone" placeholder="请输入联系电话" />
              </el-form-item>
            </el-col>
            <el-col v-if="!form.id" :span="12">
              <el-form-item label="初始密码" prop="managerPassword">
                <el-input v-model="form.managerPassword" show-password placeholder="请设置主管初始密码" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="联系地址" prop="contactAddress">
                <el-input v-model="form.contactAddress" type="textarea" :rows="2" placeholder="请输入联系地址" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="结算账号" prop="settlementAccounts">
                <el-input
                  v-model="form.settlementAccounts"
                  type="textarea"
                  :rows="3"
                  placeholder='建议填写 JSON，例如：[{"type":"bank","bank":"开户行","account":"账号","name":"户名"}]'
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="资料地址">
                <el-input v-model="form.businessLicense" placeholder="营业执照文件 URL" class="mb8" />
                <el-input v-model="form.idCardFront" placeholder="身份证正面文件 URL" class="mb8" />
                <el-input v-model="form.idCardBack" placeholder="身份证反面文件 URL" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <template #footer>
          <div class="dialog-footer">
            <el-button type="primary" :loading="saveLoading" @click="submitForm" v-hasPermi="[form.id ? 'qingbird:branchInfo:edit' : 'qingbird:branchInfo:add']">确 定</el-button>
            <el-button @click="cancel">取 消</el-button>
          </div>
        </template>
      </el-dialog>
    </template>

    <template v-else>
      <el-descriptions title="我的分公司资料" :column="3" border class="manager-summary">
        <template #extra>
          <el-button icon="Refresh" @click="getMyInfo" v-hasPermi="['qingbird:branchInfo:query']">刷新</el-button>
          <el-button
            type="primary"
            icon="Check"
            :loading="submitLoading"
            :disabled="myForm.auditStatus === 1"
            @click="submitMyInfo"
            v-hasPermi="['qingbird:branchInfo:submit']"
          >
            保存并提交审核
          </el-button>
        </template>
        <el-descriptions-item label="分公司编号">{{ myForm.branchId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="职场代号">{{ myForm.workplaceName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审核状态">
          <el-tag :type="statusMeta(myForm.auditStatus).type">{{ statusMeta(myForm.auditStatus).label }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-form
        ref="myBranchRef"
        :model="myForm"
        :rules="myRules"
        label-width="120px"
        class="manager-form"
        :disabled="myForm.auditStatus === 1"
      >
        <el-row>
          <el-col :span="12">
            <el-form-item label="分公司名称" prop="companyName">
              <el-input v-model="myForm.companyName" placeholder="请输入营业执照上的公司名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="负责人姓名" prop="legalPersonName">
              <el-input v-model="myForm.legalPersonName" placeholder="请输入负责人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话" prop="contactPhone">
              <el-input v-model="myForm.contactPhone" placeholder="请输入联系电话" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系地址" prop="contactAddress">
              <el-input v-model="myForm.contactAddress" placeholder="请输入联系地址" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-divider content-position="left">公司账号</el-divider>
          </el-col>
          <el-col :span="8">
            <el-form-item label="开户行" required>
              <el-input v-model="accountForm.bank" placeholder="例如：招商银行长沙岳麓支行" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="对公账号" required>
              <el-input v-model="accountForm.bankAccount" placeholder="请输入公司对公账号" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="账户名称" required>
              <el-input v-model="accountForm.bankName" placeholder="请输入公司账户名称" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-divider content-position="left">支付宝账号</el-divider>
          </el-col>
          <el-col :span="12">
            <el-form-item label="支付宝账号" required>
              <el-input v-model="accountForm.alipayAccount" placeholder="请输入支付宝账号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="支付宝户名" required>
              <el-input v-model="accountForm.alipayName" placeholder="请输入支付宝实名认证姓名/公司名" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-divider content-position="left">资质文件</el-divider>
          </el-col>
          <el-col :span="24">
            <el-form-item label="营业执照" prop="businessLicense">
              <image-upload
                v-model="myForm.businessLicense"
                :limit="1"
                :file-size="10"
                :file-type="['png', 'jpg', 'jpeg', 'webp']"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="身份证正面" prop="idCardFront">
              <image-upload
                v-model="myForm.idCardFront"
                :limit="1"
                :file-size="10"
                :file-type="['png', 'jpg', 'jpeg', 'webp']"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="身份证反面" prop="idCardBack">
              <image-upload
                v-model="myForm.idCardBack"
                :limit="1"
                :file-size="10"
                :file-type="['png', 'jpg', 'jpeg', 'webp']"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </template>
  </div>
</template>

<script setup name="QingbirdBranchManagement">
import { computed, getCurrentInstance, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import useUserStore from '@/store/modules/user'
import { validateInitialPassword } from '@/utils/passwordPolicy'
import {
  listBranchInfo,
  getBranchInfo,
  getMyBranchInfo,
  addBranchInfo,
  updateBranchInfo,
  delBranchInfo,
  submitBranchInfo,
  approveBranchInfo
} from '@/api/qingbird/branchInfo'

const { proxy } = getCurrentInstance()
const userStore = useUserStore()
const isAdmin = computed(() => (userStore.roles || []).includes('admin'))

const loading = ref(false)
const saveLoading = ref(false)
const submitLoading = ref(false)
const showSearch = ref(true)
const open = ref(false)
const title = ref('')
const total = ref(0)
const branchList = ref([])
const ids = ref([])
const selectedRows = ref([])
const single = ref(true)
const multiple = ref(true)
const selectedRow = computed(() => selectedRows.value.length === 1 ? selectedRows.value[0] : null)

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  companyName: undefined,
  workplaceName: undefined,
  auditStatus: undefined
})

const emptyForm = () => ({
  id: undefined,
  branchId: undefined,
  workplaceName: '',
  companyName: '',
  legalPersonName: '',
  contactPhone: '',
  contactAddress: '',
  settlementAccounts: '[]',
  businessLicense: '',
  idCardFront: '',
  idCardBack: '',
  managerUserName: '',
  managerPassword: '',
  auditStatus: 0
})

const form = ref(emptyForm())
const myForm = ref(emptyForm())
const accountForm = reactive({
  bank: '',
  bankAccount: '',
  bankName: '',
  alipayAccount: '',
  alipayName: ''
})

const validateManagerUserName = (rule, value, callback) => {
  if (!form.value.id && !value) {
    callback(new Error('主管账号不能为空'))
  } else {
    callback()
  }
}

const validateManagerPassword = (rule, value, callback) => {
  if (form.value.id) {
    callback()
    return
  }
  const result = validateInitialPassword(value, form.value.managerUserName)
  if (!result.valid) {
    callback(new Error(result.message))
    return
  }
  callback()
}

const validateJson = (rule, value, callback) => {
  if (!value || !value.trim()) {
    callback()
    return
  }
  try {
    JSON.parse(value)
    callback()
  } catch (err) {
    callback(new Error('请填写合法 JSON，留空会按 [] 保存'))
  }
}

const rules = {
  workplaceName: [{ required: true, message: '职场代号不能为空', trigger: 'blur' }],
  companyName: [{ required: true, message: '分公司名称不能为空', trigger: 'blur' }],
  legalPersonName: [{ required: true, message: '负责人姓名不能为空', trigger: 'blur' }],
  managerUserName: [{ validator: validateManagerUserName, trigger: 'blur' }],
  managerPassword: [{ validator: validateManagerPassword, trigger: 'blur' }],
  settlementAccounts: [{ validator: validateJson, trigger: 'blur' }]
}

const myRules = {
  companyName: [{ required: true, message: '分公司名称不能为空', trigger: 'blur' }],
  legalPersonName: [{ required: true, message: '负责人姓名不能为空', trigger: 'blur' }],
  contactPhone: [{ required: true, message: '联系电话不能为空', trigger: 'blur' }],
  contactAddress: [{ required: true, message: '联系地址不能为空', trigger: 'blur' }],
  businessLicense: [{ required: true, message: '营业执照不能为空', trigger: 'blur' }],
  idCardFront: [{ required: true, message: '身份证正面不能为空', trigger: 'blur' }],
  idCardBack: [{ required: true, message: '身份证反面不能为空', trigger: 'blur' }]
}

function statusMeta(status) {
  const map = {
    0: { label: '未完善资料', type: 'info' },
    1: { label: '待总部审核', type: 'warning' },
    2: { label: '审核已通过', type: 'success' }
  }
  return map[status] || map[0]
}

function normalizeSettlementAccounts(value) {
  if (value === null || value === undefined || value === '') return '[]'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

function normalizeBranchInfo(data) {
  return {
    ...emptyForm(),
    ...(data || {}),
    settlementAccounts: normalizeSettlementAccounts(data?.settlementAccounts)
  }
}

async function getList() {
  loading.value = true
  try {
    const res = await listBranchInfo(queryParams)
    branchList.value = (res.rows || []).map(normalizeBranchInfo)
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

function resetQuery() {
  proxy.resetForm('queryRef')
  handleQuery()
}

function resetForm() {
  form.value = emptyForm()
  proxy.resetForm('branchRef')
}

function normalizeSubmitData(data) {
  return {
    ...data,
    settlementAccounts: data.settlementAccounts && data.settlementAccounts.trim()
      ? data.settlementAccounts.trim()
      : '[]'
  }
}

function resetAccountForm() {
  Object.assign(accountForm, {
    bank: '',
    bankAccount: '',
    bankName: '',
    alipayAccount: '',
    alipayName: ''
  })
}

function syncAccountForm(settlementAccounts) {
  resetAccountForm()
  try {
    const accounts = JSON.parse(normalizeSettlementAccounts(settlementAccounts))
    if (!Array.isArray(accounts)) return
    const bank = accounts.find(item => item.type === 'bank') || {}
    const alipay = accounts.find(item => item.type === 'alipay') || {}
    accountForm.bank = bank.bank || ''
    accountForm.bankAccount = bank.account || ''
    accountForm.bankName = bank.name || ''
    accountForm.alipayAccount = alipay.account || ''
    accountForm.alipayName = alipay.name || ''
  } catch (err) {
    resetAccountForm()
  }
}

function buildSettlementAccounts() {
  return JSON.stringify([
    {
      type: 'bank',
      bank: accountForm.bank.trim(),
      account: accountForm.bankAccount.trim(),
      name: accountForm.bankName.trim()
    },
    {
      type: 'alipay',
      account: accountForm.alipayAccount.trim(),
      name: accountForm.alipayName.trim()
    }
  ])
}

function validateAccountForm() {
  if (!accountForm.bank || !accountForm.bankAccount || !accountForm.bankName) {
    ElMessage.error('请完整填写公司账号：开户行、对公账号、账户名称')
    return false
  }
  if (!accountForm.alipayAccount || !accountForm.alipayName) {
    ElMessage.error('请完整填写支付宝账号和支付宝户名')
    return false
  }
  return true
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
  ids.value = selection.map(item => item.id)
  single.value = selection.length !== 1
  multiple.value = selection.length === 0
}

function handleAdd() {
  resetForm()
  title.value = '新增分公司'
  open.value = true
}

async function handleUpdate(row) {
  resetForm()
  const id = row?.id || ids.value[0]
  const res = await getBranchInfo(id)
  form.value = normalizeBranchInfo(res.data)
  title.value = '修改分公司'
  open.value = true
}

function submitForm() {
  proxy.$refs.branchRef.validate(async valid => {
    if (!valid) return
    saveLoading.value = true
    try {
      const data = normalizeSubmitData(form.value)
      if (data.id) {
        await updateBranchInfo(data)
        ElMessage.success('修改成功')
      } else {
        await addBranchInfo(data)
        ElMessage.success('新增成功')
      }
      open.value = false
      getList()
    } catch (err) {
      ElMessage.error(err?.message || '保存失败')
    } finally {
      saveLoading.value = false
    }
  })
}

function cancel() {
  open.value = false
  resetForm()
}

async function handleApprove(row) {
  const target = row || selectedRow.value
  if (!target) return
  await ElMessageBox.confirm(`确认通过【${target.companyName || target.workplaceName}】的分公司资料审核吗？`, '审核确认', {
    type: 'warning'
  })
  await approveBranchInfo(target.id)
  ElMessage.success('审核已通过')
  getList()
}

async function handleDelete(row) {
  const targetIds = row?.id ? [row.id] : ids.value
  if (!targetIds.length) return
  await ElMessageBox.confirm(`是否确认删除选中的 ${targetIds.length} 条分公司记录？`, '删除确认', {
    type: 'warning'
  })
  await delBranchInfo(targetIds.join(','))
  ElMessage.success('删除成功')
  getList()
}

async function getMyInfo() {
  loading.value = true
  try {
    const res = await getMyBranchInfo()
    myForm.value = normalizeBranchInfo(res.data)
    syncAccountForm(myForm.value.settlementAccounts)
  } finally {
    loading.value = false
  }
}

function submitMyInfo() {
  proxy.$refs.myBranchRef.validate(async valid => {
    if (!valid) return
    if (!validateAccountForm()) return
    submitLoading.value = true
    try {
      await submitBranchInfo(normalizeSubmitData({
        ...myForm.value,
        settlementAccounts: buildSettlementAccounts()
      }))
      ElMessage.success('资料已提交总部审核')
      getMyInfo()
    } catch (err) {
      ElMessage.error(err?.message || '提交失败')
    } finally {
      submitLoading.value = false
    }
  })
}

onMounted(async () => {
  if (isAdmin.value) {
    getList()
  } else {
    getMyInfo()
  }
})
</script>

<style lang="scss" scoped>
.branch-manage-page {
  padding: 0;
}

.search-form {
  margin-bottom: 10px;
}

.manager-summary {
  margin-bottom: 18px;
}

.manager-form {
  max-width: 1100px;
}

.mb8 {
  margin-bottom: 8px;
}
</style>
