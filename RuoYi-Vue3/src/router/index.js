import { createWebHistory, createRouter } from 'vue-router'
/* 若依默认 Layout */
import Layout from '@/layout'
/* 青鸟集团自定义 Layout */
import QingbirdLayout from '@/layout/qingbird/index.vue'

// 公共路由
export const constantRoutes = [
  {
    path: '/redirect',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '/redirect/:path(.*)',
        component: () => import('@/views/redirect/index.vue')
      }
    ]
  },
  {
    path: '/login',
    component: () => import('@/views/login'),
    hidden: true
  },
  {
    path: '/register',
    component: () => import('@/views/register'),
    hidden: true
  },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/error/404'),
    hidden: true
  },
  {
    path: '/401',
    component: () => import('@/views/error/401'),
    hidden: true
  },
  // 根路径直接重定向到青鸟控制台
  {
    path: '',
    redirect: '/qingbird/dashboard',
    hidden: true
  },
  {
    path: '/index',
    redirect: '/qingbird/dashboard',
    hidden: true
  },
  {
    path: '/lock',
    component: () => import('@/views/lock'),
    hidden: true,
    meta: { title: '锁定屏幕' }
  },
  {
    path: '/user',
    component: Layout,
    hidden: true,
    redirect: 'noredirect',
    children: [
      {
        path: 'profile/:activeTab?',
        component: () => import('@/views/system/user/profile/index'),
        name: 'Profile',
        meta: { title: '个人中心', icon: 'user' }
      }
    ]
  },

  // ===================================================
  // 青鸟集团业务模块（使用 QingbirdLayout）
  // ===================================================
  {
    path: '/qingbird',
    component: QingbirdLayout,
    redirect: '/qingbird/dashboard',
    hidden: true,
    children: [
      // P1 核心页面
      {
        path: 'center',
        component: () => import('@/views/qingbird/center/index.vue'),
        name: 'QingbirdCenter',
        meta: { title: '集团中心' }
      },
      {
        path: 'dashboard',
        component: () => import('@/views/qingbird/dashboard/index.vue'),
        name: 'QingbirdDashboard',
        meta: { title: '控制台' }
      },
      {
        path: 'qc-detail',
        component: () => import('@/views/qingbird/qcDetail/index.vue'),
        name: 'QingbirdQcDetail',
        meta: { title: '质检明细' }
      },
      // P2/P3 占位页面
      {
        path: 'branch',
        component: () => import('@/views/qingbird/branch/index.vue'),
        name: 'QingbirdBranch',
        meta: { title: '分公司管理' }
      },
      {
        path: 'system/user',
        component: () => import('@/views/system/user/index.vue'),
        name: 'QingbirdSystemUser',
        meta: { title: '用户管理', roles: ['admin'] }
      },
      {
        path: 'system/dept',
        component: () => import('@/views/system/dept/index.vue'),
        name: 'QingbirdSystemDept',
        meta: { title: '部门管理', roles: ['admin'] }
      },
      {
        path: 'system/user-auth/role/:userId(\\d+)',
        component: () => import('@/views/system/user/authRole.vue'),
        name: 'QingbirdAuthRole',
        meta: { title: '分配角色', activeMenu: '/qingbird/system/user', roles: ['admin'] }
      },
      {
        path: 'branch-data',
        component: () => import('@/views/qingbird/branchData/index.vue'),
        name: 'QingbirdBranchData',
        meta: { title: '分公司数据中心' }
      },
      {
        path: 'docs',
        component: () => import('@/views/qingbird/docs/index.vue'),
        name: 'QingbirdDocs',
        meta: { title: '云文档' }
      },
      {
        path: 'salary',
        component: () => import('@/views/qingbird/salary/index.vue'),
        name: 'QingbirdSalary',
        meta: { title: '薪资预览' }
      },
      {
        path: 'shop',
        component: () => import('@/views/qingbird/shop/index.vue'),
        name: 'QingbirdShop',
        meta: { title: '店铺管理' }
      },
      {
        path: 'output',
        component: () => import('@/views/qingbird/output/index.vue'),
        name: 'QingbirdOutput',
        meta: { title: '产值管理' }
      },
      {
        path: 'seat',
        component: () => import('@/views/qingbird/seat/index.vue'),
        name: 'QingbirdSeat',
        meta: { title: '客服坐席' }
      },
      {
        path: 'qc',
        component: () => import('@/views/qingbird/qc/index.vue'),
        name: 'QingbirdQc',
        meta: { title: '店铺质检' }
      },
      {
        path: 'settlement',
        component: () => import('@/views/qingbird/settlement/index.vue'),
        name: 'QingbirdSettlement',
        meta: { title: '结算管理' }
      },
      {
        path: 'bonus',
        component: () => import('@/views/qingbird/bonus/index.vue'),
        name: 'QingbirdBonus',
        meta: { title: '绩费明细' }
      },
      {
        path: 'finance',
        component: () => import('@/views/qingbird/finance/index.vue'),
        name: 'QingbirdFinance',
        meta: { title: '财务总览' }
      }
    ]
  }
]

// 动态路由，基于用户权限动态去加载
export const dynamicRoutes = [
  {
    path: '/system/user-auth',
    component: Layout,
    hidden: true,
    permissions: ['system:user:edit'],
    children: [
      {
        path: 'role/:userId(\\d+)',
        component: () => import('@/views/system/user/authRole'),
        name: 'AuthRole',
        meta: { title: '分配角色', activeMenu: '/system/user' }
      }
    ]
  },
  {
    path: '/system/role-auth',
    component: Layout,
    hidden: true,
    permissions: ['system:role:edit'],
    children: [
      {
        path: 'user/:roleId(\\d+)',
        component: () => import('@/views/system/role/authUser'),
        name: 'AuthUser',
        meta: { title: '分配用户', activeMenu: '/system/role' }
      }
    ]
  },
  {
    path: '/system/dict-data',
    component: Layout,
    hidden: true,
    permissions: ['system:dict:list'],
    children: [
      {
        path: 'index/:dictId(\\d+)',
        component: () => import('@/views/system/dict/data'),
        name: 'Data',
        meta: { title: '字典数据', activeMenu: '/system/dict' }
      }
    ]
  },
  {
    path: '/monitor/job-log',
    component: Layout,
    hidden: true,
    permissions: ['monitor:job:list'],
    children: [
      {
        path: 'index/:jobId(\\d+)',
        component: () => import('@/views/monitor/job/log'),
        name: 'JobLog',
        meta: { title: '调度日志', activeMenu: '/monitor/job' }
      }
    ]
  },
  {
    path: '/tool/gen-edit',
    component: Layout,
    hidden: true,
    permissions: ['tool:gen:edit'],
    children: [
      {
        path: 'index/:tableId(\\d+)',
        component: () => import('@/views/tool/gen/editTable'),
        name: 'GenEdit',
        meta: { title: '修改生成配置', activeMenu: '/tool/gen' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
})

export default router
