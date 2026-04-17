<template>
  <div class="app-container">
    <el-row :gutter="20">
      <splitpanes :horizontal="appStore.device === 'mobile'" class="default-theme">
        <!--部门数据-->
        <pane v-if="!isQingbirdUserPage" size="16">
          <el-col>
            <div class="head-container">
              <el-input v-model="deptName" placeholder="请输入部门名称" clearable prefix-icon="Search" style="margin-bottom: 20px" />
            </div>
            <div class="head-container">
              <el-tree :data="deptOptions" :props="{ label: 'label', children: 'children' }" :expand-on-click-node="false" :filter-node-method="filterNode" ref="deptTreeRef" node-key="id" highlight-current default-expand-all @node-click="handleNodeClick" />
            </div>
          </el-col>
        </pane>
        <!--用户数据-->
        <pane :size="isQingbirdUserPage ? 100 : 84">
          <el-col>
            <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="68px">
              <el-form-item v-if="isQingbirdUserPage" label="所属分公司" prop="employeeBranchCode">
                <el-select
                  v-model="queryParams.employeeBranchCode"
                  placeholder="请选择所属分公司"
                  clearable
                  filterable
                  style="width: 240px"
                  @change="handleQuery"
                >
                  <el-option
                    v-for="branch in qingbirdBranchOptions"
                    :key="branch.branchCode"
                    :label="branch.branchName"
                    :value="branch.branchCode"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="isQingbirdUserPage" label="登录账号" prop="employeeLoginAccount">
                <el-input v-model="queryParams.employeeLoginAccount" placeholder="请输入登录账号" clearable style="width: 240px" @keyup.enter="handleQuery" />
              </el-form-item>
              <el-form-item v-else label="用户名称" prop="userName">
                <el-input v-model="queryParams.userName" placeholder="请输入用户名称" clearable style="width: 240px" @keyup.enter="handleQuery" />
              </el-form-item>
              <el-form-item :label="isQingbirdUserPage ? '手机号' : '手机号码'" prop="phonenumber">
                <el-input v-model="queryParams.phonenumber" placeholder="请输入手机号码" clearable style="width: 240px" @keyup.enter="handleQuery" />
              </el-form-item>
              <el-form-item v-if="isQingbirdUserPage" label="名字" prop="employeeName">
                <el-input v-model="queryParams.employeeName" placeholder="请输入名字" clearable style="width: 240px" @keyup.enter="handleQuery" />
              </el-form-item>
              <el-form-item v-if="isQingbirdUserPage" label="身份证号" prop="employeeIdCard">
                <el-input v-model="queryParams.employeeIdCard" placeholder="请输入身份证号" clearable style="width: 240px" @keyup.enter="handleQuery" />
              </el-form-item>
              <el-form-item v-if="!isQingbirdUserPage" label="状态" prop="status">
                <el-select v-model="queryParams.status" placeholder="用户状态" clearable style="width: 240px">
                  <el-option v-for="dict in sys_normal_disable" :key="dict.value" :label="dict.label" :value="dict.value" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="!isQingbirdUserPage" label="创建时间" style="width: 308px">
                <el-date-picker v-model="dateRange" value-format="YYYY-MM-DD" type="daterange" range-separator="-" start-placeholder="开始日期" end-placeholder="结束日期"></el-date-picker>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
                <el-button icon="Refresh" @click="resetQuery">重置</el-button>
              </el-form-item>
            </el-form>

            <el-row :gutter="10" class="mb8">
              <el-col :span="1.5">
                <el-button type="primary" plain icon="Plus" @click="handleAdd" v-hasPermi="[isQingbirdUserPage ? 'qingbird:employee:add' : 'system:user:add']">新增</el-button>
              </el-col>
              <el-col :span="1.5">
                <el-button type="success" plain icon="Edit" :disabled="single" @click="handleUpdate" v-hasPermi="[isQingbirdUserPage ? 'qingbird:employee:edit' : 'system:user:edit']">修改</el-button>
              </el-col>
              <el-col :span="1.5">
                <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete" v-hasPermi="[isQingbirdUserPage ? 'qingbird:employee:remove' : 'system:user:remove']">删除</el-button>
              </el-col>
              <el-col :span="1.5">
                <el-button v-if="!isQingbirdUserPage" type="info" plain icon="Upload" @click="handleImport" v-hasPermi="['system:user:import']">导入</el-button>
              </el-col>
              <el-col :span="1.5">
                <el-button type="warning" plain icon="Download" @click="handleExport" v-hasPermi="[isQingbirdUserPage ? 'qingbird:employee:export' : 'system:user:export']">导出</el-button>
              </el-col>
              <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" :columns="activeColumns"></right-toolbar>
            </el-row>

            <el-table v-loading="loading" :data="userList" @selection-change="handleSelectionChange">
              <el-table-column type="selection" width="50" align="center" />
              <el-table-column label="用户编号" align="center" key="userId" prop="userId" v-if="!isQingbirdUserPage && columns.userId.visible" />
              <el-table-column label="用户名称" align="center" key="userName" prop="userName" v-if="!isQingbirdUserPage && columns.userName.visible" :show-overflow-tooltip="true" />
              <el-table-column label="用户昵称" align="center" key="nickName" prop="nickName" v-if="!isQingbirdUserPage && columns.nickName.visible" :show-overflow-tooltip="true" />
              <el-table-column label="所属分公司" align="center" key="deptName" prop="dept.deptName" v-if="!isQingbirdUserPage && columns.deptName.visible" min-width="130" :show-overflow-tooltip="true" />
              <el-table-column label="手机号码" align="center" key="phonenumber" prop="phonenumber" v-if="!isQingbirdUserPage && columns.phonenumber.visible" width="120" />
              <el-table-column label="登录IP" align="center" key="loginIp" prop="loginIp" v-if="!isQingbirdUserPage && columns.loginIp.visible" width="130" :show-overflow-tooltip="true" />
              <el-table-column label="最后登录" align="center" key="loginDate" prop="loginDate" v-if="!isQingbirdUserPage && columns.loginDate.visible" width="160">
                <template #default="scope">
                  <span>{{ parseTime(scope.row.loginDate) || '从未登录' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="状态" align="center" key="status" v-if="!isQingbirdUserPage && columns.status.visible">
                <template #default="scope">
                  <el-switch
                    v-model="scope.row.status"
                    active-value="0"
                    inactive-value="1"
                    @change="handleStatusChange(scope.row)"
                  ></el-switch>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" align="center" prop="createTime" v-if="!isQingbirdUserPage && columns.createTime.visible" width="160">
                <template #default="scope">
                  <span>{{ parseTime(scope.row.createTime) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="登录账号" align="center" key="qingbirdLoginAccount" v-if="isQingbirdUserPage && qingbirdColumns.loginAccount.visible" min-width="120" :show-overflow-tooltip="true">
                <template #default="scope">
                  <span>{{ scope.row.loginAccount }}</span>
                </template>
              </el-table-column>
              <el-table-column label="所属分公司" align="center" key="qingbirdBranch" prop="branchLabel" v-if="isQingbirdUserPage && qingbirdColumns.branch.visible" min-width="130" :show-overflow-tooltip="true" />
              <el-table-column label="名字" align="center" key="qingbirdName" v-if="isQingbirdUserPage && qingbirdColumns.name.visible" min-width="100" :show-overflow-tooltip="true">
                <template #default="scope">
                  <span>{{ scope.row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="身份证号" align="center" key="qingbirdIdCard" prop="idCard" v-if="isQingbirdUserPage && qingbirdColumns.idCard.visible" width="180" :show-overflow-tooltip="true" />
              <el-table-column label="手机号" align="center" key="qingbirdPhone" prop="mobile" v-if="isQingbirdUserPage && qingbirdColumns.phone.visible" width="120" />
              <el-table-column label="地址" align="center" key="qingbirdAddress" prop="address" v-if="isQingbirdUserPage && qingbirdColumns.address.visible" min-width="180" :show-overflow-tooltip="true" />
              <el-table-column label="登录地址" align="center" key="qingbirdLoginAddress" v-if="isQingbirdUserPage && qingbirdColumns.loginAddress.visible" min-width="130">
                <template #default="scope">
                  <el-tooltip :content="scope.row.lastLoginIp || '暂无登录IP'" placement="top">
                    <span>{{ scope.row.lastLoginIp || '-' }}</span>
                  </el-tooltip>
                </template>
              </el-table-column>
              <el-table-column label="备注名" align="center" key="qingbirdRemarkName" prop="remark" v-if="isQingbirdUserPage && qingbirdColumns.remarkName.visible" min-width="120" :show-overflow-tooltip="true" />
              <el-table-column label="操作" align="center" :width="isQingbirdUserPage ? 130 : 190" class-name="small-padding fixed-width">
                <template #default="scope">
                  <template v-if="isQingbirdUserPage">
                    <el-tooltip content="修改" placement="top" v-if="scope.row.userId !== 1">
                      <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['qingbird:employee:edit']"></el-button>
                    </el-tooltip>
                    <el-tooltip content="删除" placement="top" v-if="scope.row.userId !== 1">
                      <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['qingbird:employee:remove']"></el-button>
                    </el-tooltip>
                    <el-tooltip content="登录日志" placement="top">
                      <el-button link type="primary" icon="Tickets" @click="openLoginLogs(scope.row)"></el-button>
                    </el-tooltip>
                  </template>
                  <template v-else>
                    <el-tooltip content="修改" placement="top" v-if="scope.row.userId !== 1">
                      <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['system:user:edit']"></el-button>
                    </el-tooltip>
                    <el-tooltip content="删除" placement="top" v-if="scope.row.userId !== 1">
                      <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['system:user:remove']"></el-button>
                    </el-tooltip>
                    <el-tooltip content="重置密码" placement="top" v-if="scope.row.userId !== 1">
                      <el-button link type="primary" icon="Key" @click="handleResetPwd(scope.row)" v-hasPermi="['system:user:resetPwd']"></el-button>
                    </el-tooltip>
                    <el-tooltip content="分配角色" placement="top" v-if="scope.row.userId !== 1">
                      <el-button link type="primary" icon="CircleCheck" @click="handleAuthRole(scope.row)" v-hasPermi="['system:user:edit']"></el-button>
                    </el-tooltip>
                    <el-tooltip content="查看登录日志" placement="top">
                      <el-button link type="primary" icon="Tickets" @click="openLoginLogs(scope.row)"></el-button>
                    </el-tooltip>
                  </template>
                </template>
              </el-table-column>
            </el-table>
            <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" @pagination="getList" />
          </el-col>
        </pane>
      </splitpanes>
    </el-row>

    <!-- 添加或修改用户配置对话框 -->
    <el-dialog :title="title" v-model="open" width="600px" append-to-body>
      <el-form :model="form" :rules="rules" ref="userRef" label-width="80px">
        <template v-if="isQingbirdUserPage">
          <el-row>
            <el-col :span="12">
              <el-form-item label="登录账号" prop="loginAccount">
                <el-input v-model="form.loginAccount" placeholder="请输入登录账号" maxlength="30" :disabled="!!form.id" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="所属分公司" prop="branchCode">
                <el-select v-model="form.branchCode" placeholder="请选择所属分公司" style="width: 100%;" filterable>
                  <el-option
                    v-for="branch in qingbirdBranchOptions"
                    :key="branch.branchCode"
                    :label="branch.branchName"
                    :value="branch.branchCode"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="12">
              <el-form-item label="名字" prop="name">
                <el-input v-model="form.name" placeholder="请输入真实姓名" maxlength="30" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="身份证号" prop="idCard">
                <el-input v-model="form.idCard" placeholder="请输入身份证号" maxlength="18" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="12">
              <el-form-item label="手机号" prop="mobile">
                <el-input v-model="form.mobile" placeholder="请输入手机号" maxlength="11" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="24">
              <el-form-item label="地址" prop="address">
                <el-input v-model="form.address" placeholder="请输入地址" maxlength="255" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="24">
              <el-form-item label="备注名" prop="remark">
                <el-input v-model="form.remark" placeholder="请输入备注名" maxlength="100" />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
        <template v-else>
        <el-row>
          <el-col :span="12">
            <el-form-item label="用户昵称" prop="nickName">
              <el-input v-model="form.nickName" placeholder="请输入用户昵称" maxlength="30" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="归属部门" prop="deptId">
              <el-tree-select v-model="form.deptId" :data="enabledDeptOptions" :props="{ value: 'id', label: 'label', children: 'children' }" value-key="id" placeholder="请选择归属部门" clearable check-strictly />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="12">
            <el-form-item label="手机号码" prop="phonenumber">
              <el-input v-model="form.phonenumber" placeholder="请输入手机号码" maxlength="11" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" placeholder="请输入邮箱" maxlength="50" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="12">
            <el-form-item v-if="form.userId == undefined" label="用户名称" prop="userName">
              <el-input v-model="form.userName" placeholder="请输入用户名称" maxlength="30" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item v-if="form.userId == undefined" label="用户密码" prop="password">
              <el-input v-model="form.password" placeholder="请输入用户密码" type="password" maxlength="20" show-password />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="12">
            <el-form-item label="用户性别">
              <el-select v-model="form.sex" placeholder="请选择">
                <el-option v-for="dict in sys_user_sex" :key="dict.value" :label="dict.label" :value="dict.value"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-radio-group v-model="form.status">
                <el-radio v-for="dict in sys_normal_disable" :key="dict.value" :value="dict.value">{{ dict.label }}</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="12">
            <el-form-item label="岗位">
              <el-select v-model="form.postIds" multiple placeholder="请选择">
                <el-option v-for="item in postOptions" :key="item.postId" :label="item.postName" :value="item.postId" :disabled="item.status == 1"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色">
              <el-select v-model="form.roleIds" multiple placeholder="请选择">
                <el-option v-for="item in roleOptions" :key="item.roleId" :label="item.roleName" :value="item.roleId" :disabled="item.status == 1"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" placeholder="请输入内容"></el-input>
            </el-form-item>
          </el-col>
        </el-row>
        </template>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 用户导入对话框 -->
    <el-dialog :title="upload.title" v-model="upload.open" width="400px" append-to-body>
      <el-upload ref="uploadRef" :limit="1" accept=".xlsx, .xls" :headers="upload.headers" :action="upload.url + '?updateSupport=' + upload.updateSupport" :disabled="upload.isUploading" :on-progress="handleFileUploadProgress" :on-success="handleFileSuccess" :on-change="handleFileChange" :on-remove="handleFileRemove" :auto-upload="false" drag>
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip text-center">
            <div class="el-upload__tip">
              <el-checkbox v-model="upload.updateSupport" />是否更新已经存在的用户数据
            </div>
            <span>仅允许导入xls、xlsx格式文件。</span>
            <el-link type="primary" underline="never" style="font-size: 12px; vertical-align: baseline" @click="importTemplate">下载模板</el-link>
          </div>
        </template>
      </el-upload>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitFileForm">确 定</el-button>
          <el-button @click="upload.open = false">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 登录日志对话框 -->
    <el-dialog v-model="loginLogOpen" :title="`${currentLogUserName || ''} 登录日志`" width="980px" append-to-body>
      <el-table v-loading="loginLogLoading" :data="loginLogList" border>
        <el-table-column label="访问编号" prop="infoId" width="90" align="center" />
        <el-table-column label="用户名称" prop="userName" width="130" :show-overflow-tooltip="true" />
        <el-table-column label="登录地址" prop="ipaddr" width="130" :show-overflow-tooltip="true" />
        <el-table-column label="登录地点" prop="loginLocation" width="130" :show-overflow-tooltip="true" />
        <el-table-column label="操作系统" prop="os" width="120" :show-overflow-tooltip="true" />
        <el-table-column label="浏览器" prop="browser" width="120" :show-overflow-tooltip="true" />
        <el-table-column label="登录状态" prop="status" width="90" align="center">
          <template #default="scope">
            <dict-tag :options="sys_common_status" :value="scope.row.status" />
          </template>
        </el-table-column>
        <el-table-column label="描述" prop="msg" min-width="160" :show-overflow-tooltip="true" />
        <el-table-column label="访问时间" prop="loginTime" width="170" align="center">
          <template #default="scope">
            <span>{{ parseTime(scope.row.loginTime) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-show="loginLogTotal > 0"
        :total="loginLogTotal"
        v-model:page="loginLogQuery.pageNum"
        v-model:limit="loginLogQuery.pageSize"
        @pagination="fetchLoginLogs"
      />
    </el-dialog>
  </div>
</template>

<script setup name="User">
import { getToken } from "@/utils/auth"
import request from "@/utils/request"
import useAppStore from '@/store/modules/app'
import useUserStore from '@/store/modules/user'
import { changeUserStatus, listUser, resetUserPwd, delUser, getUser, updateUser, addUser, deptTreeSelect } from "@/api/system/user"
import { list as listLogininfor } from "@/api/monitor/logininfor"
import { listBranchInfo, getMyBranchInfo } from "@/api/qingbird/branchInfo"
import { Splitpanes, Pane } from "splitpanes"
import "splitpanes/dist/splitpanes.css"

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()
const userStore = useUserStore()
const { proxy } = getCurrentInstance()
const { sys_normal_disable, sys_user_sex, sys_common_status } = proxy.useDict("sys_normal_disable", "sys_user_sex", "sys_common_status")
const isQingbirdUserPage = computed(() => route.path.startsWith("/qingbird/"))
const isAdmin = computed(() => (userStore.roles || []).includes("admin"))

const userList = ref([])
const open = ref(false)
const loading = ref(true)
const showSearch = ref(true)
const ids = ref([])
const single = ref(true)
const multiple = ref(true)
const total = ref(0)
const title = ref("")
const dateRange = ref([])
const deptName = ref("")
const deptOptions = ref(undefined)
const enabledDeptOptions = ref(undefined)
const initPassword = ref(undefined)
const postOptions = ref([])
const roleOptions = ref([])
const qingbirdBranchOptions = ref([])
/*** 用户导入参数 */
const upload = reactive({
  // 是否显示弹出层（用户导入）
  open: false,
  // 弹出层标题（用户导入）
  title: "",
  // 是否禁用上传
  isUploading: false,
  // 是否更新已经存在的用户数据
  updateSupport: 0,
  // 设置上传的请求头部
  headers: { Authorization: "Bearer " + getToken() },
  // 上传的地址
  url: import.meta.env.VITE_APP_BASE_API + "/system/user/importData"
})
// 列显隐信息
const columns = ref({
  userId: { label: '用户编号', visible: true },
  userName: { label: '用户名称', visible: true },
  nickName: { label: '用户昵称', visible: true },
  deptName: { label: '所属分公司', visible: true },
  phonenumber: { label: '手机号码', visible: true },
  loginIp: { label: '登录IP', visible: true },
  loginDate: { label: '最后登录', visible: true },
  status: { label: '状态', visible: true },
  createTime: { label: '创建时间', visible: true }
})
const qingbirdColumns = ref({
  loginAccount: { label: '登录账号', visible: true },
  branch: { label: '所属分公司', visible: true },
  name: { label: '名字', visible: true },
  idCard: { label: '身份证号', visible: true },
  phone: { label: '手机号', visible: true },
  address: { label: '地址', visible: true },
  loginAddress: { label: '登录地址', visible: true },
  remarkName: { label: '备注名', visible: true }
})
const activeColumns = computed(() => isQingbirdUserPage.value ? qingbirdColumns.value : columns.value)

const loginLogOpen = ref(false)
const loginLogLoading = ref(false)
const loginLogList = ref([])
const loginLogTotal = ref(0)
const currentLogUserName = ref("")
const loginLogQuery = reactive({
  pageNum: 1,
  pageSize: 10,
  userName: undefined,
  orderByColumn: "loginTime",
  isAsc: "descending"
})

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    userName: undefined,
    employeeLoginAccount: undefined,
    phonenumber: undefined,
    employeeName: undefined,
    employeeIdCard: undefined,
    employeeBranchCode: undefined,
    status: undefined,
    deptId: undefined
  },
  rules: {
    loginAccount: [{ required: true, message: "登录账号不能为空", trigger: "blur" }],
    branchCode: [{ required: true, message: "请选择所属分公司", trigger: "change" }],
    name: [{ required: true, message: "名字不能为空", trigger: "blur" }],
    userName: [{ required: true, message: "用户名称不能为空", trigger: "blur" }, { min: 2, max: 20, message: "用户名称长度必须介于 2 和 20 之间", trigger: "blur" }],
    nickName: [{ required: true, message: "用户昵称不能为空", trigger: "blur" }],
    password: [{ required: true, message: "用户密码不能为空", trigger: "blur" }, { min: 5, max: 20, message: "用户密码长度必须介于 5 和 20 之间", trigger: "blur" }, { pattern: /^[^<>"'|\\]+$/, message: "不能包含非法字符：< > \" ' \\\ |", trigger: "blur" }],
    email: [{ type: "email", message: "请输入正确的邮箱地址", trigger: ["blur", "change"] }],
    phonenumber: [{ pattern: /^1[3|4|5|6|7|8|9][0-9]\d{8}$/, message: "请输入正确的手机号码", trigger: "blur" }]
  }
})

const { queryParams, form, rules } = toRefs(data)

/** 通过条件过滤节点  */
const filterNode = (value, data) => {
  if (!value) return true
  return data.label.indexOf(value) !== -1
}

/** 根据名称筛选部门树 */
watch(deptName, val => {
  proxy.$refs["deptTreeRef"]?.filter(val)
})

/** 查询用户列表 */
function getList() {
  if (isQingbirdUserPage.value) {
    getQingbirdEmployeeList()
    return
  }
  loading.value = true
  listUser(proxy.addDateRange(queryParams.value, dateRange.value)).then(res => {
    loading.value = false
    userList.value = res.rows
    total.value = res.total
  })
}

function getBranchLabel(branchCode) {
  if (!branchCode) return ""
  const branch = qingbirdBranchOptions.value.find(item => item.branchCode === branchCode)
  return branch?.branchName || branchCode
}

function mergeQingbirdBranchOptions(rows = []) {
  const existingCodes = new Set(qingbirdBranchOptions.value.map(item => item.branchCode))
  rows.forEach(row => {
    const code = row.branchCode
    if (!code || existingCodes.has(code)) return
    existingCodes.add(code)
    qingbirdBranchOptions.value.push({
      branchCode: code,
      branchName: `${code} / 未建分公司档案`
    })
  })
}

function mapQingbirdEmployee(row) {
  return {
    ...row,
    userName: row.loginAccount,
    nickName: row.remark,
    phonenumber: row.mobile,
    branchLabel: getBranchLabel(row.branchCode),
    employeeLoginAccount: row.loginAccount,
    employeeBranchCode: row.branchCode,
    employeeName: row.name,
    employeeIdCard: row.idCard,
    employeeAddress: row.address,
    loginIp: row.lastLoginIp
  }
}

function getQingbirdEmployeeList() {
  loading.value = true
  request({
    url: "/qingbird/employee/list",
    method: "get",
    params: {
      pageNum: queryParams.value.pageNum,
      pageSize: queryParams.value.pageSize,
      branchCode: queryParams.value.employeeBranchCode,
      loginAccount: queryParams.value.employeeLoginAccount,
      name: queryParams.value.employeeName,
      idCard: queryParams.value.employeeIdCard,
      mobile: queryParams.value.phonenumber
    }
  }).then(res => {
    const rows = res.rows || []
    mergeQingbirdBranchOptions(rows)
    userList.value = rows.map(mapQingbirdEmployee)
    total.value = res.total || 0
  }).finally(() => {
    loading.value = false
  })
}

async function loadQingbirdBranchOptions() {
  if (!isQingbirdUserPage.value) return
  if (isAdmin.value) {
    const res = await listBranchInfo({ pageNum: 1, pageSize: 1000 })
    if (res?.code === 200) {
      qingbirdBranchOptions.value = (res.rows || []).map(item => ({
        branchCode: item.workplaceName || String(item.branchId),
        branchName: item.workplaceName
          ? `${item.workplaceName} / ${item.companyName || "未命名分公司"}`
          : `${item.companyName || "未命名分公司"} / ${item.branchId}`
      }))
    }
    return
  }
  const res = await getMyBranchInfo()
  if (res?.code === 200 && res.data) {
    const code = res.data.workplaceName || String(res.data.branchId || "")
    qingbirdBranchOptions.value = [{
      branchCode: code,
      branchName: `${code} / ${res.data.companyName || "当前分公司"}`
    }]
    queryParams.value.employeeBranchCode = code
  }
}

/** 查询部门下拉树结构 */
function getDeptTree() {
  deptTreeSelect().then(response => {
    deptOptions.value = response.data
    enabledDeptOptions.value = filterDisabledDept(JSON.parse(JSON.stringify(response.data)))
  })
}

/** 过滤禁用的部门 */
function filterDisabledDept(deptList) {
  return deptList.filter(dept => {
    if (dept.disabled) {
      return false
    }
    if (dept.children && dept.children.length) {
      dept.children = filterDisabledDept(dept.children)
    }
    return true
  })
}

/** 节点单击事件 */
function handleNodeClick(data) {
  queryParams.value.deptId = data.id
  handleQuery()
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1
  getList()
}

/** 重置按钮操作 */
function resetQuery() {
  dateRange.value = []
  proxy.resetForm("queryRef")
  queryParams.value.deptId = undefined
  if (isQingbirdUserPage.value && !isAdmin.value && qingbirdBranchOptions.value[0]?.branchCode) {
    queryParams.value.employeeBranchCode = qingbirdBranchOptions.value[0].branchCode
  }
  proxy.$refs.deptTreeRef?.setCurrentKey(null)
  handleQuery()
}

/** 删除按钮操作 */
function handleDelete(row) {
  if (isQingbirdUserPage.value) {
    const employeeIds = row?.id || ids.value
    proxy.$modal.confirm('是否确认删除客服坐席编号为"' + employeeIds + '"的数据项？').then(function () {
      return request({ url: `/qingbird/employee/${employeeIds}`, method: "delete" })
    }).then(() => {
      getList()
      proxy.$modal.msgSuccess("删除成功")
    }).catch(() => {})
    return
  }
  const userIds = row.userId || ids.value
  proxy.$modal.confirm('是否确认删除用户编号为"' + userIds + '"的数据项？').then(function () {
    return delUser(userIds)
  }).then(() => {
    getList()
    proxy.$modal.msgSuccess("删除成功")
  }).catch(() => {})
}

/** 导出按钮操作 */
function handleExport() {
  if (isQingbirdUserPage.value) {
    proxy.download("qingbird/employee/export", {
      branchCode: queryParams.value.employeeBranchCode,
      loginAccount: queryParams.value.employeeLoginAccount,
      name: queryParams.value.employeeName,
      idCard: queryParams.value.employeeIdCard,
      mobile: queryParams.value.phonenumber
    }, `customer_seat_${new Date().getTime()}.xlsx`)
    return
  }
  proxy.download("system/user/export", {
    ...queryParams.value,
  },`user_${new Date().getTime()}.xlsx`)
}

/** 用户状态修改  */
function handleStatusChange(row) {
  let text = row.status === "0" ? "启用" : "停用"
  proxy.$modal.confirm('确认要"' + text + '""' + row.userName + '"用户吗?').then(function () {
    return changeUserStatus(row.userId, row.status)
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功")
  }).catch(function () {
    row.status = row.status === "0" ? "1" : "0"
  })
}

/** 更多操作 */
function handleCommand(command, row) {
  switch (command) {
    case "handleResetPwd":
      handleResetPwd(row)
      break
    case "handleAuthRole":
      handleAuthRole(row)
      break
    default:
      break
  }
}

/** 跳转角色分配 */
function handleAuthRole(row) {
  const userId = row.userId
  const basePath = route.path.startsWith("/qingbird/") ? "/qingbird/system/user-auth/role/" : "/system/user-auth/role/"
  router.push(basePath + userId)
}

function openLoginLogs(row) {
  const loginAccount = isQingbirdUserPage.value ? row.loginAccount : row.userName
  currentLogUserName.value = loginAccount
  loginLogQuery.pageNum = 1
  loginLogQuery.userName = loginAccount
  loginLogOpen.value = true
  fetchLoginLogs()
}

function fetchLoginLogs() {
  loginLogLoading.value = true
  if (isQingbirdUserPage.value) {
    request({
      url: "/qingbird/employee/loginLogs",
      method: "get",
      params: loginLogQuery
    }).then(response => {
      loginLogList.value = response.rows || []
      loginLogTotal.value = response.total || 0
    }).finally(() => {
      loginLogLoading.value = false
    })
    return
  }
  listLogininfor(loginLogQuery).then(response => {
    loginLogList.value = response.rows || []
    loginLogTotal.value = response.total || 0
  }).finally(() => {
    loginLogLoading.value = false
  })
}

/** 重置密码按钮操作 */
function handleResetPwd(row) {
  proxy.$prompt('请输入"' + row.userName + '"的新密码', "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    closeOnClickModal: false,
    inputPattern: /^.{5,20}$/,
    inputErrorMessage: "用户密码长度必须介于 5 和 20 之间",
    inputValidator: (value) => {
      if (/<|>|"|'|\||\\/.test(value)) {
        return "不能包含非法字符：< > \" ' \\\ |"
      }
    },
  }).then(({ value }) => {
    resetUserPwd(row.userId, value).then(() => {
      proxy.$modal.msgSuccess("修改成功，新密码是：" + value)
    })
  }).catch(() => {})
}

/** 选择条数  */
function handleSelectionChange(selection) {
  ids.value = selection.map(item => isQingbirdUserPage.value ? item.id : item.userId)
  single.value = selection.length != 1
  multiple.value = !selection.length
}

/** 导入按钮操作 */
function handleImport() {
  upload.title = "用户导入"
  upload.open = true
  upload.selectedFile = null
}

/** 下载模板操作 */
function importTemplate() {
  proxy.download("system/user/importTemplate", {
  }, `user_template_${new Date().getTime()}.xlsx`)
}

/**文件上传中处理 */
const handleFileUploadProgress = (event, file, fileList) => {
  upload.isUploading = true
}

/** 文件选择处理 */
const handleFileChange = (file, fileList) => {
  upload.selectedFile = file
}

/** 文件删除处理 */
const handleFileRemove = (file, fileList) => {
  upload.selectedFile = null
}

/** 文件上传成功处理 */
const handleFileSuccess = (response, file, fileList) => {
  upload.open = false
  upload.isUploading = false
  proxy.$refs["uploadRef"].handleRemove(file)
  proxy.$alert("<div style='overflow: auto;overflow-x: hidden;max-height: 70vh;padding: 10px 20px 0;'>" + response.msg + "</div>", "导入结果", { dangerouslyUseHTMLString: true })
  getList()
}

/** 提交上传文件 */
function submitFileForm() {
  const file = upload.selectedFile
  if (!file || file.length === 0 || !file.name.toLowerCase().endsWith('.xls') && !file.name.toLowerCase().endsWith('.xlsx')) {
    proxy.$modal.msgError("请选择后缀为 “xls”或“xlsx”的文件。")
    return
  }
  proxy.$refs["uploadRef"].submit()
}

/** 重置操作表单 */
function reset() {
  form.value = {
    id: undefined,
    userId: undefined,
    deptId: undefined,
    userName: undefined,
    loginAccount: undefined,
    branchCode: qingbirdBranchOptions.value[0]?.branchCode,
    name: undefined,
    idCard: undefined,
    mobile: undefined,
    address: undefined,
    nickName: undefined,
    password: undefined,
    phonenumber: undefined,
    email: undefined,
    sex: undefined,
    status: "0",
    remark: undefined,
    postIds: [],
    roleIds: []
  }
  proxy.resetForm("userRef")
}

/** 取消按钮 */
function cancel() {
  open.value = false
  reset()
}

/** 新增按钮操作 */
function handleAdd() {
  reset()
  if (isQingbirdUserPage.value) {
    open.value = true
    title.value = "添加客服坐席"
    return
  }
  getUser().then(response => {
    postOptions.value = response.posts
    roleOptions.value = response.roles
    open.value = true
    title.value = "添加用户"
    form.value.password = initPassword.value
  })
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset()
  if (isQingbirdUserPage.value) {
    const employeeId = row?.id || ids.value
    request({ url: `/qingbird/employee/${employeeId}`, method: "get" }).then(response => {
      const employee = response.data || row || {}
      form.value = {
        ...employee,
        branchCode: employee.branchCode || row?.branchCode,
        loginAccount: employee.loginAccount || row?.loginAccount,
        name: employee.name || row?.name,
        idCard: employee.idCard || row?.idCard,
        mobile: employee.mobile || row?.mobile,
        address: employee.address || row?.address,
        remark: employee.remark || row?.remark,
        status: employee.status || "0"
      }
      open.value = true
      title.value = "修改客服坐席"
    })
    return
  }
  const userId = row.userId || ids.value
  getUser(userId).then(response => {
    form.value = response.data
    postOptions.value = response.posts
    roleOptions.value = response.roles
    form.value.postIds = response.postIds
    form.value.roleIds = response.roleIds
    open.value = true
    title.value = "修改用户"
    form.value.password = ""
  })
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["userRef"].validate(valid => {
    if (valid) {
      if (isQingbirdUserPage.value) {
        const method = form.value.id ? "put" : "post"
        request({ url: "/qingbird/employee", method, data: { ...form.value } }).then(() => {
          proxy.$modal.msgSuccess(form.value.id ? "修改成功" : "新增成功")
          open.value = false
          getList()
        })
        return
      }
      if (form.value.userId != undefined) {
        updateUser(form.value).then(() => {
          proxy.$modal.msgSuccess("修改成功")
          open.value = false
          getList()
        })
      } else {
        addUser(form.value).then(() => {
          proxy.$modal.msgSuccess("新增成功")
          open.value = false
          getList()
        })
      }
    }
  })
}

onMounted(async () => {
  getDeptTree()
  await loadQingbirdBranchOptions()
  getList()
  proxy.getConfigKey("sys.user.initPassword").then(response => {
    initPassword.value = response.msg
  })
})
</script>
