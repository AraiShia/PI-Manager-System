<template>
  <header class="top-nav">
    <div class="nav-left">
      <span class="title">{{ pageTitle }}</span>
    </div>
    <div class="nav-right">
      <div class="search-box">
        <input type="text" placeholder="搜索..." v-model="searchQuery" />
      </div>
      <button class="notification-btn">
        🔔
        <span class="notification-badge">3</span>
      </button>
      <div class="user-info">
        <span>管理员</span>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'

const searchQuery = ref('')

const pageTitles = {
  'Dashboard': '看板',
  'Products': '产品管理',
  'AddProduct': '新增产品',
  'EditProduct': '编辑产品',
  'Customers': '客户管理',
  'AddCustomer': '新增客户',
  'Suppliers': '供应商管理',
  'PIList': 'PI管理',
  'AddPI': '新建PI'
}

const pageTitle = computed(() => {
  return pageTitles[window.location.pathname.split('/')[1] || 'Dashboard'] || '看板'
})
</script>

<style scoped>
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 64px;
  background-color: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-box {
  position: relative;
}

.search-box input {
  padding: 8px 12px 8px 32px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  width: 200px;
}

.notification-btn {
  position: relative;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background-color: #ef4444;
  color: #fff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
}

.user-info {
  padding: 8px 16px;
  background-color: #f1f5f9;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
}
</style>
