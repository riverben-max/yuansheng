<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="68px">
      <el-form-item label="文章标题" prop="title">
        <el-input
          v-model="queryParams.title"
          placeholder="请输入文章标题"
          clearable
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="文章分类" prop="category">
        <el-select v-model="queryParams.category" placeholder="请选择文章分类" clearable>
          <el-option
            v-for="dict in biz_cloud_doc_category"
            :key="dict.value"
            :label="dict.label"
            :value="dict.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button
          type="primary"
          plain
          icon="Plus"
          @click="handleAdd"
          v-hasPermi="['qingbird:doc:add']"
        >新增文章</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="success"
          plain
          icon="Edit"
          :disabled="single"
          @click="handleUpdate"
          v-hasPermi="['qingbird:doc:edit']"
        >修改</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="danger"
          plain
          icon="Delete"
          :disabled="multiple"
          @click="handleDelete"
          v-hasPermi="['qingbird:doc:remove']"
        >删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="docList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="编号" align="center" prop="id" width="80" />
      <el-table-column label="文章标题" align="center" prop="title" :show-overflow-tooltip="true" />
      <el-table-column label="分类" align="center" prop="category">
        <template #default="scope">
          <dict-tag :options="biz_cloud_doc_category" :value="scope.row.category"/>
        </template>
      </el-table-column>
      <el-table-column label="状态" align="center" prop="status">
        <template #default="scope">
          <el-tag :type="scope.row.status === '0' ? 'success' : 'info'">
            {{ scope.row.status === '0' ? '正常' : '隐藏' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建人" align="center" prop="createBy" width="120" />
      <el-table-column label="创建时间" align="center" prop="createTime" width="160">
        <template #default="scope">
          <span>{{ parseTime(scope.row.createTime) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-button link type="primary" icon="View" @click="handlePreview(scope.row)" v-hasPermi="['qingbird:doc:query']">预览</el-button>
          <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['qingbird:doc:edit']">修改</el-button>
          <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['qingbird:doc:remove']">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <pagination
      v-show="total>0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 添加或修改文章对话框 -->
    <el-dialog :title="title" v-model="open" width="900px" append-to-body>
      <el-form ref="docRef" :model="form" :rules="rules" label-width="80px">
        <el-row>
          <el-col :span="24">
            <el-form-item label="文章标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入文章标题" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="文章分类" prop="category">
              <el-select v-model="form.category" placeholder="请选择文章分类" style="width: 100%;">
                <el-option
                  v-for="dict in biz_cloud_doc_category"
                  :key="dict.value"
                  :label="dict.label"
                  :value="dict.value"
                ></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="文章状态">
              <el-radio-group v-model="form.status">
                <el-radio label="0">正常</el-radio>
                <el-radio label="1">隐藏</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="文章内容">
              <editor v-model="form.content" :min-height="300" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 预览文章对话框 -->
    <el-dialog :title="previewTitle" v-model="openPreview" width="900px" append-to-body>
      <div class="article-preview-container">
        <h1 class="article-title">{{ previewDoc.title }}</h1>
        <div class="article-meta">
          <span>创建人：{{ previewDoc.createBy }}</span>
          <span>分类：<dict-tag :options="biz_cloud_doc_category" :value="previewDoc.category" style="display:inline-block" /></span>
          <span>发布时间：{{ parseTime(previewDoc.createTime) }}</span>
        </div>
        <el-divider border-style="dashed" />
        <div class="article-content ql-editor" v-html="sanitizedPreviewContent"></div>
      </div>
    </el-dialog>

  </div>
</template>

<script setup name="QingbirdDocs">
import { listDoc, getDoc, delDoc, addDoc, updateDoc } from "@/api/qingbird/doc";
import { sanitizeRichText } from "@/utils/richText";

const { proxy } = getCurrentInstance();
const { biz_cloud_doc_category } = proxy.useDict('biz_cloud_doc_category');

const docList = ref([]);
const open = ref(false);
const openPreview = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const previewTitle = ref("文章预览");
const previewDoc = ref({});
const sanitizedPreviewContent = computed(() => sanitizeRichText(previewDoc.value?.content));

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    title: undefined,
    category: undefined,
  },
  rules: {
    title: [
      { required: true, message: "文章标题不能为空", trigger: "blur" }
    ],
    category: [
      { required: true, message: "文章分类不能为空", trigger: "change" }
    ]
  }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询列表 */
function getList() {
  loading.value = true;
  listDoc(queryParams.value).then(response => {
    docList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

// 取消按钮
function cancel() {
  open.value = false;
  reset();
}

// 表单重置
function reset() {
  form.value = {
    id: undefined,
    title: undefined,
    category: undefined,
    content: undefined,
    status: "0",
    remark: undefined
  };
  proxy.resetForm("docRef");
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮操作 */
function resetQuery() {
  proxy.resetForm("queryRef");
  handleQuery();
}

// 多选框选中数据
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

/** 新增按钮操作 */
function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加云文档文章";
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset();
  const id = row.id || ids.value;
  getDoc(id).then(response => {
    form.value = response.data;
    open.value = true;
    title.value = "修改云文档文章";
  });
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["docRef"].validate(valid => {
    if (valid) {
      if (form.value.id != undefined) {
        updateDoc(form.value).then(response => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addDoc(form.value).then(response => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}

/** 删除按钮操作 */
function handleDelete(row) {
  const docIds = row.id || ids.value;
  proxy.$modal.confirm('是否确认删除文章编号为"' + docIds + '"的数据项？').then(function() {
    return delDoc(docIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

/** 预览操作 */
function handlePreview(row) {
  getDoc(row.id).then(response => {
    previewDoc.value = response.data;
    openPreview.value = true;
  });
}

getList();
</script>

<style scoped>
.article-preview-container {
  padding: 10px 20px 30px;
}
.article-title {
  text-align: center;
  font-size: 24px;
  color: #333;
  margin-top: 0;
  margin-bottom: 20px;
}
.article-meta {
  text-align: center;
  color: #999;
  font-size: 13px;
}
.article-meta span {
  margin: 0 10px;
}
.article-content {
  font-size: 15px;
  line-height: 1.8;
  color: #444;
}
/* 兼容一部分富文本样式如果需要 */
.article-content img {
  max-width: 100%;
}
</style>
