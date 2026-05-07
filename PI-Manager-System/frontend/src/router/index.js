import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('../views/ProductList.vue')
  },
  {
    path: '/products/add',
    name: 'AddProduct',
    component: () => import('../views/ProductForm.vue')
  },
  {
    path: '/products/:id',
    name: 'EditProduct',
    component: () => import('../views/ProductForm.vue')
  },
  {
    path: '/customers',
    name: 'Customers',
    component: () => import('../views/CustomerList.vue')
  },
  {
    path: '/customers/add',
    name: 'AddCustomer',
    component: () => import('../views/CustomerForm.vue')
  },
  {
    path: '/suppliers',
    name: 'Suppliers',
    component: () => import('../views/SupplierList.vue')
  },
  {
    path: '/pi',
    name: 'PIList',
    component: () => import('../views/PIList.vue')
  },
  {
    path: '/pi/add',
    name: 'AddPI',
    component: () => import('../views/PIForm.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
